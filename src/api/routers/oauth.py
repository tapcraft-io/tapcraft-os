"""API routes for OAuth provider and credential management."""

import secrets
import urllib.parse
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.models.schemas import (
    OAuthCredentialResponse,
    OAuthProviderCreate,
    OAuthProviderResponse,
    OAuthProviderUpdate,
)
from src.services import crud
from src.services.secrets import encrypt_value, decrypt_value

router = APIRouter(prefix="/oauth", tags=["oauth"])

# In-memory state store for CSRF protection during OAuth flows
_oauth_states: Dict[str, Dict[str, Any]] = {}


def _provider_to_response(provider, credential_count: int = 0) -> dict:
    """Convert provider model to response dict with credential count."""
    return {
        "id": provider.id,
        "workspace_id": provider.workspace_id,
        "name": provider.name,
        "slug": provider.slug,
        "client_id": provider.client_id,
        "auth_url": provider.auth_url,
        "token_url": provider.token_url,
        "scopes": provider.scopes,
        "redirect_uri": provider.redirect_uri,
        "credential_count": credential_count,
        "created_at": provider.created_at,
        "updated_at": provider.updated_at,
    }


@router.post("/providers", response_model=OAuthProviderResponse)
async def create_provider(
    payload: OAuthProviderCreate,
    workspace_id: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """Register a new OAuth provider."""
    encrypted_secret = encrypt_value(payload.client_secret)
    provider = await crud.create_oauth_provider(
        db=db,
        workspace_id=workspace_id,
        name=payload.name,
        slug=payload.slug,
        client_id=payload.client_id,
        encrypted_client_secret=encrypted_secret,
        auth_url=payload.auth_url,
        token_url=payload.token_url,
        scopes=payload.scopes,
        redirect_uri=payload.redirect_uri,
    )
    return _provider_to_response(provider, 0)


@router.get("/providers", response_model=List[OAuthProviderResponse])
async def list_providers(
    workspace_id: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """List all OAuth providers in a workspace."""
    providers = await crud.list_oauth_providers(db=db, workspace_id=workspace_id)
    return [_provider_to_response(p, len(p.credentials) if p.credentials else 0) for p in providers]


@router.get("/providers/{provider_id}", response_model=OAuthProviderResponse)
async def get_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get an OAuth provider by ID."""
    provider = await crud.get_oauth_provider(db=db, provider_id=provider_id, load_credentials=True)
    if not provider:
        raise HTTPException(status_code=404, detail="OAuth provider not found")
    return _provider_to_response(provider, len(provider.credentials) if provider.credentials else 0)


@router.patch("/providers/{provider_id}", response_model=OAuthProviderResponse)
async def update_provider(
    provider_id: int,
    payload: OAuthProviderUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an OAuth provider."""
    encrypted_secret = None
    if payload.client_secret:
        encrypted_secret = encrypt_value(payload.client_secret)

    provider = await crud.update_oauth_provider(
        db=db,
        provider_id=provider_id,
        name=payload.name,
        client_id=payload.client_id,
        encrypted_client_secret=encrypted_secret,
        scopes=payload.scopes,
        redirect_uri=payload.redirect_uri,
    )
    if not provider:
        raise HTTPException(status_code=404, detail="OAuth provider not found")
    return _provider_to_response(provider)


@router.delete("/providers/{provider_id}")
async def delete_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an OAuth provider and all its credentials."""
    deleted = await crud.delete_oauth_provider(db=db, provider_id=provider_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="OAuth provider not found")
    return {"deleted": True}


# ============================================================================
# OAuth Flow
# ============================================================================


@router.get("/providers/{provider_id}/authorize")
async def initiate_oauth(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Generate the OAuth authorization URL for a provider."""
    provider = await crud.get_oauth_provider(db=db, provider_id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="OAuth provider not found")

    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "provider_id": provider_id,
        "workspace_id": provider.workspace_id,
        "created_at": datetime.utcnow(),
    }

    redirect_uri = provider.redirect_uri or ""
    params = {
        "client_id": provider.client_id,
        "response_type": "code",
        "scope": provider.scopes,
        "state": state,
        "redirect_uri": redirect_uri,
    }
    auth_url = f"{provider.auth_url}?{urllib.parse.urlencode(params)}"
    return {"authorize_url": auth_url, "state": state}


@router.post("/callback")
async def oauth_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle the OAuth callback and exchange code for tokens."""
    # Validate state
    state_data = _oauth_states.pop(state, None)
    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    # Check state age (10 minute expiry)
    age = (datetime.utcnow() - state_data["created_at"]).total_seconds()
    if age > 600:
        raise HTTPException(status_code=400, detail="OAuth state expired")

    provider_id = state_data["provider_id"]
    workspace_id = state_data["workspace_id"]

    provider = await crud.get_oauth_provider(db=db, provider_id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="OAuth provider not found")

    # Exchange code for tokens
    client_secret = decrypt_value(provider.encrypted_client_secret)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            provider.token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": provider.client_id,
                "client_secret": client_secret,
                "redirect_uri": provider.redirect_uri or "",
            },
            headers={"Accept": "application/json"},
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Token exchange failed: {response.text[:500]}",
        )

    token_data = response.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="No access_token in response")

    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")
    expires_at = None
    if expires_in:
        expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))

    credential = await crud.create_oauth_credential(
        db=db,
        workspace_id=workspace_id,
        provider_id=provider_id,
        name=f"{provider.name} Account",
        encrypted_access_token=encrypt_value(access_token),
        encrypted_refresh_token=encrypt_value(refresh_token) if refresh_token else None,
        token_type=token_data.get("token_type", "Bearer"),
        expires_at=expires_at,
        scopes=token_data.get("scope", provider.scopes),
    )

    return OAuthCredentialResponse.model_validate(credential)


# ============================================================================
# Credential Management
# ============================================================================


@router.get("/credentials", response_model=List[OAuthCredentialResponse])
async def list_credentials(
    workspace_id: int = 1,
    provider_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all OAuth credentials."""
    return await crud.list_oauth_credentials(
        db=db, workspace_id=workspace_id, provider_id=provider_id
    )


@router.delete("/credentials/{credential_id}")
async def delete_credential(
    credential_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an OAuth credential (revoke connection)."""
    deleted = await crud.delete_oauth_credential(db=db, credential_id=credential_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Credential not found")
    return {"deleted": True}


@router.post("/credentials/{credential_id}/refresh")
async def refresh_credential(
    credential_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Refresh an OAuth credential's access token."""
    credential = await crud.get_oauth_credential(db=db, credential_id=credential_id)
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    if not credential.encrypted_refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token available")

    provider = await crud.get_oauth_provider(db=db, provider_id=credential.provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="OAuth provider not found")

    refresh_token = decrypt_value(credential.encrypted_refresh_token)
    client_secret = decrypt_value(provider.encrypted_client_secret)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            provider.token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": provider.client_id,
                "client_secret": client_secret,
            },
            headers={"Accept": "application/json"},
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Token refresh failed: {response.text[:500]}",
        )

    token_data = response.json()
    new_access_token = token_data.get("access_token")
    if not new_access_token:
        raise HTTPException(status_code=502, detail="No access_token in refresh response")

    credential.encrypted_access_token = encrypt_value(new_access_token)
    if token_data.get("refresh_token"):
        credential.encrypted_refresh_token = encrypt_value(token_data["refresh_token"])

    expires_in = token_data.get("expires_in")
    if expires_in:
        credential.expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))

    await db.commit()
    await db.refresh(credential)
    return OAuthCredentialResponse.model_validate(credential)
