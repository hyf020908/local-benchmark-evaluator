from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._jobs[payload["id"]] = copy.deepcopy(payload)
        return self.get(payload["id"])

    def get(self, job_id: str) -> dict[str, Any]:
        if job_id not in self._jobs:
            raise KeyError(job_id)
        return copy.deepcopy(self._jobs[job_id])

    def update(self, job_id: str, **changes: Any) -> dict[str, Any]:
        if job_id not in self._jobs:
            raise KeyError(job_id)
        self._jobs[job_id].update(changes)
        self._jobs[job_id]["updated_at"] = utc_now()
        return self.get(job_id)

    def patch_progress(self, job_id: str, **changes: Any) -> dict[str, Any]:
        if job_id not in self._jobs:
            raise KeyError(job_id)
        progress = self._jobs[job_id].setdefault("progress", {})
        progress.update(changes)
        self._jobs[job_id]["updated_at"] = utc_now()
        return self.get(job_id)

    def append_log(self, job_id: str, message: str) -> dict[str, Any]:
        if job_id not in self._jobs:
            raise KeyError(job_id)
        logs = self._jobs[job_id].setdefault("logs", [])
        logs.append(f"[{utc_now()}] {message}")
        self._jobs[job_id]["updated_at"] = utc_now()
        return self.get(job_id)

    def add_sample_result(self, job_id: str, result: dict[str, Any]) -> dict[str, Any]:
        if job_id not in self._jobs:
            raise KeyError(job_id)
        results = self._jobs[job_id].setdefault("sample_results", [])
        results.append(result)
        self._jobs[job_id]["updated_at"] = utc_now()
        return self.get(job_id)

    def list_jobs(self) -> list[dict[str, Any]]:
        items = [copy.deepcopy(item) for item in self._jobs.values()]
        return sorted(items, key=lambda item: item["created_at"], reverse=True)


job_store = JobStore()
