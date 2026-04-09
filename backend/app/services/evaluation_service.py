from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException

from app.core.config import settings
from app.core.security import mask_api_key
from app.evaluators.registry import registry
from app.schemas.evaluation import DatasetInfo, EvaluationRequest
from app.services.job_store import job_store, utc_now
from app.services.model_client import ModelClientError, OpenAICompatibleClient


class EvaluationService:
    def _resolve_example_path(self, dataset_key: str) -> Optional[str]:
        authoritative_roots = {
            "mmlu_pro": settings.benchmarks_root / "MMLU-Pro",
            "ceval": settings.benchmarks_root / "ceval",
            "cmmlu": settings.benchmarks_root / "CMMLU",
            "truthfulqa": settings.benchmarks_root / "TruthfulQA",
            "mmlu": settings.benchmarks_root / "MMLU",
            "gsm8k": settings.benchmarks_root / "GSM8K",
        }
        candidate = authoritative_roots.get(dataset_key)
        if candidate and candidate.exists():
            return str(candidate.resolve())
        return None

    def list_supported_datasets(self) -> list[DatasetInfo]:
        datasets: list[DatasetInfo] = []
        for evaluator in registry.list():
            datasets.append(
                DatasetInfo(
                    key=evaluator.key,
                    label=evaluator.label,
                    description=evaluator.description,
                    example_path=self._resolve_example_path(evaluator.key),
                )
            )
        return datasets

    def list_history(self) -> list[dict[str, Any]]:
        live_jobs = job_store.list_jobs()
        persisted: list[dict[str, Any]] = []
        for path in sorted(settings.outputs_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            persisted.append(
                {
                    "id": data.get("id", path.stem),
                    "dataset_type": data.get("dataset_type"),
                    "dataset_name": data.get("dataset_name"),
                    "model": data.get("model"),
                    "status": data.get("status"),
                    "created_at": data.get("created_at"),
                    "finished_at": data.get("finished_at"),
                    "output_file": str(path),
                    "metrics": data.get("metrics", {}),
                }
            )
        seen_ids = {item["id"] for item in live_jobs}
        for item in persisted:
            if item["id"] not in seen_ids:
                live_jobs.append(item)
        return sorted(
            live_jobs,
            key=lambda item: item.get("created_at", ""),
            reverse=True,
        )

    def get_job(self, job_id: str) -> dict[str, Any]:
        try:
            return job_store.get(job_id)
        except KeyError as exc:
            persisted_file = settings.outputs_dir / f"{job_id}.json"
            if persisted_file.exists():
                return json.loads(persisted_file.read_text(encoding="utf-8"))
            raise HTTPException(status_code=404, detail="评测任务不存在。") from exc

    def start(self, request: EvaluationRequest) -> dict[str, Any]:
        dataset_path = Path(request.dataset_path)
        if not dataset_path.is_absolute():
            raise HTTPException(status_code=422, detail="数据集路径必须是绝对路径。")
        if not dataset_path.exists():
            raise HTTPException(status_code=404, detail="数据集路径不存在。")
        if not dataset_path.is_dir():
            raise HTTPException(status_code=422, detail="数据集路径必须是目录。")

        evaluator = registry.detect(dataset_path) if request.dataset_type == "auto" else registry.get(request.dataset_type)
        if request.dataset_type != "auto" and not evaluator.can_handle(dataset_path):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"当前路径与 {evaluator.label} 目录结构不匹配。"
                    " 请检查目录组织或改用自动识别。"
                ),
            )

        job_id = str(uuid.uuid4())
        job = {
            "id": job_id,
            "status": "queued",
            "dataset_type": evaluator.key,
            "dataset_name": evaluator.label,
            "dataset_path": str(dataset_path),
            "model": request.model,
            "base_url": request.base_url,
            "base_url_display": request.base_url,
            "api_key_masked": mask_api_key(request.api_key),
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "started_at": None,
            "finished_at": None,
            "output_file": None,
            "error_message": None,
            "request": request.model_dump(exclude={"api_key"}),
            "progress": {
                "total": 0,
                "completed": 0,
                "success": 0,
                "failed": 0,
                "correct": 0,
                "parsable": 0,
            },
            "metrics": {},
            "sample_results": [],
            "logs": [],
        }
        job_store.create(job)
        job_store.append_log(job_id, f"任务已创建，评测集={evaluator.label}，模型={request.model}")
        asyncio.create_task(self._run_job(job_id, request, evaluator.key))
        return job_store.get(job_id)

    async def _run_job(self, job_id: str, request: EvaluationRequest, dataset_key: str) -> None:
        try:
            evaluator = registry.get(dataset_key)
            started_at = time.perf_counter()
            job_store.update(job_id, status="running", started_at=utc_now())
            job_store.append_log(job_id, f"开始加载数据集：{request.dataset_path}")

            try:
                # Dataset loading can involve local archive parsing or Hugging Face downloads.
                # Run it off the event loop so status polling remains responsive.
                dataset = await asyncio.to_thread(
                    evaluator.load,
                    Path(request.dataset_path),
                    request.max_samples,
                    request.few_shot,
                )
                job_store.patch_progress(job_id, total=len(dataset.samples))
                job_store.append_log(job_id, f"数据集加载完成，共 {len(dataset.samples)} 条样本。")
            except Exception as exc:
                await self._mark_failed(job_id, f"数据集加载失败：{exc}")
                return

            client = OpenAICompatibleClient(
                base_url=request.base_url,
                api_key=request.api_key,
                model=request.model,
                timeout_seconds=request.timeout_seconds,
            )

            semaphore = asyncio.Semaphore(request.concurrency)

            async def worker(sample_index: int, sample) -> None:
                async with semaphore:
                    sample_started = time.perf_counter()
                    prompt = evaluator.build_prompt(sample, dataset, request.few_shot)
                    try:
                        raw_output = await client.complete(prompt, temperature=request.temperature)
                        parsed_answer = evaluator.parse_prediction(raw_output, sample)
                        is_correct = evaluator.is_correct(sample, parsed_answer)
                        error_reason = None if parsed_answer else "模型输出中未成功解析出答案。"
                        result_status = "ok"
                        success_delta = 1
                        failed_delta = 0
                        parsable_delta = 1 if parsed_answer else 0
                        correct_delta = 1 if is_correct else 0
                    except ModelClientError as exc:
                        raw_output = ""
                        parsed_answer = None
                        is_correct = False
                        error_reason = str(exc)
                        result_status = "error"
                        success_delta = 0
                        failed_delta = 1
                        parsable_delta = 0
                        correct_delta = 0
                    except Exception as exc:
                        raw_output = ""
                        parsed_answer = None
                        is_correct = False
                        error_reason = f"评测异常：{exc}"
                        result_status = "error"
                        success_delta = 0
                        failed_delta = 1
                        parsable_delta = 0
                        correct_delta = 0

                    elapsed = round(time.perf_counter() - sample_started, 4)
                    result = {
                        "sample_id": sample.sample_id,
                        "group": sample.group,
                        "question_summary": evaluator.summarize_question(sample),
                        "question": sample.question,
                        "raw_output": raw_output,
                        "parsed_answer": parsed_answer,
                        "reference_answer": sample.answer,
                        "is_correct": is_correct,
                        "status": result_status,
                        "error_reason": error_reason,
                        "elapsed_seconds": elapsed,
                        "options": sample.options,
                    }
                    job_store.add_sample_result(job_id, result)
                    snapshot = job_store.get(job_id)
                    progress = snapshot["progress"]
                    job_store.patch_progress(
                        job_id,
                        completed=progress["completed"] + 1,
                        success=progress["success"] + success_delta,
                        failed=progress["failed"] + failed_delta,
                        correct=progress["correct"] + correct_delta,
                        parsable=progress["parsable"] + parsable_delta,
                    )
                    if result_status == "error":
                        job_store.append_log(
                            job_id,
                            f"[{sample.sample_id}] 调用失败：{error_reason}",
                        )
                    else:
                        verdict = "正确" if is_correct else "错误"
                        job_store.append_log(
                            job_id,
                            f"[{sample.sample_id}] 完成，解析答案={parsed_answer or 'N/A'}，判定={verdict}",
                        )

            await asyncio.gather(*(worker(idx, sample) for idx, sample in enumerate(dataset.samples)))

            snapshot = job_store.get(job_id)
            progress = snapshot["progress"]
            total_elapsed = round(time.perf_counter() - started_at, 4)
            total = max(progress["total"], 1)
            metrics = {
                "total_questions": progress["total"],
                "completed_questions": progress["completed"],
                "success_questions": progress["success"],
                "failed_questions": progress["failed"],
                "parsable_questions": progress["parsable"],
                "correct_questions": progress["correct"],
                "accuracy": round(progress["correct"] / total, 4),
                "avg_seconds_per_question": round(total_elapsed / total, 4),
                "total_elapsed_seconds": total_elapsed,
            }
            output_file = self._persist_job(
                {
                    **snapshot,
                    "status": "completed",
                    "finished_at": utc_now(),
                    "metrics": metrics,
                }
            )
            job_store.update(
                job_id,
                status="completed",
                finished_at=utc_now(),
                metrics=metrics,
                output_file=str(output_file),
            )
            job_store.append_log(job_id, f"评测完成，结果已保存到 {output_file}")
        except Exception as exc:
            await self._mark_failed(job_id, f"后台任务异常终止：{exc}")

    async def _mark_failed(self, job_id: str, message: str) -> None:
        output_file = self._persist_job(
            {
                **job_store.get(job_id),
                "status": "failed",
                "finished_at": utc_now(),
                "error_message": message,
            }
        )
        job_store.update(
            job_id,
            status="failed",
            finished_at=utc_now(),
            error_message=message,
            output_file=str(output_file),
        )
        job_store.append_log(job_id, message)

    def _persist_job(self, payload: dict[str, Any]) -> Path:
        filename = f"{payload['id']}.json"
        target = settings.outputs_dir / filename
        persisted_payload = {**payload, "output_file": str(target)}
        target.write_text(
            json.dumps(persisted_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target


evaluation_service = EvaluationService()
