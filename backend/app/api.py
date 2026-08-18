import secrets
from datetime import UTC, datetime, timedelta
from hashlib import sha256 as sha256_digest
from pathlib import Path
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    encrypt_secret,
    hash_oidc_state,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db import get_session, set_tenant_context
from app.dependencies import get_principal, require_role
from app.models import (
    AgentStep,
    AnalysisRun,
    Chunk,
    Dashboard,
    DataSource,
    Document,
    IngestionTask,
    KnowledgeBase,
    Membership,
    OIDCLoginState,
    Organization,
    RefreshToken,
    Report,
    ReportExport,
    SchemaSnapshot,
    User,
)
from app.modules.analysis.service import AnalysisService
from app.modules.datasources.service import (
    DataSourceError,
    ensure_source_enabled,
    execute_guarded_query,
    get_tenant_source,
    synchronize_schema,
    test_connection,
)
from app.modules.knowledge.service import get_tenant_knowledge_base, search_tenant_knowledge
from app.modules.reports.service import get_tenant_report, render_markdown, render_pdf
from app.schemas import (
    AgentStepView,
    AnalysisRequest,
    AnalysisView,
    DataSourceCreate,
    DataSourceView,
    DocumentView,
    IngestionTaskView,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseView,
    KnowledgeSearchRequest,
    LoginRequest,
    MemberRoleUpdate,
    MemberView,
    OrganizationSummary,
    PermissionMatrixView,
    Principal,
    QueryRequest,
    QuotaUpdate,
    RefreshRequest,
    ReportCreate,
    ReportExportView,
    ReportView,
    SchemaSnapshotView,
    TokenResponse,
)
from app.services.audit import audit
from app.services.ingestion import process_ingestion
from app.services.knowledge import KnowledgeError, extract_text, sha256
from app.services.llm import ModelConfigurationError, ModelResponseError

router = APIRouter(prefix="/api/v1")


@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    organization = await session.scalar(select(Organization).where(Organization.slug == payload.organization_slug))
    user = await session.scalar(select(User).where(User.email == payload.email.lower()))
    if not organization or not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    membership = await session.scalar(select(Membership).where(
        Membership.organization_id == organization.id, Membership.user_id == user.id, Membership.is_active.is_(True)
    ))
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization membership required")
    await set_tenant_context(session, organization.id)
    await audit(session, organization.id, user.id, "auth.login", "user", user.id)
    raw_refresh = create_refresh_token()
    session.add(RefreshToken(
        token_hash=hash_refresh_token(raw_refresh), user_id=user.id, organization_id=organization.id,
        expires_at=datetime.now(UTC) + timedelta(days=get_settings().refresh_token_days),
    ))
    await session.commit()
    return TokenResponse(
        access_token=create_access_token(user.id, organization.id, membership.role), refresh_token=raw_refresh
    )


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    stored = await session.scalar(select(RefreshToken).where(
        RefreshToken.token_hash == hash_refresh_token(payload.refresh_token)
    ))
    now = datetime.now(UTC)
    expires_at = stored.expires_at.replace(tzinfo=UTC) if stored and stored.expires_at.tzinfo is None else (stored.expires_at if stored else now)
    if not stored or stored.revoked_at or expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    membership = await session.scalar(select(Membership).where(
        Membership.organization_id == stored.organization_id, Membership.user_id == stored.user_id,
        Membership.is_active.is_(True),
    ))
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied")
    replacement = create_refresh_token()
    replacement_row = RefreshToken(
        token_hash=hash_refresh_token(replacement), user_id=stored.user_id, organization_id=stored.organization_id,
        expires_at=now + timedelta(days=get_settings().refresh_token_days),
    )
    session.add(replacement_row)
    stored.revoked_at = now
    stored.replaced_by = replacement_row.id
    await set_tenant_context(session, stored.organization_id)
    await audit(session, stored.organization_id, stored.user_id, "auth.refresh", "refresh_token", stored.id)
    await session.commit()
    return TokenResponse(
        access_token=create_access_token(stored.user_id, stored.organization_id, membership.role),
        refresh_token=replacement,
    )


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, session: AsyncSession = Depends(get_session)) -> Response:
    stored = await session.scalar(select(RefreshToken).where(
        RefreshToken.token_hash == hash_refresh_token(payload.refresh_token)
    ))
    if stored and not stored.revoked_at:
        stored.revoked_at = datetime.now(UTC)
        await set_tenant_context(session, stored.organization_id)
        await audit(session, stored.organization_id, stored.user_id, "auth.logout", "refresh_token", stored.id)
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def oidc_discovery() -> dict:
    issuer = get_settings().oidc_issuer
    if not issuer or not get_settings().oidc_client_id:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OIDC is not configured")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{issuer.rstrip('/')}/.well-known/openid-configuration")
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OIDC discovery failed") from exc


