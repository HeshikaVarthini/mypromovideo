"""YouTube Data API v3 client for channel and video intelligence."""

from __future__ import annotations

import math
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.models import ChannelData, VideoItem

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
MAX_VIDEOS_PER_CHANNEL = 25

# Words that usually mean a fan/news channel, not the brand's main channel
DISTRACTOR_WORDS = {
    "music", "tv", "news", "insider", "fans", "fan", "daily", "live",
    "hindi", "tamil", "telugu", "marathi", "bengali", "urdu", "arabic",
    "lyrics", "podcast", "reacts", "reaction", "gossip", "rumors", "rumours",
    "concept", "unboxing", "review", "reviews", "trailer", "lyric", "karaoke",
    "vevo", "topic", "archive", "clips", "shorts", "updates", "leaks",
    "explained", "tutorial", "tips", "tricks", "support", "help",
}

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall", "can", "need",
    "it", "its", "this", "that", "these", "those", "video", "videos",
    "channel", "youtube", "watch", "full", "hd", "4k", "official", "global",
    "india", "world", "international",
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

    def _normalize_key(self, name: str) -> str:
        return re.sub(r"[^a-z0-9]", "", name.lower())

    async def get_channel_by_handle(self, handle: str) -> Optional[dict]:
        handle = handle.lstrip("@")
        data = await self._get(
            "channels",
            {"part": "snippet,statistics,contentDetails", "forHandle": handle},
        )
        items = data.get("items", [])
        return items[0] if items else None

    def _generate_handle_candidates(self, company_name: str) -> list[str]:
        """Build @handle guesses from any company name (no fixed brand list)."""
        name = company_name.strip()
        if not name:
            return []

        parts = re.split(r"[\s\-]+", name)
        compact = re.sub(r"[^a-zA-Z0-9]", "", name)
        titled = "".join(p.capitalize() for p in parts if p)
        upper = compact.upper() if len(compact) <= 4 else None  # BMW, HP, AMD

        raw = [
            compact,
            compact.lower(),
            titled,
            titled.lower(),
            name.replace(" ", ""),
            name.replace(" ", "").lower(),
            f"{titled}Global",
            f"{titled}Official",
            f"{compact}Global",
            f"{compact}Official",
        ]
        if upper:
            raw.append(upper)
        if len(parts) > 1:
            raw.append(parts[0].capitalize())

        seen: set[str] = set()
        result: list[str] = []
        for h in raw:
            h = h.lstrip("@").strip()
            if h and h.lower() not in seen:
                seen.add(h.lower())
                result.append(h)
        return result[:10]

    async def _search_channel_ids(self, company_name: str) -> list[str]:
        """Run multiple searches and collect unique channel IDs."""
        queries = [
            f"{company_name} official channel",
            f"{company_name} official",
            company_name,
        ]
        seen: set[str] = set()
        ids: list[str] = []

        for q in queries:
            try:
                data = await self._get(
                    "search",
                    {
                        "part": "snippet",
                        "q": q,
                        "type": "channel",
                        "maxResults": 10,
                        "order": "relevance",
                    },
                )
                for item in data.get("items", []):
                    cid = item.get("snippet", {}).get("channelId")
                    if not cid and isinstance(item.get("id"), dict):
                        cid = item["id"].get("channelId")
                    if cid and cid not in seen:
                        seen.add(cid)
                        ids.append(cid)
            except Exception:
                continue
        return ids

    async def get_channels_batch(self, channel_ids: list[str]) -> list[dict]:
        if not channel_ids:
            return []
        results: list[dict] = []
        for i in range(0, len(channel_ids), 50):
            batch = channel_ids[i : i + 50]
            data = await self._get(
                "channels",
                {
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(batch),
                },
            )
            results.extend(data.get("items", []))
        return results

    def _score_channel(self, company_name: str, channel: dict) -> float:
        snippet = channel.get("snippet", {})
        stats = channel.get("statistics", {})
        title = snippet.get("title", "")
        title_lower = title.lower().strip()
        company_lower = company_name.lower().strip()
        company_norm = self._normalize_key(company_name)
        title_norm = self._normalize_key(title)

        score = 0.0

        # --- Title matching (most important) ---
        if title_lower == company_lower:
            score += 120
        elif title_norm == company_norm:
            score += 115
        elif title_lower == f"{company_lower} official":
            score += 110
        elif title_lower.startswith(company_lower):
            rest = title_lower[len(company_lower):].strip(" -|·")
            if not rest or rest in ("official", "global", "india", "world"):
                score += 95
            else:
                # "Apple Music", "Samsung India" etc.
                score += 45
                score -= len(rest.split()) * 18
        elif company_lower in title_lower:
            score += 35
        else:
            # Token overlap
            q_tokens = set(re.findall(r"[a-z0-9]+", company_lower))
            t_tokens = set(re.findall(r"[a-z0-9]+", title_lower))
            overlap = len(q_tokens & t_tokens) / max(len(q_tokens), 1)
            score += overlap * 30

        # --- Custom URL @handle match ---
        custom = (snippet.get("customUrl") or "").lower().lstrip("@")
        if custom:
            if custom == company_norm or custom == company_lower.replace(" ", ""):
                score += 50
            elif company_norm in custom or company_lower.replace(" ", "") in custom:
                score += 25

        # --- Official keyword ---
        if "official" in title_lower:
            score += 12

        # --- Subscriber count (prefer established brand channels) ---
        subs = int(stats.get("subscriberCount", 0) or 0)
        if subs >= 1_000_000:
            score += min(math.log10(subs) * 6, 35)
        elif subs >= 100_000:
            score += min(math.log10(subs) * 4, 20)
        elif subs >= 10_000:
            score += 5

        # --- Penalise fan/news/music spin-off channels ---
        title_tokens = set(re.findall(r"[a-z0-9]+", title_lower))
        company_tokens = set(re.findall(r"[a-z0-9]+", company_lower))
        extra = title_tokens - company_tokens - STOP_WORDS
        for word in extra:
            if word in DISTRACTOR_WORDS:
                score -= 35
        if len(extra) >= 3:
            score -= 15 * (len(extra) - 2)

        # Strong penalty: title has extra brand-unrelated words (e.g. "Apple Music")
        if title_lower != company_lower and company_lower in title_lower:
            after = title_lower.replace(company_lower, "").strip()
            after_words = [w for w in re.findall(r"[a-z]+", after) if w not in STOP_WORDS]
            if after_words and after_words[0] in DISTRACTOR_WORDS:
                score -= 50

        return score

    async def resolve_best_channel(self, company_name: str) -> Optional[dict]:
        """Find the best-matching official channel for any company name."""
        collected: dict[str, dict] = {}

        # 1) Try @handle guesses derived from the name (works for any brand)
        for handle in self._generate_handle_candidates(company_name):
            try:
                ch = await self.get_channel_by_handle(handle)
                if ch and ch.get("id"):
                    collected[ch["id"]] = ch
            except Exception:
                continue

        # 2) YouTube search — gather more candidates
        search_ids = await self._search_channel_ids(company_name)
        missing_ids = [cid for cid in search_ids if cid not in collected]
        if missing_ids:
            for ch in await self.get_channels_batch(missing_ids):
                if ch.get("id"):
                    collected[ch["id"]] = ch

        if not collected:
            return None

        # 3) Pick highest-scoring channel across all candidates
        channels = list(collected.values())
        best = max(channels, key=lambda c: self._score_channel(company_name, c))
        if self._score_channel(company_name, best) < 25:
            return None

        return best

    async def get_channel_details(self, channel_id: str) -> dict:
        data = await self._get(
            "channels",
            {"part": "snippet,statistics,contentDetails", "id": channel_id},
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
                {"part": "snippet,statistics,contentDetails", "id": ",".join(batch)},
            )
            all_videos.extend(data.get("items", []))
        return all_videos

    @staticmethod
    def parse_duration(iso_duration: str) -> int:
        if not iso_duration:
            return 0
        match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
        if not match:
            return 0
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds

    async def fetch_company_channel(self, company_name: str) -> ChannelData:
        try:
            channel = await self.resolve_best_channel(company_name)
            if not channel:
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

            channel_id = channel["id"]
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

            custom = snippet.get("customUrl", "")
            url = f"https://www.youtube.com/{custom}" if custom else f"https://www.youtube.com/channel/{channel_id}"

            return ChannelData(
                company_name=company_name,
                channel_id=channel_id,
                channel_title=snippet.get("title", company_name),
                channel_url=url,
                subscribers=int(stats.get("subscriberCount", 0) or 0),
                total_videos=int(stats.get("videoCount", 0) or 0),
                total_views=int(stats.get("viewCount", 0) or 0),
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
            views = int(stats.get("viewCount", 0) or 0)
            likes = int(stats.get("likeCount", 0) or 0)
            comments = int(stats.get("commentCount", 0) or 0)
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
        words = [w for w in re.findall(r"[a-z]{3,}", video.title.lower()) if w not in STOP_WORDS]
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

    gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
    avg_gap = sum(gaps) / len(gaps)
    variance = sum((g - avg_gap) ** 2 for g in gaps) / len(gaps)
    std_dev = variance ** 0.5
    consistency = max(0, 100 - (std_dev / max(avg_gap, 1)) * 40)
    return (round(uploads_per_month, 1), round(min(consistency, 100), 1))
