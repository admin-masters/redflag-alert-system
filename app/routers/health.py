from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/", summary="Simple liveness check")
async def read_health():
    return {"status": "ok"}