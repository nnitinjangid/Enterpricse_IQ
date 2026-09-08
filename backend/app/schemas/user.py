from typing import Literal

from pydantic import BaseModel, Field


class RoleUpdateRequest(BaseModel):
    role: Literal["admin", "manager", "user"]


class StatusUpdateRequest(BaseModel):
    is_active: bool


class UserListResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True