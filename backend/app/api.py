from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, encrypt_secret, verify_password
from app.db import get_session
from app.dependencies import get_principal, require_role
from app.models import AnalysisRun, Chunk, DataSource, Document, KnowledgeBase, Membership, Organization, User
from app.schemas import (
    AnalysisRequest,
    AnalysisView,
    DataSourceCreate,
    DataSourceView,
    LoginRequest,
    Principal,
    QueryRequest,
    TokenResponse,
    DocumentView,
    KnowledgeBaseCreate,
    KnowledgeBaseView,
)
from app.services.analysis import AnalysisService
from app.services.audit import audit
from app.services.datasource import (
    DataSourceError,
    execute_guarded_query,
    synchronize_schema,
    test_connection,
)
from app.services.knowledge import KnowledgeError, chunk_text, extract_text, sha256

router = APIRouter(prefix="/api/v1")


async def tenant_knowledge_base(session: AsyncSession, knowledge_base_id: str, tenant_id: str) -> KnowledgeBase:
    knowledge_base = await session.scalar(
        select(KnowledgeBase).where(
            KnowledgeBase.id == knowledge_base_id, KnowledgeBase.tenant_id == tenant_id
        )
    )
    if not knowledge_base:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    return knowledge_base


@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    organization = await session.scalar(select(Organization).where(Organization.slug == payload.organization_slug))
    user = await session.scalar(select(User).where(User.email == payload.email.lower()))
    if not organization or not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    membership = await session.scalar(
        select(Membership).where(Membership.organization_id == organization.id, Membership.user_id == user.id)
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization membership required")
    await audit(session, organization.id, user.id, "auth.login", "user", user.id)
    await session.commit()
    return TokenResponse(access_token=create_access_token(user.id, organization.id, membership.role))


@router.get("/me")
async def me(principal: Principal = Depends(get_principal)) -> Principal:
    return principal


@router.get("/data-sources", response_model=list[DataSourceView])
async def list_data_sources(
    principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)
) -> list[DataSource]:
    result = await session.scalars(select(DataSource).where(DataSource.tenant_id == principal.tenant_id))
    return list(result)


@router.get("/knowledge-bases", response_model=list[KnowledgeBaseView])
async def list_knowledge_bases(
    principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)
) -> list[KnowledgeBase]:
    result = await session.scalars(
        select(KnowledgeBase)
        .where(KnowledgeBase.tenant_id == principal.tenant_id)
        .order_by(KnowledgeBase.created_at.desc())
    )
    return list(result)


