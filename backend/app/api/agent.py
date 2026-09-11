from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from app.agent.graph import run_agent

from app.core.database import get_db

from app.core.dependencies import (
    get_current_user,
)

from app.models import User


router = APIRouter(
    prefix="/api/agent",
    tags=["Agent"],
)


# =========================================================
# Agent Request
# =========================================================

class AgentRequest(BaseModel):

    question: str = Field(
        min_length=1,
        max_length=2000,
    )


# =========================================================
# Agent Endpoint
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
            user_role=current_user.role,
            db=db,
        )

        return {
            "user_id": current_user.id,
            "user_role": current_user.role,
            **result,
        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except PermissionError as e:

        raise HTTPException(
            status_code=403,
            detail=str(e),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Agent failed: {str(e)}",
        )