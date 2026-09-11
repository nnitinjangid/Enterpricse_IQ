from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.core.dependencies import (
    require_role,
)

from app.evaluation.dataset import (
    get_evaluation_dataset,
)

from app.evaluation.evaluator import (
    evaluate_retrieval_dataset,
    evaluate_generation_dataset,
)

from app.models import User


router = APIRouter(
    prefix="/api/evaluation",
    tags=["Evaluation"],
)


class RetrievalEvaluationRequest(BaseModel):

    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
    )


class GenerationEvaluationRequest(BaseModel):

    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
    )


# ============================================================
# RETRIEVAL EVALUATION
# ============================================================


@router.post("/retrieval")
def run_retrieval_evaluation(
    request: RetrievalEvaluationRequest,
    current_user: User = Depends(
        require_role("admin")
    ),
    db: Session = Depends(get_db),
):

    try:

        dataset = get_evaluation_dataset()

        if not dataset:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Evaluation dataset is empty."
                ),
            )

        result = evaluate_retrieval_dataset(
            dataset=dataset,
            db=db,
            user_id=current_user.id,
            user_role=current_user.role,
            top_k=request.top_k,
        )

        return {
            "evaluation_type": "retrieval",
            "evaluated_by": current_user.id,
            "evaluated_role": current_user.role,
            **result,
        }

    except HTTPException:

        raise

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
            detail=(
                f"Retrieval evaluation failed: "
                f"{str(e)}"
            ),
        )


# ============================================================
# GENERATION EVALUATION
# ============================================================


@router.post("/generation")
def run_generation_evaluation(
    request: GenerationEvaluationRequest,
    current_user: User = Depends(
        require_role("admin")
    ),
    db: Session = Depends(get_db),
):

    try:

        dataset = get_evaluation_dataset()

        if not dataset:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Evaluation dataset is empty."
                ),
            )

        result = evaluate_generation_dataset(
            dataset=dataset,
            db=db,
            user_id=current_user.id,
            user_role=current_user.role,
            top_k=request.top_k,
        )

        return {
            "evaluation_type": "generation",
            "evaluated_by": current_user.id,
            "evaluated_role": current_user.role,
            **result,
        }

    except HTTPException:

        raise

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
            detail=(
                f"Generation evaluation failed: "
                f"{str(e)}"
            ),
        )