@router.post("/knowledge-bases", response_model=KnowledgeBaseView, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    principal: Principal = Depends(require_role("org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeBase:
    knowledge_base = KnowledgeBase(
        tenant_id=principal.tenant_id,
        name=payload.name,
        description=payload.description,
        created_by=principal.user_id,
    )
    session.add(knowledge_base)
    await session.flush()
    await audit(session, principal.tenant_id, principal.user_id, "knowledge_base.created", "knowledge_base", knowledge_base.id)
    await session.commit()
    await session.refresh(knowledge_base)
    return knowledge_base


@router.post("/knowledge-bases/{knowledge_base_id}/documents", response_model=DocumentView, status_code=status.HTTP_201_CREATED)
async def upload_document(
    knowledge_base_id: str,
    file: UploadFile = File(...),
    principal: Principal = Depends(require_role("org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> Document:
    knowledge_base = await tenant_knowledge_base(session, knowledge_base_id, principal.tenant_id)
    payload = await file.read()
    if len(payload) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Document exceeds 10 MB limit")
    try:
        text, metadata = extract_text(file.filename or "document.txt", file.content_type or "application/octet-stream", payload)
    except KnowledgeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    document = Document(
        tenant_id=principal.tenant_id,
        knowledge_base_id=knowledge_base.id,
        filename=file.filename or "document.txt",
        content_type=file.content_type or "application/octet-stream",
        content_sha256=sha256(payload),
        created_by=principal.user_id,
        status="processed",
    )
    session.add(document)
    await session.flush()
    for ordinal, chunk, location in chunk_text(text):
        location.update(metadata)
        session.add(Chunk(tenant_id=principal.tenant_id, document_id=document.id, ordinal=ordinal, text=chunk, location=location))
    await audit(session, principal.tenant_id, principal.user_id, "document.uploaded", "document", document.id, {"filename": document.filename})
    await session.commit()
    await session.refresh(document)
    chunk_count = await session.scalar(select(func.count(Chunk.id)).where(Chunk.document_id == document.id)) or 0
    return DocumentView.model_validate({**document.__dict__, "chunk_count": chunk_count})


@router.get("/knowledge-bases/{knowledge_base_id}/documents", response_model=list[DocumentView])
async def list_documents(
    knowledge_base_id: str,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> list[DocumentView]:
    await tenant_knowledge_base(session, knowledge_base_id, principal.tenant_id)
    documents = list(await session.scalars(select(Document).where(
        Document.knowledge_base_id == knowledge_base_id, Document.tenant_id == principal.tenant_id
    ).order_by(Document.created_at.desc())))
    views = []
    for document in documents:
        count = await session.scalar(select(func.count(Chunk.id)).where(Chunk.document_id == document.id)) or 0
        views.append(DocumentView.model_validate({**document.__dict__, "chunk_count": count}))
    return views


@router.post("/data-sources", response_model=DataSourceView, status_code=status.HTTP_201_CREATED)
async def create_data_source(
    payload: DataSourceCreate,
    principal: Principal = Depends(require_role("org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> DataSource:
    source = DataSource(
        tenant_id=principal.tenant_id,
        name=payload.name,
        engine=payload.engine,
        host=payload.host,
        port=payload.port,
        database_name=payload.database_name,
        username=payload.username,
        encrypted_password=encrypt_secret(payload.password),
        allowed_tables=payload.allowed_tables,
        tls_required=payload.tls_required,
    )
    session.add(source)
    await session.flush()
    await audit(session, principal.tenant_id, principal.user_id, "datasource.created", "data_source", source.id)
    await session.commit()
    await session.refresh(source)
    return source


async def tenant_data_source(session: AsyncSession, source_id: str, tenant_id: str) -> DataSource:
    source = await session.scalar(
        select(DataSource).where(DataSource.id == source_id, DataSource.tenant_id == tenant_id)
    )
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found")
    return source


@router.post("/data-sources/{source_id}/test")
async def test_data_source(
    source_id: str,
    principal: Principal = Depends(require_role("org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    source = await tenant_data_source(session, source_id, principal.tenant_id)
    try:
        result = await test_connection(source)
    except DataSourceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Data source connection failed") from exc
    await audit(session, principal.tenant_id, principal.user_id, "datasource.tested", "data_source", source.id)
    await session.commit()
    return result


@router.post("/data-sources/{source_id}/sync")
async def sync_data_source(
    source_id: str,
    principal: Principal = Depends(require_role("org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    source = await tenant_data_source(session, source_id, principal.tenant_id)
    try:
        schema = await synchronize_schema(source)
    except DataSourceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Schema synchronization failed") from exc
    await audit(session, principal.tenant_id, principal.user_id, "datasource.schema_synced", "data_source", source.id, {"table_count": len(schema.tables)})
    await session.commit()
    return {"tables": schema.tables}


@router.post("/data-sources/{source_id}/query")
async def query_data_source(
    source_id: str,
    payload: QueryRequest,
    principal: Principal = Depends(require_role("analyst", "org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    source = await tenant_data_source(session, source_id, principal.tenant_id)
    try:
        guarded, rows = await execute_guarded_query(source, payload.sql)
    except DataSourceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query execution failed") from exc
    await audit(session, principal.tenant_id, principal.user_id, "datasource.query_executed", "data_source", source.id, {"tables": guarded.tables, "row_count": len(rows)})
    await session.commit()
    return {"sql": guarded.sql, "tables": guarded.tables, "rows": rows}


@router.post("/analyses/stream")
async def stream_analysis(
    payload: AnalysisRequest,
    principal: Principal = Depends(require_role("analyst", "org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    return StreamingResponse(AnalysisService().stream(session, principal, payload), media_type="text/event-stream")


@router.get("/analyses", response_model=list[AnalysisView])
async def list_analyses(
    principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)
) -> list[AnalysisRun]:
    result = await session.scalars(
        select(AnalysisRun).where(AnalysisRun.tenant_id == principal.tenant_id).order_by(AnalysisRun.created_at.desc())
    )
    return list(result)


@router.get("/dashboards/supply-chain")
async def supply_chain_dashboard(principal: Principal = Depends(get_principal)) -> dict:
    return {
        "tenant_id": principal.tenant_id,
        "refreshed_at": "2026-08-16T10:00:00Z",
        "cards": [
            {"label": "生产达成率", "value": "91.4%", "change": "+1.8%"},
            {"label": "缺料物料", "value": "12", "change": "-3"},
            {"label": "质量合格率", "value": "98.2%", "change": "+0.4%"},
            {"label": "订单准时交付", "value": "94.7%", "change": "+2.1%"},
        ],
        "trend": [{"month": "3月", "rate": 88.2}, {"month": "4月", "rate": 89.6}, {"month": "5月", "rate": 90.1}, {"month": "6月", "rate": 91.4}],
    }


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    await session.execute(select(Organization.id).limit(1))
    return {"status": "ready"}


@router.get("/metrics")
async def metrics() -> Response:
    return Response("# SupplyMind application metrics are exposed through OpenTelemetry collectors\n", media_type="text/plain")
