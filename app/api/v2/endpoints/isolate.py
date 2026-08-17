from fastapi import APIRouter, HTTPException, status


router = APIRouter()


@router.get("/", deprecated=True)
async def isolate_info():
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "message": "This endpoint is deprecated because the API node does not contain isolate.",
            "capabilities_source": "worker registry",
            "availability": "Use /v2/workers to inspect per-worker isolate and runtime capabilities.",
        },
    )
