from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.qdrant_service import search_documents


router = APIRouter(
    prefix="/api/search",
    tags=["Search"],
)


# =========================================================
# Request Schema
# =========================================================

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


# =========================================================
# Semantic Search API
# =========================================================

@router.post("")
def semantic_search(
    request: SearchRequest,
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Perform semantic search over
    enterprise documents.
    """

    try:

        results = search_documents(
            query=request.query,
            top_k=request.top_k,
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}",
        )

    return {
        "query": request.query,
        "top_k": request.top_k,
        "total_results": len(results),
        "results": results,
    }