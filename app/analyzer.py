"""Comparative video marketing analysis engine."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models import (
    AnalysisReport,
    ChannelData,
    CompanyInsight,
    GapItem,
    RankingEntry,
    ReportRequest,
    VideoItem,
)
from app.youtube_client import compute_upload_frequency, extract_topics_from_videos

FORMAT_KEYWORDS = {
    "tutorial": ["tutorial", "how to", "guide", "learn", "step by step"],
    "product demo": ["demo", "walkthrough", "overview", "features"],
    "testimonial": ["testimonial", "review", "customer", "case study", "success"],
    "webinar": ["webinar", "live", "q&a", "panel", "discussion"],
    "behind the scenes": ["behind", "bts", "culture", "team", "day in"],
    "announcement": ["launch", "announce", "introducing", "new", "release"],
    "thought leadership": ["insights", "trends", "future", "industry", "expert"],
    "short form": ["shorts", "#shorts", "short"],
}


def detect_formats(videos: list[VideoItem]) -> list[str]:
    formats_found: set[str] = set()
    for video in videos:
        title_lower = video.title.lower()
        for fmt, keywords in FORMAT_KEYWORDS.items():
            if any(kw in title_lower for kw in keywords):
                formats_found.add(fmt)
    return sorted(formats_found)


class VideoAnalyzer:
    def analyze(
        self,
        request: ReportRequest,
        channels: list[ChannelData],
    ) -> AnalysisReport:
        found_channels = [c for c in channels if c.found and c.videos]
        insights = [self._build_insight(ch) for ch in channels if ch.found]
        rankings = self._compute_rankings(insights)
        leader = rankings[0].company_name if rankings else request.company
        leader_reason = self._leader_reason(rankings, insights)
        executive_summary = self._executive_summary(
            request, insights, rankings, leader, leader_reason
        )
        gap_analysis = self._gap_analysis(channels, request.company)
        recommendations = self._recommendations(
            request.company, insights, gap_analysis, channels
        )
        comparative_metrics = self._comparative_metrics(insights)

        return AnalysisReport(
            company=request.company,
            competitors=request.competitors,
            generated_at=datetime.now(timezone.utc),
            channels=channels,
            insights=insights,
            leader=leader,
            leader_reason=leader_reason,
            executive_summary=executive_summary,
            gap_analysis=gap_analysis,
            recommendations=recommendations,
            rankings=rankings,
            comparative_metrics=comparative_metrics,
        )

    def _build_insight(self, channel: ChannelData) -> CompanyInsight:
        videos = channel.videos
        n = len(videos) or 1
        avg_views = sum(v.views for v in videos) / n
        avg_likes = sum(v.likes for v in videos) / n
        avg_comments = sum(v.comments for v in videos) / n
        avg_engagement = sum(v.engagement_rate for v in videos) / n
        uploads_per_month, consistency = compute_upload_frequency(videos)
        topics = extract_topics_from_videos(videos)
        strengths, weaknesses = self._strengths_weaknesses(
            channel, avg_views, avg_engagement, uploads_per_month, consistency, topics
        )

        return CompanyInsight(
            company_name=channel.company_name,
            channel_title=channel.channel_title,
            subscribers=channel.subscribers,
            total_videos=channel.total_videos,
            total_views=channel.total_views,
            avg_views_per_video=round(avg_views, 0),
            avg_likes_per_video=round(avg_likes, 1),
            avg_comments_per_video=round(avg_comments, 1),
            avg_engagement_rate=round(avg_engagement, 2),
            uploads_per_month=uploads_per_month,
            posting_consistency_score=consistency,
            top_topics=topics,
            top_videos=videos[:5],
            strengths=strengths,
            weaknesses=weaknesses,
        )

    def _strengths_weaknesses(
        self,
        channel: ChannelData,
        avg_views: float,
        avg_engagement: float,
        uploads_per_month: float,
        consistency: float,
        topics: list[str],
    ) -> tuple[list[str], list[str]]:
        strengths: list[str] = []
        weaknesses: list[str] = []

        if channel.subscribers >= 100_000:
            strengths.append(
                f"Strong audience base with {channel.subscribers:,} subscribers"
            )
        elif channel.subscribers >= 10_000:
            strengths.append(
                f"Established channel presence ({channel.subscribers:,} subscribers)"
            )
        else:
            weaknesses.append(
                "Smaller subscriber base limits organic reach — paid amplification may be needed"
            )

        if avg_engagement >= 3:
            strengths.append(
                f"High audience engagement ({avg_engagement:.1f}% interaction rate)"
            )
        elif avg_engagement < 1:
            weaknesses.append(
                "Low engagement rate suggests content may not be resonating or CTAs are weak"
            )

        if uploads_per_month >= 8:
            strengths.append(
                f"High publishing velocity (~{uploads_per_month:.0f} videos/month)"
            )
        elif uploads_per_month < 2:
            weaknesses.append(
                "Infrequent uploads hurt algorithmic favour — aim for at least 4 videos/month"
            )

        if consistency >= 70:
            strengths.append("Consistent posting cadence builds audience habit")
        elif consistency < 40 and uploads_per_month > 0:
            weaknesses.append(
                "Irregular posting schedule — audiences and algorithms reward predictability"
            )

        if len(topics) >= 4:
            strengths.append(
                f"Diverse content themes: {', '.join(topics[:4])}"
            )
        elif len(topics) <= 1:
            weaknesses.append(
                "Narrow content focus — consider expanding into adjacent topics"
            )

        formats = detect_formats(channel.videos)
        if len(formats) >= 3:
            strengths.append(
                f"Varied content formats: {', '.join(formats)}"
            )
        elif len(formats) <= 1:
            weaknesses.append(
                "Limited format variety — mix tutorials, demos, and thought leadership"
            )

        if not strengths:
            strengths.append("Active YouTube presence with measurable content library")
        if not weaknesses:
            weaknesses.append("Monitor competitor moves to maintain competitive edge")

        return strengths[:4], weaknesses[:4]

    def _compute_rankings(self, insights: list[CompanyInsight]) -> list[RankingEntry]:
        if not insights:
            return []

        max_subs = max(i.subscribers for i in insights) or 1
        max_engagement = max(i.avg_engagement_rate for i in insights) or 1
        max_consistency = max(i.posting_consistency_score for i in insights) or 1
        max_uploads = max(i.uploads_per_month for i in insights) or 1
        max_views = max(i.avg_views_per_video for i in insights) or 1

        entries: list[RankingEntry] = []
        for ins in insights:
            sub_score = (ins.subscribers / max_subs) * 25
            eng_score = (ins.avg_engagement_rate / max_engagement) * 25
            con_score = (ins.posting_consistency_score / max_consistency) * 25
            vol_score = (
                (ins.uploads_per_month / max_uploads) * 15
                + (ins.avg_views_per_video / max_views) * 10
            )
            overall = round(sub_score + eng_score + con_score + vol_score, 1)
            entries.append(
                RankingEntry(
                    company_name=ins.company_name,
                    overall_score=overall,
                    rank=0,
                    subscriber_score=round(sub_score, 1),
                    engagement_score=round(eng_score, 1),
                    consistency_score=round(con_score, 1),
                    content_volume_score=round(vol_score, 1),
                )
            )

        entries.sort(key=lambda e: e.overall_score, reverse=True)
        for i, entry in enumerate(entries):
            entry.rank = i + 1
        return entries

    def _leader_reason(
        self,
        rankings: list[RankingEntry],
        insights: list[CompanyInsight],
    ) -> str:
        if not rankings:
            return "Insufficient data to determine a leader."
        leader_name = rankings[0].company_name
        leader_insight = next(
            (i for i in insights if i.company_name == leader_name), None
        )
        if not leader_insight:
            return f"{leader_name} leads on composite video marketing score."

        reasons: list[str] = []
        if leader_insight.subscribers == max(i.subscribers for i in insights):
            reasons.append("largest subscriber base")
        if leader_insight.avg_engagement_rate == max(
            i.avg_engagement_rate for i in insights
        ):
            reasons.append("highest engagement rate")
        if leader_insight.uploads_per_month == max(
            i.uploads_per_month for i in insights
        ):
            reasons.append("most active publishing schedule")
        if leader_insight.avg_views_per_video == max(
            i.avg_views_per_video for i in insights
        ):
            reasons.append("strongest per-video reach")

        if reasons:
            return (
                f"{leader_name} leads because of {', '.join(reasons)}. "
                f"Their composite score reflects balanced strength across audience, "
                f"engagement, and publishing discipline."
            )
        return (
            f"{leader_name} achieves the highest overall video marketing score "
            f"({rankings[0].overall_score}/100) across all measured dimensions."
        )

    def _executive_summary(
        self,
        request: ReportRequest,
        insights: list[CompanyInsight],
        rankings: list[RankingEntry],
        leader: str,
        leader_reason: str,
    ) -> str:
        all_names = [request.company] + request.competitors
        found_count = len(insights)
        paragraphs = [
            f"This report compares video marketing performance across "
            f"{', '.join(all_names)} using publicly available YouTube data "
            f"({found_count} of {len(all_names)} channels successfully analysed).",
            leader_reason,
        ]

        user_insight = next(
            (i for i in insights if i.company_name == request.company), None
        )
        if user_insight and rankings:
            user_rank = next(
                (r.rank for r in rankings if r.company_name == request.company),
                None,
            )
            if user_rank and user_rank > 1:
                gap_to_leader = rankings[0].overall_score - (
                    next(
                        r.overall_score
                        for r in rankings
                        if r.company_name == request.company
                    )
                )
                paragraphs.append(
                    f"{request.company} currently ranks #{user_rank} with a score of "
                    f"{next(r.overall_score for r in rankings if r.company_name == request.company):.0f}/100, "
                    f"{gap_to_leader:.0f} points behind the leader. "
                    f"Key opportunity areas include "
                    f"{'increasing upload frequency' if user_insight.uploads_per_month < 4 else 'improving engagement'}, "
                    f"and expanding into content themes competitors are already winning with."
                )
            elif user_rank == 1:
                paragraphs.append(
                    f"{request.company} holds the #1 position in this competitive set. "
                    f"The priority is defending this lead by maintaining publishing consistency "
                    f"and doubling down on top-performing content themes."
                )

        return " ".join(paragraphs)

    def _gap_analysis(
        self,
        channels: list[ChannelData],
        primary_company: str,
    ) -> list[GapItem]:
        gaps: list[GapItem] = []
        company_topics: dict[str, set[str]] = {}
        company_formats: dict[str, set[str]] = {}

        for ch in channels:
            if not ch.found:
                continue
            company_topics[ch.company_name] = set(
                t.lower() for t in extract_topics_from_videos(ch.videos)
            )
            company_formats[ch.company_name] = set(detect_formats(ch.videos))

        primary_topics = company_topics.get(primary_company, set())
        primary_formats = company_formats.get(primary_company, set())

        all_topics: set[str] = set()
        for topics in company_topics.values():
            all_topics |= topics

        for topic in all_topics:
            covered_by = [
                name
                for name, topics in company_topics.items()
                if topic in topics
            ]
            missing_from = [
                name for name in company_topics if name not in covered_by
            ]
            if primary_company in missing_from or (
                primary_company in covered_by and len(covered_by) < len(company_topics)
            ):
                if primary_company not in covered_by:
                    gaps.append(
                        GapItem(
                            topic_or_format=f"Topic: {topic.title()}",
                            covered_by=covered_by,
                            missing_from=missing_from,
                            opportunity=(
                                f"Competitors are publishing around '{topic}' while "
                                f"{primary_company} has limited or no coverage. "
                                f"Creating 2–3 videos on this theme could capture "
                                f"search intent and audience interest."
                            ),
                        )
                    )

        all_formats: set[str] = set()
        for fmts in company_formats.values():
            all_formats |= fmts

        for fmt in all_formats:
            covered_by = [
                name
                for name, fmts in company_formats.items()
                if fmt in fmts
            ]
            if primary_company not in covered_by:
                gaps.append(
                    GapItem(
                        topic_or_format=f"Format: {fmt.title()}",
                        covered_by=covered_by,
                        missing_from=[
                            n for n in company_formats if n not in covered_by
                        ],
                        opportunity=(
                            f"Competitors use '{fmt}' content while {primary_company} "
                            f"does not. Testing this format could diversify reach and "
                            f"appeal to different funnel stages."
                        ),
                    )
                )

        gaps.sort(key=lambda g: len(g.covered_by), reverse=True)
        return gaps[:8]

    def _recommendations(
        self,
        primary: str,
        insights: list[CompanyInsight],
        gaps: list[GapItem],
        channels: list[ChannelData],
    ) -> list[str]:
        recs: list[str] = []
        user = next((i for i in insights if i.company_name == primary), None)
        if not user:
            return [
                "Verify the correct YouTube channel is associated with your brand.",
                "Establish a baseline content calendar before competitive benchmarking.",
            ]

        leader = insights[0] if insights else None
        for ins in sorted(insights, key=lambda x: x.avg_engagement_rate, reverse=True):
            if ins.company_name != primary and ins.avg_engagement_rate > 0:
                leader_engagement = ins
                break
        else:
            leader_engagement = None

        if user.uploads_per_month < 4:
            target = 4
            recs.append(
                f"Increase publishing frequency from ~{user.uploads_per_month:.0f} to "
                f"at least {target} videos per month. Channels posting 4+ times monthly "
                f"see better algorithmic distribution and audience retention."
            )

        if user.avg_engagement_rate < 2 and leader_engagement:
            recs.append(
                f"Engagement ({user.avg_engagement_rate:.1f}%) trails "
                f"{leader_engagement.company_name} ({leader_engagement.avg_engagement_rate:.1f}%). "
                f"Add clear CTAs, end-screen prompts, and community posts within 24 hours "
                f"of each upload to boost interaction."
            )

        if user.top_topics:
            recs.append(
                f"Double down on proven themes: {', '.join(user.top_topics[:3])}. "
                f"Create series playlists around these topics to increase session watch time."
            )

        for gap in gaps[:3]:
            recs.append(gap.opportunity)

        primary_channel = next((c for c in channels if c.company_name == primary), None)
        primary_videos = primary_channel.videos if primary_channel else []
        short_count = sum(
            1 for v in primary_videos
            if v.duration_seconds and v.duration_seconds <= 60
        )
        if short_count < 2:
            recs.append(
                "Introduce YouTube Shorts (under 60s) to reach new audiences. "
                "Repurpose long-form highlights into 3–5 Shorts per month."
            )

        top_video = user.top_videos[0] if user.top_videos else None
        if top_video:
            recs.append(
                f"Replicate success patterns from top performer '{top_video.title[:50]}' "
                f"({top_video.views:,} views). Analyse its thumbnail, title structure, "
                f"and hook in the first 30 seconds for future content."
            )

        if user.posting_consistency_score < 60:
            recs.append(
                "Establish a fixed publishing day (e.g., every Tuesday and Thursday) "
                "and batch-record content to improve consistency scores and audience habit."
            )

        recs.append(
            "Benchmark monthly: re-run this analysis to track score movement "
            "and validate that strategic changes are improving competitive position."
        )

        return recs[:8]

    def _comparative_metrics(self, insights: list[CompanyInsight]) -> dict:
        return {
            "companies": [i.company_name for i in insights],
            "subscribers": [i.subscribers for i in insights],
            "total_videos": [i.total_videos for i in insights],
            "avg_views": [i.avg_views_per_video for i in insights],
            "avg_engagement": [i.avg_engagement_rate for i in insights],
            "uploads_per_month": [i.uploads_per_month for i in insights],
            "consistency": [i.posting_consistency_score for i in insights],
        }
