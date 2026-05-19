from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ReportRequest(BaseModel):
    company: str = Field(..., min_length=1, max_length=120)
    competitors: list[str] = Field(default_factory=list, max_length=4)

    @field_validator("competitors")
    @classmethod
    def normalize_competitors(cls, v: list[str]) -> list[str]:
        cleaned = [c.strip() for c in v if c and c.strip()]
        if len(cleaned) > 4:
            raise ValueError("Maximum 4 competitors allowed")
        return cleaned


class VideoItem(BaseModel):
    video_id: str
    title: str
    published_at: str
    views: int
    likes: int
    comments: int
    engagement_rate: float
    duration_seconds: Optional[int] = None
    url: str


class ChannelData(BaseModel):
    company_name: str
    channel_id: str
    channel_title: str
    channel_url: str
    subscribers: int
    total_videos: int
    total_views: int
    videos: list[VideoItem] = Field(default_factory=list)
    found: bool = True
    error: Optional[str] = None


class CompanyInsight(BaseModel):
    company_name: str
    channel_title: str
    subscribers: int
    total_videos: int
    total_views: int
    avg_views_per_video: float
    avg_likes_per_video: float
    avg_comments_per_video: float
    avg_engagement_rate: float
    uploads_per_month: float
    posting_consistency_score: float
    top_topics: list[str]
    top_videos: list[VideoItem]
    strengths: list[str]
    weaknesses: list[str]


class GapItem(BaseModel):
    topic_or_format: str
    covered_by: list[str]
    missing_from: list[str]
    opportunity: str


class RankingEntry(BaseModel):
    company_name: str
    overall_score: float
    rank: int
    subscriber_score: float
    engagement_score: float
    consistency_score: float
    content_volume_score: float


class AnalysisReport(BaseModel):
    company: str
    competitors: list[str]
    generated_at: datetime
    channels: list[ChannelData]
    insights: list[CompanyInsight]
    leader: str
    leader_reason: str
    executive_summary: str
    gap_analysis: list[GapItem]
    recommendations: list[str]
    rankings: list[RankingEntry]
    comparative_metrics: dict
