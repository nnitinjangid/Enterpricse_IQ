from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from app.agent.graph import (
    run_agent,
)

from app.core.database import (
    get_db,
)

from app.core.dependencies import (
    get_current_user,
)

from app.models.user import User


router = APIRouter(
    prefix="/api/agent",
    tags=["Agent"],
)


# =========================================================
# Request Schema
# =========================================================

class AgentRequest(BaseModel):

    question: str = Field(
        min_length=1,
        max_length=2000,
    )


# =========================================================
# Agent API
# =========================================================

@router.post("")
def agent_chat(
    request: AgentRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    try:

        result = run_agent(
            question=request.question,
            user_id=current_user.id,
            db=db,
        )

        return {
            "user_id": current_user.id,
            "question": result[
                "question"
            ],
            "route": result[
                "route"
            ],
            "confidence": result[
                "route_confidence"
            ],
            "answer": result[
                "answer"
            ],
            "sources": result.get(
                "sources",
                [],
            ),
        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Agent failed: {str(e)}",
        )