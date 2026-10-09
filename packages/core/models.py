from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class FindingState(StrEnum):
    DISCOVERED = "DISCOVERED"
    PLANNED = "PLANNED"
    TESTING = "TESTING"
    CONFIRMED = "CONFIRMED"
    NOT_REPRODUCED = "NOT_REPRODUCED"
    INCONCLUSIVE = "INCONCLUSIVE"
    FIX_PROPOSED = "FIX_PROPOSED"
    FIX_TESTED = "FIX_TESTED"
    AWAITING_REVIEW = "AWAITING_REVIEW"


Category = Literal["bola", "authentication", "exposure", "headers", "injection", "dependency"]


class SourceRef(BaseModel):
    file: str
    line: int = Field(ge=1)


class Route(BaseModel):
    path: str
    methods: list[str]
    source: SourceRef
    router: Literal["app", "pages"]
    authentication_observed: bool = False
    ownership_observed: bool = False
    inputs: list[str] = []
    database_calls: list[str] = []
    sensitive_fields: list[str] = []
    environment_variables: list[str] = []
    server_action: bool = False


class Hypothesis(BaseModel):
    category: Category
    title: str
    endpoint: str
    sources: list[SourceRef]
    observations: list[str]
    conditions: list[str]
    expected: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    cwe: str | None = None


class Target(BaseModel):
    url: HttpUrl
    authorized: bool = False
    approved: bool = False
    allow_loopback: bool = False

    @field_validator("url")
    @classmethod
    def clean_url(cls, value):
        if value.username or value.password or value.query or value.fragment:
            raise ValueError("Target must not contain credentials, query, or fragment")
        if value.path not in (None, "/"):
            raise ValueError("Target must be an origin without a path")
        return value


class SyntheticFixture(BaseModel):
    endpoint: str = "/api/records/alice-record"
    other_endpoint: str = "/api/records/bob-record"
    owner_token: str = "demo-alice"
    other_token: str = "demo-bob"

    @field_validator("other_token")
    @classmethod
    def distinct_tokens(cls, value, info):
        if value == info.data.get("owner_token"):
            raise ValueError("Synthetic identities must use distinct tokens")
        return value


class Settings(BaseModel):
    targets: list[Target] = []
    categories: list[Category] = ["bola", "authentication", "exposure", "headers", "injection", "dependency"]
    request_budget: int = Field(default=30, ge=1, le=200)
    timeout_seconds: float = Field(default=5, ge=0.1, le=30)
    scan_timeout_seconds: int = Field(default=120, ge=5, le=600)
    requests_per_second: float = Field(default=3, ge=0.1, le=10)
    max_hypotheses: int = Field(default=20, ge=1, le=100)
    fixture: SyntheticFixture | None = None
    llm_enabled: bool = False
    llm_model: str = "openai/gpt-4o-mini"
    llm_base_url: HttpUrl | None = None
    sandbox_mode: Literal["static-only", "trusted-local"] = "static-only"


class RepositoryCreate(BaseModel):
    path: str = Field(min_length=1, max_length=4096)
    name: str | None = Field(default=None, max_length=100)


class ScanCreate(BaseModel):
    repository_id: str
    target: HttpUrl | None = None
    dynamic: bool = False


class TestPlan(BaseModel):
    category: Category
    method: Literal["GET"] = "GET"
    path: str
    identity: Literal["anonymous", "owner", "other"] = "anonymous"


class SettingsPatch(BaseModel):
    targets: list[Target] | None = None
    categories: list[Category] | None = None
    request_budget: int | None = Field(default=None, ge=1, le=200)
    timeout_seconds: float | None = Field(default=None, ge=0.1, le=30)
    scan_timeout_seconds: int | None = Field(default=None, ge=5, le=600)
    requests_per_second: float | None = Field(default=None, ge=0.1, le=10)
    max_hypotheses: int | None = Field(default=None, ge=1, le=100)
    fixture: SyntheticFixture | None = None
    llm_enabled: bool | None = None
    llm_model: str | None = None
    llm_base_url: HttpUrl | None = None
    sandbox_mode: Literal["static-only", "trusted-local"] | None = None
