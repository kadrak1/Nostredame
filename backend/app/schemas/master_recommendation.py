"""Pydantic schemas for MasterRecommendation endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


StrengthLevel = Literal["light", "medium", "strong"]

STRENGTH_LEVEL_RANGES: dict[str, tuple[int, int]] = {
    "light": (1, 4),
    "medium": (5, 7),
    "strong": (8, 10),
}


class RecommendationItemSchema(BaseModel):
    tobacco_id: int
    weight_grams: float = Field(20.0, ge=5.0, le=40.0)


class MasterRecommendationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    strength_level: StrengthLevel
    items: list[RecommendationItemSchema] = Field(..., min_length=1, max_length=5)

    @model_validator(mode="after")
    def check_unique_tobaccos(self) -> "MasterRecommendationCreate":
        ids = [item.tobacco_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("В рекомендации не должно быть дублирующихся табаков")
        return self


class MasterRecommendationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    strength_level: StrengthLevel | None = None
    items: list[RecommendationItemSchema] | None = Field(None, min_length=1, max_length=5)

    @model_validator(mode="after")
    def check_unique_tobaccos(self) -> "MasterRecommendationUpdate":
        if self.items is not None:
            ids = [item.tobacco_id for item in self.items]
            if len(ids) != len(set(ids)):
                raise ValueError("В рекомендации не должно быть дублирующихся табаков")
        return self


class MasterRecommendationPublic(BaseModel):
    id: int
    name: str
    strength_level: StrengthLevel
    items: list[RecommendationItemSchema]
    created_at: datetime

    model_config = {"from_attributes": True}


class RecommendationItemPublic(BaseModel):
    """Item enriched with tobacco name and flavors — for guest-facing endpoint."""

    tobacco_id: int
    tobacco_name: str
    flavor_profile: list[str]


class MasterRecommendationEnriched(BaseModel):
    """Recommendation with full tobacco info — returned by public GET."""

    id: int
    name: str
    strength_level: StrengthLevel
    items: list[RecommendationItemPublic]
    created_at: datetime
