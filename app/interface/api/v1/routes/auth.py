from fastapi import APIRouter, Depends

from app.core.entities.user import User
from app.interface.api.v1.schemas.auth import UserOut
from app.interface.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserOut)
async def get_current_user_info(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email)
