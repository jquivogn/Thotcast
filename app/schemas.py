from datetime import datetime
from pydantic import BaseModel, field_validator


class PodcastStep(BaseModel):
    character: str
    voice: str
    subject: str


class ConfigIn(BaseModel):
    rss_feeds: list[str]
    keywords: list[str]
    podcast_structure: list[PodcastStep]

    @field_validator("rss_feeds")
    @classmethod
    def rss_feeds_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one RSS feed is required")
        return v

    @field_validator("podcast_structure")
    @classmethod
    def structure_not_empty(cls, v: list[PodcastStep]) -> list[PodcastStep]:
        if not v:
            raise ValueError("At least one podcast step is required")
        return v


class ConfigOut(BaseModel):
    id: int
    rss_feeds: list[str]
    keywords: list[str]
    podcast_structure: list[PodcastStep]
    updated_at: datetime

    model_config = {"from_attributes": True}


class EpisodeOut(BaseModel):
    id: int
    title: str
    summary: str
    audio_url: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerateResponse(BaseModel):
    message: str
    episode_id: int
