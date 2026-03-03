"""Secrets management with Fernet encryption."""

import os
from typing import Optional

from cryptography.fernet import Fernet
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Secret

_KEY: Optional[bytes] = None


def _get_fernet() -> Fernet:
    global _KEY
    if _KEY is None:
        raw = os.environ.get("TAPCRAFT_SECRET_KEY", "")
        if not raw:
            raise RuntimeError(
                "TAPCRAFT_SECRET_KEY environment variable is not set. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        _KEY = raw.encode() if isinstance(raw, str) else raw
    return Fernet(_KEY)


def encrypt_value(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()


async def set_secret(db: AsyncSession, name: str, value: str, category: Optional[str] = None) -> Secret:
    """Create or update a secret."""
    encrypted = encrypt_value(value)
    result = await db.execute(select(Secret).where(Secret.name == name))
    existing = result.scalar_one_or_none()
    if existing:
        existing.encrypted_value = encrypted
        if category is not None:
            existing.category = category
        await db.flush()
        return existing
    secret = Secret(name=name, encrypted_value=encrypted, category=category)
    db.add(secret)
    await db.flush()
    return secret


async def get_secret(name: str, db: Optional[AsyncSession] = None) -> str:
    """Retrieve and decrypt a secret by name.

    If no session is provided, creates a temporary one.
    """
    if db is not None:
        return await _get_secret_with_session(db, name)

    from src.db.base import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        return await _get_secret_with_session(session, name)


async def _get_secret_with_session(db: AsyncSession, name: str) -> str:
    result = await db.execute(select(Secret).where(Secret.name == name))
    secret = result.scalar_one_or_none()
    if secret is None:
        raise KeyError(f"Secret '{name}' not found")
    return decrypt_value(secret.encrypted_value)


async def list_secrets(db: AsyncSession) -> list[Secret]:
    result = await db.execute(select(Secret).order_by(Secret.name))
    return list(result.scalars().all())


async def delete_secret(db: AsyncSession, name: str) -> bool:
    result = await db.execute(sa_delete(Secret).where(Secret.name == name))
    await db.flush()
    return result.rowcount > 0
