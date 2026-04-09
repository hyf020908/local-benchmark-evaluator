from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.evaluation import EvaluationRequest, HealthResponse
from app.services.evaluation_service import evaluation_service


router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.app_env,
    )


@router.get("/datasets")
async def list_datasets() -> dict:
    return {"items": [item.model_dump() for item in evaluation_service.list_supported_datasets()]}


@router.get("/evaluations")
async def list_evaluations() -> dict:
    return {"items": evaluation_service.list_history()}


@router.post("/evaluations/run")
async def run_evaluation(request: EvaluationRequest) -> dict:
    return evaluation_service.start(request)


@router.get("/evaluations/{job_id}")
async def get_evaluation(job_id: str) -> dict:
    return evaluation_service.get_job(job_id)
