from fastapi import APIRouter, Depends

from app.core.dependencies import (
    get_current_user,
    require_role,
)
from app.models.user import User


router = APIRouter(
    prefix="/api/rbac-test",
    tags=["RBAC Test"],
)


# =========================================================
# USER ACCESS
# =========================================================

@router.get("/user")
def user_access(
    current_user: User = Depends(get_current_user),
):
    return {
        "message": "User-level access granted.",
        "user_id": current_user.id,
        "role": current_user.role,
    }


# =========================================================
# MANAGER ACCESS
# =========================================================

@router.get("/manager")
def manager_access(
    current_user: User = Depends(
        require_role("manager", "admin")
    ),
):
    return {
        "message": "Manager-level access granted.",
        "user_id": current_user.id,
        "role": current_user.role,
    }


# =========================================================
# ADMIN ACCESS
# =========================================================

@router.get("/admin")
def admin_access(
    current_user: User = Depends(
        require_role("admin")
    ),
):
    return {
        "message": "Admin-level access granted.",
        "user_id": current_user.id,
        "role": current_user.role,
    }