@router.get("/auth/oidc/start")
async def oidc_start(organization_slug: str, session: AsyncSession = Depends(get_session)) -> Response:
    organization = await session.scalar(select(Organization).where(Organization.slug == organization_slug))
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    metadata = await oidc_discovery()
    state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
    session.add(OIDCLoginState(
        state_hash=hash_oidc_state(state), nonce=nonce, organization_id=organization.id,
        expires_at=datetime.now(UTC) + timedelta(seconds=get_settings().oidc_state_ttl_seconds),
    ))
    await session.commit()
    params = {"client_id": get_settings().oidc_client_id, "response_type": "code",
              "scope": "openid email profile", "redirect_uri": get_settings().oidc_redirect_uri,
              "state": state, "nonce": nonce}
    return Response(status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                    headers={"location": f"{metadata['authorization_endpoint']}?{urlencode(params)}"})


@router.get("/auth/oidc/callback", response_model=TokenResponse)
async def oidc_callback(code: str, state: str, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    login_state = await session.scalar(select(OIDCLoginState).where(OIDCLoginState.state_hash == hash_oidc_state(state)))
    now = datetime.now(UTC)
    expires_at = login_state.expires_at.replace(tzinfo=UTC) if login_state and login_state.expires_at.tzinfo is None else (login_state.expires_at if login_state else now)
    if not login_state or login_state.consumed_at or expires_at <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OIDC state")
    metadata = await oidc_discovery()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            token_response = await client.post(metadata["token_endpoint"], data={
                "grant_type": "authorization_code", "code": code, "redirect_uri": get_settings().oidc_redirect_uri,
                "client_id": get_settings().oidc_client_id, "client_secret": get_settings().oidc_client_secret,
            })
            token_response.raise_for_status()
            token_data = token_response.json()
            id_token = token_data["id_token"]
            header = jwt.get_unverified_header(id_token)
            jwks_response = await client.get(metadata["jwks_uri"])
            jwks_response.raise_for_status()
            jwk = next((key for key in jwks_response.json().get("keys", []) if key.get("kid") == header.get("kid")), None)
            if not jwk:
                raise ValueError("OIDC signing key not found")
            signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
            claims = jwt.decode(id_token, signing_key, algorithms=[header.get("alg", "RS256")],
                                audience=get_settings().oidc_client_id, issuer=get_settings().oidc_issuer)
            if claims.get("iss") != get_settings().oidc_issuer or claims.get("nonce") != login_state.nonce:
                raise ValueError("OIDC claims validation failed")
            profile = claims
            if not profile.get("email") and metadata.get("userinfo_endpoint"):
                userinfo = await client.get(metadata["userinfo_endpoint"], headers={"Authorization": f"Bearer {token_data['access_token']}"})
                userinfo.raise_for_status()
                profile = userinfo.json()
    except (httpx.HTTPError, KeyError, ValueError, jwt.PyJWTError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OIDC callback failed") from exc
    email = str(profile.get("email", "")).lower().strip()
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OIDC email claim is required")
    user = await session.scalar(select(User).where(User.email == email))
    if not user:
        user = User(email=email, display_name=str(profile.get("name") or email.split("@", 1)[0]), password_hash=hash_password(secrets.token_urlsafe(32)))
        session.add(user)
        await session.flush()
    membership = await session.scalar(select(Membership).where(
        Membership.organization_id == login_state.organization_id, Membership.user_id == user.id
    ))
    if not membership:
        membership = Membership(organization_id=login_state.organization_id, user_id=user.id, role="viewer")
        session.add(membership)
    if not membership.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied")
    raw_refresh = create_refresh_token()
    session.add(RefreshToken(
        token_hash=hash_refresh_token(raw_refresh), user_id=user.id, organization_id=login_state.organization_id,
        expires_at=now + timedelta(days=get_settings().refresh_token_days),
    ))
    login_state.consumed_at = now
    await set_tenant_context(session, login_state.organization_id)
    await audit(session, login_state.organization_id, user.id, "auth.oidc_login", "user", user.id)
    await session.commit()
    return TokenResponse(access_token=create_access_token(user.id, login_state.organization_id, membership.role), refresh_token=raw_refresh)


@router.get("/me")
async def me(principal: Principal = Depends(get_principal)) -> Principal:
    return principal


@router.get("/organization", response_model=OrganizationSummary)
async def organization_summary(
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> OrganizationSummary:
    organization = await session.scalar(select(Organization).where(Organization.id == principal.tenant_id))
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    counts = {}
    for key, model in (
        ("member_count", Membership),
        ("data_source_count", DataSource),
        ("knowledge_base_count", KnowledgeBase),
        ("report_count", Report),
    ):
        column = Membership.organization_id if model is Membership else model.tenant_id
        counts[key] = int(await session.scalar(select(func.count()).select_from(model).where(column == principal.tenant_id)) or 0)
    counts["active_member_count"] = int(await session.scalar(select(func.count()).select_from(Membership).where(
        Membership.organization_id == principal.tenant_id, Membership.is_active.is_(True)
    )) or 0)
    counts["dashboard_count"] = int(await session.scalar(select(func.count()).select_from(Dashboard).where(
        Dashboard.tenant_id == principal.tenant_id
    )) or 0)
    quota = organization.quota_config or {}
    return OrganizationSummary(
        id=organization.id, slug=organization.slug, name=organization.name, role=principal.role,
        quota=quota, **counts,
    )


@router.get("/organization/quotas", response_model=dict[str, int])
async def get_organization_quotas(
    principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)
) -> dict[str, int]:
    organization = await session.scalar(select(Organization).where(Organization.id == principal.tenant_id))
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return organization.quota_config or {}


@router.patch("/organization/quotas", response_model=dict[str, int])
async def update_organization_quotas(
    payload: QuotaUpdate,
    principal: Principal = Depends(require_role("org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    organization = await session.scalar(select(Organization).where(Organization.id == principal.tenant_id))
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    organization.quota_config = payload.model_dump()
    await audit(session, principal.tenant_id, principal.user_id, "organization.quota_updated", "organization", organization.id, payload.model_dump())
    await session.commit()
    return organization.quota_config


@router.get("/organization/permissions", response_model=PermissionMatrixView)
async def permission_matrix(principal: Principal = Depends(get_principal)) -> PermissionMatrixView:
    return PermissionMatrixView(roles={
        "platform_admin": {"manage_members": True, "manage_data_sources": True, "manage_knowledge": True, "run_analysis": True, "view_audit": True},
        "org_admin": {"manage_members": True, "manage_data_sources": True, "manage_knowledge": True, "run_analysis": True, "view_audit": True},
        "analyst": {"manage_members": False, "manage_data_sources": False, "manage_knowledge": False, "run_analysis": True, "view_audit": False},
        "viewer": {"manage_members": False, "manage_data_sources": False, "manage_knowledge": False, "run_analysis": False, "view_audit": False},
    })


@router.get("/members", response_model=list[MemberView])
async def list_members(
    principal: Principal = Depends(require_role("org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> list[MemberView]:
    rows = await session.execute(
        select(Membership, User).join(User, User.id == Membership.user_id)
        .where(Membership.organization_id == principal.tenant_id).order_by(User.email)
    )
    return [MemberView(user_id=m.user_id, email=u.email, display_name=u.display_name,
                       role=m.role, is_active=m.is_active) for m, u in rows]


@router.patch("/members/{user_id}", response_model=MemberView)
async def update_member(
    user_id: str,
    payload: MemberRoleUpdate,
    principal: Principal = Depends(require_role("org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> MemberView:
    membership = await session.scalar(select(Membership).where(
        Membership.organization_id == principal.tenant_id, Membership.user_id == user_id
    ))
    user = await session.scalar(select(User).where(User.id == user_id))
    if not membership or not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    if user_id == principal.user_id and payload.role != "org_admin" and principal.role == "org_admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove your own admin role")
    membership.role = payload.role
    membership.is_active = True
    await audit(session, principal.tenant_id, principal.user_id, "member.role_updated", "membership", membership.id,
                {"user_id": user_id, "role": payload.role})
    await session.commit()
    return MemberView(user_id=user.id, email=user.email, display_name=user.display_name,
                      role=membership.role, is_active=membership.is_active)


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disable_member(
    user_id: str,
    principal: Principal = Depends(require_role("org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> Response:
    membership = await session.scalar(select(Membership).where(
        Membership.organization_id == principal.tenant_id, Membership.user_id == user_id
    ))
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    if user_id == principal.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot disable yourself")
    membership.is_active = False
    await audit(session, principal.tenant_id, principal.user_id, "member.disabled", "membership", membership.id,
                {"user_id": user_id})
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


@router.get("/knowledge-bases/{knowledge_base_id}", response_model=KnowledgeBaseView)
async def get_knowledge_base(
    knowledge_base_id: str, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)
) -> KnowledgeBase:
    return await get_tenant_knowledge_base(session, knowledge_base_id, principal.tenant_id)


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


@router.patch("/knowledge-bases/{knowledge_base_id}", response_model=KnowledgeBaseView)
async def update_knowledge_base(
    knowledge_base_id: str, payload: KnowledgeBaseUpdate,
    principal: Principal = Depends(require_role("org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeBase:
    knowledge_base = await get_tenant_knowledge_base(session, knowledge_base_id, principal.tenant_id)
    knowledge_base.name = payload.name
    knowledge_base.description = payload.description
    await audit(session, principal.tenant_id, principal.user_id, "knowledge_base.updated", "knowledge_base", knowledge_base.id)
    await session.commit()
    return knowledge_base


@router.post("/knowledge-bases/{knowledge_base_id}/archive", response_model=KnowledgeBaseView)
async def archive_knowledge_base(
    knowledge_base_id: str, principal: Principal = Depends(require_role("org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeBase:
    knowledge_base = await get_tenant_knowledge_base(session, knowledge_base_id, principal.tenant_id)
    knowledge_base.is_archived = not knowledge_base.is_archived
    knowledge_base.archived_at = datetime.now(UTC) if knowledge_base.is_archived else None
    await audit(session, principal.tenant_id, principal.user_id, "knowledge_base.archived" if knowledge_base.is_archived else "knowledge_base.restored", "knowledge_base", knowledge_base.id)
    await session.commit()
    return knowledge_base


@router.delete("/knowledge-bases/{knowledge_base_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    knowledge_base_id: str, principal: Principal = Depends(require_role("org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> Response:
    knowledge_base = await get_tenant_knowledge_base(session, knowledge_base_id, principal.tenant_id)
    document_count = await session.scalar(select(func.count(Document.id)).where(Document.knowledge_base_id == knowledge_base.id, Document.is_archived.is_(False))) or 0
    if document_count:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archive the knowledge base before deleting it")
    knowledge_base.is_archived = True
    knowledge_base.archived_at = datetime.now(UTC)
    await audit(session, principal.tenant_id, principal.user_id, "knowledge_base.deleted", "knowledge_base", knowledge_base.id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/knowledge-bases/{knowledge_base_id}/documents", response_model=DocumentView, status_code=status.HTTP_201_CREATED)
async def upload_document(
    knowledge_base_id: str,
    file: UploadFile = File(...),
    principal: Principal = Depends(require_role("org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> Document:
    knowledge_base = await get_tenant_knowledge_base(session, knowledge_base_id, principal.tenant_id)
    payload = await file.read()
    if len(payload) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Document exceeds 10 MB limit")
    try:
        extract_text(file.filename or "document.txt", file.content_type or "application/octet-stream", payload)
    except KnowledgeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    digest = sha256(payload)
    task_key = f"{principal.tenant_id}:{digest}"
    existing_task = await session.scalar(select(IngestionTask).where(IngestionTask.task_key == task_key))
    if existing_task:
        existing_document = await session.scalar(select(Document).where(Document.id == existing_task.document_id))
        if existing_document:
            chunk_count = await session.scalar(select(func.count(Chunk.id)).where(Chunk.document_id == existing_document.id)) or 0
            return DocumentView.model_validate({**existing_document.__dict__, "chunk_count": chunk_count, "ingestion_task_id": existing_task.id})
    storage_dir = Path(get_settings().document_directory)
    storage_dir.mkdir(parents=True, exist_ok=True)
    source_path = storage_dir / digest
    source_path.write_bytes(payload)
    document = Document(
        tenant_id=principal.tenant_id,
        knowledge_base_id=knowledge_base.id,
        filename=file.filename or "document.txt",
        content_type=file.content_type or "application/octet-stream",
        content_sha256=digest,
        created_by=principal.user_id,
        file_size_bytes=len(payload),
        language="zh" if any("\u4e00" <= char <= "\u9fff" for char in payload.decode("utf-8", errors="ignore")) else "en",
        status="queued",
        source_path=str(source_path),
    )
    session.add(document)
    await session.flush()
    task = IngestionTask(tenant_id=principal.tenant_id, document_id=document.id, task_key=task_key)
    session.add(task)
    await session.flush()
    if get_settings().ingestion_mode == "broker":
        from scripts.worker import celery_app

        dispatched = celery_app.send_task("supplymind.documents.ingest", args=[task.id])
        task.celery_task_id = dispatched.id
        await audit(session, principal.tenant_id, principal.user_id, "document.ingestion_queued", "document", document.id, {"task_id": task.id})
    else:
        await process_ingestion(session, task, document)
    await audit(session, principal.tenant_id, principal.user_id, "document.uploaded", "document", document.id, {"filename": document.filename})
    await session.commit()
    await session.refresh(document)
    chunk_count = await session.scalar(select(func.count(Chunk.id)).where(Chunk.document_id == document.id)) or 0
    return DocumentView.model_validate({**document.__dict__, "chunk_count": chunk_count, "ingestion_task_id": task.id})


@router.get("/documents/{document_id}", response_model=DocumentView)
async def get_document(
    document_id: str, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)
) -> DocumentView:
    document = await session.scalar(select(Document).where(Document.id == document_id, Document.tenant_id == principal.tenant_id))
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    chunk_count = await session.scalar(select(func.count(Chunk.id)).where(Chunk.document_id == document.id)) or 0
    return DocumentView.model_validate({**document.__dict__, "chunk_count": chunk_count})


@router.post("/documents/{document_id}/archive", response_model=DocumentView)
async def archive_document(
    document_id: str, principal: Principal = Depends(require_role("org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> DocumentView:
    document = await session.scalar(select(Document).where(Document.id == document_id, Document.tenant_id == principal.tenant_id))
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    document.is_archived = not document.is_archived
    document.archived_at = datetime.now(UTC) if document.is_archived else None
    await audit(session, principal.tenant_id, principal.user_id, "document.archived" if document.is_archived else "document.restored", "document", document.id)
    await session.commit()
    chunk_count = await session.scalar(select(func.count(Chunk.id)).where(Chunk.document_id == document.id)) or 0
    return DocumentView.model_validate({**document.__dict__, "chunk_count": chunk_count})


@router.post("/ingestion-tasks/{task_id}/retry", response_model=IngestionTaskView)
async def retry_ingestion(
    task_id: str, principal: Principal = Depends(require_role("org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> IngestionTask:
    task = await session.scalar(select(IngestionTask).where(IngestionTask.id == task_id, IngestionTask.tenant_id == principal.tenant_id))
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion task not found")
    if task.status == "processing":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ingestion task is already processing")
    task.status = "queued"
    task.dead_letter = False
    task.error_message = None
    task.next_retry_at = None
    document = await session.scalar(select(Document).where(Document.id == task.document_id, Document.tenant_id == principal.tenant_id))
    if not document or document.is_archived:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document is archived or unavailable")
    if get_settings().ingestion_mode == "broker":
        from scripts.worker import celery_app
        dispatched = celery_app.send_task("supplymind.documents.ingest", args=[task.id])
        task.celery_task_id = dispatched.id
    else:
        await process_ingestion(session, task, document)
    await audit(session, principal.tenant_id, principal.user_id, "document.ingestion_retried", "document", document.id, {"task_id": task.id})
    await session.commit()
    return task


@router.get("/ingestion-tasks/{task_id}", response_model=IngestionTaskView)
async def get_ingestion_task(
    task_id: str,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> IngestionTask:
    task = await session.scalar(select(IngestionTask).where(
        IngestionTask.id == task_id, IngestionTask.tenant_id == principal.tenant_id
    ))
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion task not found")
    return task


@router.post("/knowledge-bases/{knowledge_base_id}/search")
async def search_knowledge_base(
    knowledge_base_id: str,
    payload: KnowledgeSearchRequest,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await get_tenant_knowledge_base(session, knowledge_base_id, principal.tenant_id)
    try:
        results = await search_tenant_knowledge(
            session, principal.tenant_id, knowledge_base_id, payload.query, payload.limit
        )
    except ModelConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ModelResponseError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    await audit(session, principal.tenant_id, principal.user_id, "knowledge.searched", "knowledge_base", knowledge_base_id, {"result_count": len(results)})
    await session.commit()
    return {"query": payload.query, "results": results}


@router.post("/reports", response_model=ReportView, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ReportCreate,
    principal: Principal = Depends(require_role("analyst", "org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> Report:
    run = await session.scalar(select(AnalysisRun).where(
        AnalysisRun.id == payload.analysis_run_id, AnalysisRun.tenant_id == principal.tenant_id
    ))
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")
    markdown, citations = render_markdown(run, payload.title)
    report = Report(
        tenant_id=principal.tenant_id,
        analysis_run_id=run.id,
        title=payload.title or f"供应链分析报告 · {run.question[:80]}",
        markdown=markdown,
        citations=citations,
        created_by=principal.user_id,
    )
    session.add(report)
    await session.flush()
    await audit(session, principal.tenant_id, principal.user_id, "report.created", "report", report.id, {"analysis_run_id": run.id})
    await session.commit()
    await session.refresh(report)
    return report


@router.get("/reports", response_model=list[ReportView])
async def list_reports(
    principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)
) -> list[Report]:
    result = await session.scalars(select(Report).where(Report.tenant_id == principal.tenant_id).order_by(Report.created_at.desc()))
    return list(result)


@router.get("/reports/{report_id}", response_model=ReportView)
async def get_report(
    report_id: str,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> Report:
    report = await get_tenant_report(session, report_id, principal.tenant_id)
    return report


@router.post("/reports/{report_id}/exports/pdf", response_model=ReportExportView, status_code=status.HTTP_202_ACCEPTED)
async def export_report_pdf(
    report_id: str,
    principal: Principal = Depends(require_role("viewer", "analyst", "org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> ReportExport:
    report = await get_tenant_report(session, report_id, principal.tenant_id)
    existing = await session.scalar(select(ReportExport).where(
        ReportExport.report_id == report.id, ReportExport.tenant_id == principal.tenant_id,
        ReportExport.format == "pdf", ReportExport.status.in_(["queued", "running", "completed"]),
    ).order_by(ReportExport.created_at.desc()))
    if existing:
        return existing
    export = ReportExport(tenant_id=principal.tenant_id, report_id=report.id, created_by=principal.user_id)
    session.add(export)
    await session.flush()
    if get_settings().ingestion_mode == "broker":
        from scripts.worker import celery_app
        task = celery_app.send_task("supplymind.reports.export_pdf", args=[export.id])
        export.celery_task_id = task.id
    else:
        directory = Path(get_settings().report_directory)
        directory.mkdir(parents=True, exist_ok=True)
        export.file_path = str(directory / f"{report.id}-{export.id}.pdf")
        render_pdf(report.markdown, export.file_path)
        export.checksum_sha256 = sha256_digest(Path(export.file_path).read_bytes()).hexdigest()
        export.status = "completed"
    await audit(session, principal.tenant_id, principal.user_id, "report.export_queued", "report", report.id, {"export_id": export.id, "format": "pdf"})
    await session.commit()
    await session.refresh(export)
    return export


@router.get("/reports/{report_id}/exports/pdf", response_model=ReportExportView)
async def report_pdf_status(
    report_id: str,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> ReportExport:
    export = await session.scalar(select(ReportExport).where(
        ReportExport.report_id == report_id, ReportExport.tenant_id == principal.tenant_id,
        ReportExport.format == "pdf",
    ).order_by(ReportExport.created_at.desc()))
    if not export:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF export not found")
    return export


@router.get("/reports/{report_id}/exports", response_model=list[ReportExportView])
async def list_report_exports(report_id: str, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> list[ReportExport]:
    await get_tenant_report(session, report_id, principal.tenant_id)
    return list(await session.scalars(select(ReportExport).where(ReportExport.report_id == report_id, ReportExport.tenant_id == principal.tenant_id).order_by(ReportExport.created_at.desc())))


@router.get("/reports/{report_id}/exports/pdf/download")
async def download_report_pdf(
    report_id: str,
    principal: Principal = Depends(require_role("viewer", "analyst", "org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
):
    export = await session.scalar(select(ReportExport).where(
        ReportExport.report_id == report_id, ReportExport.tenant_id == principal.tenant_id,
        ReportExport.format == "pdf", ReportExport.status == "completed",
    ).order_by(ReportExport.created_at.desc()))
    if not export or not export.file_path or not Path(export.file_path).is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF is not ready")
    await audit(session, principal.tenant_id, principal.user_id, "report.downloaded", "report", report_id, {"format": "pdf"})
    await session.commit()
    return FileResponse(export.file_path, media_type="application/pdf", filename=f"{report_id}.pdf")


@router.get("/knowledge-bases/{knowledge_base_id}/documents", response_model=list[DocumentView])
async def list_documents(
    knowledge_base_id: str,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> list[DocumentView]:
    await get_tenant_knowledge_base(session, knowledge_base_id, principal.tenant_id)
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


@router.post("/data-sources/{source_id}/test")
async def test_data_source(
    source_id: str,
    principal: Principal = Depends(require_role("org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        source = await get_tenant_source(session, source_id, principal.tenant_id)
        ensure_source_enabled(source)
    except DataSourceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    try:
        result = await test_connection(source)
    except DataSourceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Data source connection failed") from exc
    source.status = "active"
    source.last_tested_at = datetime.now(UTC)
    await audit(session, principal.tenant_id, principal.user_id, "datasource.tested", "data_source", source.id)
    await session.commit()
    return result


@router.post("/data-sources/{source_id}/sync")
async def sync_data_source(
    source_id: str,
    principal: Principal = Depends(require_role("org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        source = await get_tenant_source(session, source_id, principal.tenant_id)
        ensure_source_enabled(source)
    except DataSourceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    try:
        schema = await synchronize_schema(source)
    except DataSourceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Schema synchronization failed") from exc
    source.last_synced_at = datetime.now(UTC)
    snapshot = SchemaSnapshot(tenant_id=principal.tenant_id, data_source_id=source.id, tables=schema.tables, table_count=len(schema.tables))
    session.add(snapshot)
    await audit(session, principal.tenant_id, principal.user_id, "datasource.schema_synced", "data_source", source.id, {"table_count": len(schema.tables), "snapshot_id": snapshot.id})
    await session.commit()
    return {"tables": schema.tables, "snapshot_id": snapshot.id, "synced_at": source.last_synced_at}


@router.get("/data-sources/{source_id}", response_model=DataSourceView)
async def get_data_source(source_id: str, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> DataSource:
    try:
        return await get_tenant_source(session, source_id, principal.tenant_id)
    except DataSourceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/data-sources/{source_id}/schema", response_model=SchemaSnapshotView | None)
async def get_data_source_schema(source_id: str, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> SchemaSnapshot | None:
    try:
        source = await get_tenant_source(session, source_id, principal.tenant_id)
    except DataSourceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return await session.scalar(select(SchemaSnapshot).where(SchemaSnapshot.data_source_id == source.id, SchemaSnapshot.tenant_id == principal.tenant_id).order_by(SchemaSnapshot.created_at.desc()))


@router.post("/data-sources/{source_id}/disable", response_model=DataSourceView)
async def disable_data_source(source_id: str, principal: Principal = Depends(require_role("org_admin", "platform_admin")), session: AsyncSession = Depends(get_session)) -> DataSource:
    try:
        source = await get_tenant_source(session, source_id, principal.tenant_id)
    except DataSourceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    source.status = "disabled" if source.status == "active" else "active"
    source.disabled_at = datetime.now(UTC) if source.status == "disabled" else None
    await audit(session, principal.tenant_id, principal.user_id, "datasource.disabled" if source.status == "disabled" else "datasource.enabled", "data_source", source.id)
    await session.commit()
    return source


@router.delete("/data-sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_data_source(source_id: str, principal: Principal = Depends(require_role("org_admin", "platform_admin")), session: AsyncSession = Depends(get_session)) -> Response:
    try:
        source = await get_tenant_source(session, source_id, principal.tenant_id)
    except DataSourceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    referenced = await session.scalar(select(func.count(AnalysisRun.id)).where(AnalysisRun.data_source_id == source.id, AnalysisRun.tenant_id == principal.tenant_id)) or 0
    if referenced:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Data source is referenced by analysis runs; disable it instead")
    await audit(session, principal.tenant_id, principal.user_id, "datasource.deleted", "data_source", source.id)
    await session.delete(source)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/data-sources/{source_id}/query")
async def query_data_source(
    source_id: str,
    payload: QueryRequest,
    principal: Principal = Depends(require_role("analyst", "org_admin", "platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        source = await get_tenant_source(session, source_id, principal.tenant_id)
        ensure_source_enabled(source)
    except DataSourceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
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


@router.get("/analyses/{analysis_id}", response_model=AnalysisView)
async def get_analysis(analysis_id: str, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> AnalysisRun:
    run = await session.scalar(select(AnalysisRun).where(AnalysisRun.id == analysis_id, AnalysisRun.tenant_id == principal.tenant_id))
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")
    return run


@router.get("/analyses/{analysis_id}/steps", response_model=list[AgentStepView])
async def get_analysis_steps(analysis_id: str, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> list:
    run = await session.scalar(select(AnalysisRun).where(AnalysisRun.id == analysis_id, AnalysisRun.tenant_id == principal.tenant_id))
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")
    return list(await session.scalars(select(AgentStep).where(AgentStep.analysis_run_id == run.id, AgentStep.tenant_id == principal.tenant_id).order_by(AgentStep.created_at)))


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(session: AsyncSession = Depends(get_session)) -> dict[str, object]:
    settings = get_settings()
    dependencies: dict[str, str] = {}
    try:
        await session.execute(select(Organization.id).limit(1))
        dependencies["postgres"] = "ok"
    except Exception:
        dependencies["postgres"] = "error"

    redis_client = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=2,
        socket_timeout=2,
        health_check_interval=15,
    )
    try:
        await redis_client.ping()
        dependencies["redis"] = "ok"
    except Exception:
        dependencies["redis"] = "error"
    finally:
        await redis_client.aclose()

    if any(value != "ok" for value in dependencies.values()):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "dependencies": dependencies},
        )
    return {"status": "ready", "dependencies": dependencies}


@router.get("/metrics")
async def metrics() -> Response:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
