from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


DatasetType = Literal[
    "auto",
    "mmlu_pro",
    "ceval",
    "cmmlu",
    "truthfulqa",
    "agieval",
    "gpqa",
    "hellaswag",
    "gaokao_bench",
    "big_bench",
    "big_bench_hard",
]


class EvaluationRequest(BaseModel):
    base_url: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    dataset_path: str = Field(..., min_length=1)
    dataset_type: DatasetType = "auto"
    max_samples: int = Field(20, ge=1, le=5000)
    concurrency: int = Field(2, ge=1, le=16)
    temperature: float = Field(0.0, ge=0.0, le=2.0)
    timeout_seconds: int = Field(120, ge=10, le=600)
    few_shot: int = Field(0, ge=0, le=10)
    random_seed: int = Field(1, ge=1, le=1_000_000)

    @field_validator("base_url", "model", "dataset_path")
    @classmethod
    def strip_value(cls, value: str) -> str:
        return value.strip()


class DatasetInfo(BaseModel):
    key: str
    label: str
    description: str
    supports_auto_detect: bool = True


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
