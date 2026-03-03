"""API endpoints for secrets management."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.services.secrets import set_secret, list_secrets, delete_secret

router = APIRouter(prefix="/secrets", tags=["secrets"])


class SecretCreate(BaseModel):
    name: str
    value: str
    category: Optional[str] = None


class SecretOut(BaseModel):
    id: int
    name: str
    category: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


@router.post("", response_model=SecretOut)
async def create_secret(body: SecretCreate, db: AsyncSession = Depends(get_db)):
    try:
        secret = await set_secret(db, body.name, body.value, body.category)
        await db.commit()
        return SecretOut(
            id=secret.id,
            name=secret.name,
            category=secret.category,
            created_at=secret.created_at.isoformat(),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[SecretOut])
async def get_secrets(db: AsyncSession = Depends(get_db)):
    secrets = await list_secrets(db)
    return [
        SecretOut(
            id=s.id,
            name=s.name,
            category=s.category,
            created_at=s.created_at.isoformat(),
        )
        for s in secrets
    ]


@router.delete("/{name}")
async def remove_secret(name: str, db: AsyncSession = Depends(get_db)):
    deleted = await delete_secret(db, name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Secret '{name}' not found")
    await db.commit()
    return {"deleted": True}
