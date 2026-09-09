from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.core.dependencies import (
    get_current_user,
)

from app.models.user import User

from app.services.rag_service import (
    ask_rag,
)


router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"],
)


# =========================================================
# Request Schema
# =========================================================

class ChatRequest(BaseModel):

    question: str = Field(
        min_length=1,
        max_length=2000,
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
    )


# =========================================================
# Chat API
# =========================================================

@router.post("")
def chat(
    request: ChatRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    try:

        result = ask_rag(
            question=request.question,
            db=db,
            user_id=current_user.id,
            top_k=request.top_k,
        )

        return {
            "user_id": current_user.id,
            **result,
        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"RAG failed: {str(e)}",
        )