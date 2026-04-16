from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


AiRole = Literal["user", "assistant"]
AiPage = Literal["greenFinance", "carbon", "energy", "macro"]


class AiHistoryMessage(BaseModel):
    role: AiRole
    content: str = Field(min_length=1, max_length=4000)


class AiPageContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    page: AiPage
    pageTitle: str = Field(min_length=1, max_length=100)
    year: int | None = None
    selectedProvince: str | None = None
    drillProvince: str | None = None
    drillCity: str | None = None
    snapshot: dict[str, Any] = Field(default_factory=dict)


class AiChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    pageContext: AiPageContext
    history: list[AiHistoryMessage] = Field(default_factory=list)


class AiSummaryRequest(BaseModel):
    pageContext: AiPageContext
    history: list[AiHistoryMessage] = Field(default_factory=list)


class AiTooltipRequest(BaseModel):
    regionName: str = Field(min_length=1, max_length=100)
    year: int | None = None
    moduleName: str = Field(min_length=1, max_length=50)
    tooltipScope: str = Field(min_length=1, max_length=100)
    dataPayload: dict[str, Any] = Field(default_factory=dict)
