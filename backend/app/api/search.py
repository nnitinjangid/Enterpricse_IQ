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

from app.services.qdrant_service import (
    search_documents,
)

from app.services.bm25_service import (
    keyword_search,
)

from app.services.hybrid_search_service import (
    hybrid_search,
)

from app.services.reranker_service import (
    rerank_results,
)


router = APIRouter(
    prefix="/api/search",
    tags=["Search"],
)


class SearchRequest(BaseModel):

    query: str = Field(
        min_length=1,
        max_length=2000,
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
    )


@router.post("")
def semantic_search(
    request: SearchRequest,
    current_user: User = Depends(
        get_current_user
    ),
):

    try:

        results = search_documents(
            query=request.query,
            top_k=request.top_k,
            user_id=current_user.id,
            user_role=current_user.role,
        )

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Search failed: {str(e)}"
            ),
        )

    return {
        "query": request.query,
        "top_k": request.top_k,
        "total_results": len(results),
        "retrieval_method": "semantic",
        "results": results,
    }


@router.post("/keyword")
def keyword_search_api(
    request: SearchRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    try:

        results = keyword_search(
            query=request.query,
            db=db,
            user_id=current_user.id,
            user_role=current_user.role,
            top_k=request.top_k,
        )

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Keyword search failed: "
                f"{str(e)}"
            ),
        )

    return {
        "query": request.query,
        "top_k": request.top_k,
        "total_results": len(results),
        "retrieval_method": "bm25",
        "results": results,
    }


@router.post("/hybrid")
def hybrid_search_api(
    request: SearchRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    try:

        results = hybrid_search(
            query=request.query,
            db=db,
            user_id=current_user.id,
            user_role=current_user.role,
            top_k=request.top_k,
        )

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Hybrid search failed: "
                f"{str(e)}"
            ),
        )

    return {
        "query": request.query,
        "top_k": request.top_k,
        "total_results": len(results),
        "retrieval_method": "hybrid",
        "results": results,
    }


@router.post("/rerank")
def rerank_search_api(
    request: SearchRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    try:

        candidates = hybrid_search(
            query=request.query,
            db=db,
            user_id=current_user.id,
            user_role=current_user.role,
            top_k=max(
                request.top_k * 2,
                10,
            ),
        )

        results = rerank_results(
            query=request.query,
            results=candidates,
            top_k=request.top_k,
        )

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Reranking failed: "
                f"{str(e)}"
            ),
        )

    return {
        "query": request.query,
        "top_k": request.top_k,
        "candidates": len(candidates),
        "total_results": len(results),
        "retrieval_method": (
            "hybrid_reranked"
        ),
        "results": results,
    }