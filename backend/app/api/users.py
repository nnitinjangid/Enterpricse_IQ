from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.user import User
from app.schemas.user import (
    RoleUpdateRequest,
    StatusUpdateRequest,
    UserDetailResponse,
    UserListResponse,
)


router = APIRouter(
    prefix="/api/users",
    tags=["User Management"],
)


# =========================================================
# GET ALL USERS
# =========================================================

@router.get(
    "",
    response_model=list[UserListResponse],
)
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("admin")
    ),
):
    """
    Return all users.

    Admin only.
    """

    users = (
        db.query(User)
        .order_by(User.id.asc())
        .all()
    )

    return users


# =========================================================
# GET USER BY ID
# =========================================================

@router.get(
    "/{user_id}",
    response_model=UserDetailResponse,
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("admin")
    ),
):
    """
    Return a specific user.

    Admin only.
    """

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return user


# =========================================================
# UPDATE USER ROLE
# =========================================================

@router.patch(
    "/{user_id}/role",
    response_model=UserDetailResponse,
)
def update_user_role(
    user_id: int,
    role_data: RoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("admin")
    ),
):
    """
    Change a user's role.

    Admin only.
    """

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # Prevent admin from accidentally removing
    # their own admin privileges.
    if (
        user.id == current_user.id
        and role_data.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove your own admin role.",
        )

    user.role = role_data.role

    db.commit()
    db.refresh(user)

    return user


# =========================================================
# UPDATE USER STATUS
# =========================================================

@router.patch(
    "/{user_id}/status",
    response_model=UserDetailResponse,
)
def update_user_status(
    user_id: int,
    status_data: StatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("admin")
    ),
):
    """
    Activate or deactivate a user.

    Admin only.
    """

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # Prevent admin from deactivating themselves.
    if (
        user.id == current_user.id
        and status_data.is_active is False
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )

    user.is_active = status_data.is_active

    db.commit()
    db.refresh(user)

    return user