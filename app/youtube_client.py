"""YouTube Data API v3 client for channel and video intelligence."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.models import ChannelData, VideoItem

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
MAX_VIDEOS_PER_CHANNEL = 25

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall", "can", "need",
    "it", "its", "this", "that", "these", "those", "i", "you", "he", "she",
    "we", "they", "what", "which", "who", "when", "where", "why", "how",
    "all", "each", "every", "both", "few", "more", "most", "other", "some",
    "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too",
    "very", "just", "also", "now", "new", "video", "videos", "official",
    "channel", "youtube", "watch", "full", "hd", "4k",
}


class YouTubeClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "YOUTUBE_API_KEY environment variable is required. "
                "Get one at https://console.cloud.google.com/apis/credentials"
            )

    async def _get(self, endpoint: str, params: dict[str, Any]) -> dict:
        params = {**params, "key": self.api_key}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{YOUTUBE_API_BASE}/{endpoint}", params=params)
            response.raise_for_status()
            return response.json()

    async def search_channel(self, company_name: str) -> Optional[dict]:
        """Find the most relevant YouTube channel for a company name."""
        data = await self._get(
            "search",
            {
                "part": "snippet",
                "q": f"{company_name} official",
                "type": "channel",
                "maxResults": 5,
                "order": "relevance",
            },
        )
        items = data.get("items", [])
        if not items:
            data = await self._get(
                "search",
                {
                    "part": "snippet",
                    "q": company_name,
                    "type": "channel",
                    "maxResults": 5,
                    "order": "relevance",
                },
            )
            items = data.get("items", [])

        if not items:
            return None

        best = self._pick_best_channel(company_name, items)
        return best

    def _pick_best_channel(self, company_name: str, items: list[dict]) -> dict:
        """Score channels by name similarity to company."""
        query_tokens = set(re.findall(r"[a-z0-9]+", company_name.lower()))

        def score(item: dict) -> float:
            title = item["snippet"]["title"].lower()
            title_tokens = set(re.findall(r"[a-z0-9]+", title))
            overlap = len(query_tokens & title_tokens) / max(len(query_tokens), 1)
            if "official" in title:
                overlap += 0.15
            return overlap

        return max(items, key=score)

    async def get_channel_details(self, channel_id: str) -> dict:
        data = await self._get(
            "channels",
            {
                "part": "snippet,statistics,contentDetails",
                "id": channel_id,
            },
        )
        items = data.get("items", [])
        if not items:
            raise ValueError(f"Channel not found: {channel_id}")
        return items[0]

    async def get_upload_playlist_videos(self, uploads_playlist_id: str) -> list[str]:
        video_ids: list[str] = []
        page_token: Optional[str] = None

        while len(video_ids) < MAX_VIDEOS_PER_CHANNEL:
            params: dict[str, Any] = {
                "part": "contentDetails",
                "playlistId": uploads_playlist_id,
                "maxResults": min(50, MAX_VIDEOS_PER_CHANNEL - len(video_ids)),
            }
            if page_token:
                params["pageToken"] = page_token

            data = await self._get("playlistItems", params)
            for item in data.get("items", []):
                vid = item.get("contentDetails", {}).get("videoId")
                if vid:
                    video_ids.append(vid)

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return video_ids[:MAX_VIDEOS_PER_CHANNEL]

    async def get_video_details(self, video_ids: list[str]) -> list[dict]:
        if not video_ids:
            return []

        all_videos: list[dict] = []
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i : i + 50]
            data = await self._get(
                "videos",
                {
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(batch),
                },
            )
            all_videos.extend(data.get("items", []))
        return all_videos

    @staticmethod
    def parse_duration(iso_duration: str) -> int:
        """Parse ISO 8601 duration (PT1H2M3S) to seconds."""
        if not iso_duration:
            return 0
        match = re.match(
            r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
            iso_duration,
        )
        if not match:
            return 0
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds

    async def fetch_company_channel(self, company_name: str) -> ChannelData:
        try:
            search_result = await self.search_channel(company_name)
            if not search_result:
                return ChannelData(
                    company_name=company_name,
                    channel_id="",
                    channel_title="Not found",
                    channel_url="",
                    subscribers=0,
                    total_videos=0,
                    total_views=0,
                    videos=[],
                    found=False,
                    error=f"No YouTube channel found for '{company_name}'",
                )

            channel_id = search_result["snippet"]["channelId"]
            channel = await self.get_channel_details(channel_id)
            stats = channel.get("statistics", {})
            snippet = channel.get("snippet", {})
            uploads_id = channel.get("contentDetails", {}).get(
                "relatedPlaylists", {}
            ).get("uploads", "")

            video_ids = []
            if uploads_id:
                video_ids = await self.get_upload_playlist_videos(uploads_id)

            raw_videos = await self.get_video_details(video_ids)
            videos = self._parse_videos(raw_videos)

            return ChannelData(
                company_name=company_name,
                channel_id=channel_id,
                channel_title=snippet.get("title", company_name),
                channel_url=f"https://www.youtube.com/channel/{channel_id}",
                subscribers=int(stats.get("subscriberCount", 0)),
                total_videos=int(stats.get("videoCount", 0)),
                total_views=int(stats.get("viewCount", 0)),
                videos=videos,
                found=True,
            )
        except Exception as exc:
            return ChannelData(
                company_name=company_name,
                channel_id="",
                channel_title="Error",
                channel_url="",
                subscribers=0,
                total_videos=0,
                total_views=0,
                videos=[],
                found=False,
                error=str(exc),
            )

    def _parse_videos(self, raw_videos: list[dict]) -> list[VideoItem]:
        items: list[VideoItem] = []
        for v in raw_videos:
            stats = v.get("statistics", {})
            snippet = v.get("snippet", {})
            vid = v["id"]
            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            comments = int(stats.get("commentCount", 0))
            engagement = ((likes + comments) / views * 100) if views > 0 else 0.0

            items.append(
                VideoItem(
                    video_id=vid,
                    title=snippet.get("title", "Untitled"),
                    published_at=snippet.get("publishedAt", ""),
                    views=views,
                    likes=likes,
                    comments=comments,
                    engagement_rate=round(engagement, 2),
                    duration_seconds=self.parse_duration(
                        v.get("contentDetails", {}).get("duration", "")
                    ),
                    url=f"https://www.youtube.com/watch?v={vid}",
                )
            )
        items.sort(key=lambda x: x.views, reverse=True)
        return items


def extract_topics_from_videos(videos: list[VideoItem], top_n: int = 8) -> list[str]:
    """Extract recurring themes from video titles via keyword frequency."""
    word_freq: dict[str, int] = {}
    for video in videos:
        words = re.findall(r"[a-z]{3,}", video.title.lower())
        seen_in_title: set[str] = set()
        for word in words:
            if word in STOP_WORDS or word in seen_in_title:
                continue
            seen_in_title.add(word)
            word_freq[word] = word_freq.get(word, 0) + 1

    bigrams: dict[str, int] = {}
    for video in videos:
        words = [
            w
            for w in re.findall(r"[a-z]{3,}", video.title.lower())
            if w not in STOP_WORDS
        ]
        for i in range(len(words) - 1):
            bg = f"{words[i]} {words[i+1]}"
            bigrams[bg] = bigrams.get(bg, 0) + 1

    combined: list[tuple[str, int]] = []
    for word, count in word_freq.items():
        if count >= 2:
            combined.append((word.title(), count))
    for bg, count in bigrams.items():
        if count >= 2:
            combined.append((bg.title(), count + 1))

    combined.sort(key=lambda x: x[1], reverse=True)
    return [t[0] for t in combined[:top_n]]


def compute_upload_frequency(videos: list[VideoItem]) -> tuple[float, float]:
    """Return (uploads_per_month, consistency_score 0-100)."""
    if len(videos) < 2:
        return (0.0, 0.0)

    dates: list[datetime] = []
    for v in videos:
        try:
            dt = datetime.fromisoformat(v.published_at.replace("Z", "+00:00"))
            dates.append(dt)
        except (ValueError, AttributeError):
            continue

    if len(dates) < 2:
        return (0.0, 0.0)

    dates.sort()
    span_days = max((dates[-1] - dates[0]).days, 1)
    uploads_per_month = len(dates) / (span_days / 30.44)

    gaps = [
        (dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)
    ]
    avg_gap = sum(gaps) / len(gaps)
    variance = sum((g - avg_gap) ** 2 for g in gaps) / len(gaps)
    std_dev = variance ** 0.5
    consistency = max(0, 100 - (std_dev / max(avg_gap, 1)) * 40)
    return (round(uploads_per_month, 1), round(min(consistency, 100), 1))
