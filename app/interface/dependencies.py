from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status

from app.core.entities.user import User
from app.core.exceptions import AuthenticationError, ExternalServiceError
from app.infrastructure.container import Container


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_bearer_token(authorization: str = Header(default="")) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token.strip()


async def get_current_user(
    container: Container = Depends(get_container),
    token: str = Depends(get_bearer_token),
) -> User:
    try:
        return await container.auth_provider.get_user(token)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except ExternalServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from exc
