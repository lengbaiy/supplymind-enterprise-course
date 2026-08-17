from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["platform_admin", "org_admin", "analyst", "viewer"]


class LoginRequest(BaseModel):
    email: str
    password: str
    organization_slug: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class Principal(BaseModel):
    user_id: str
    tenant_id: str
    role: Role


class DataSourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    engine: Literal["mysql", "postgresql"]
    host: str
    port: int = Field(ge=1, le=65535)
    database_name: str
    username: str
    password: str = Field(min_length=1)
    allowed_tables: list[str] = Field(min_length=1)
    tls_required: bool = False


class DataSourceView(BaseModel):
    id: str
    name: str
    engine: str
    host: str
    port: int
    database_name: str
    allowed_tables: list[str]
    tls_required: bool
    created_at: datetime


class QueryRequest(BaseModel):
    sql: str = Field(min_length=8, max_length=20_000)


class AnalysisRequest(BaseModel):
    data_source_id: str
    question: str = Field(min_length=5, max_length=4000)


class AnalysisView(BaseModel):
    id: str
    status: str
    question: str
    sql: str | None
    result: dict | None
    created_at: datetime


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=2000)


class KnowledgeBaseView(BaseModel):
    id: str
    name: str
    description: str
    created_by: str
    created_at: datetime


class DocumentView(BaseModel):
    id: str
    knowledge_base_id: str
    filename: str
    content_type: str
    status: str
    chunk_count: int
    created_at: datetime
