from __future__ import annotations

import json
import zipfile
from pathlib import Path

from app.core.config import settings
from datasets import load_dataset
from app.evaluators.base import MultipleChoiceEvaluator
from app.evaluators.common.io import first_existing_dir, load_json_records
from app.evaluators.common.models import EvaluationSample, PreparedDataset
from app.evaluators.common.sampling import choose_random_samples


class MMLUProEvaluator(MultipleChoiceEvaluator):
    key = "mmlu_pro"
    label = "MMLU-Pro"
    description = "Extended multi-choice benchmark with JSON/JSONL validation and test files."

    def can_handle(self, dataset_path: Path) -> bool:
        validation_dir = first_existing_dir(dataset_path, ["validation", "val", "data/validation"])
        test_dir = first_existing_dir(dataset_path, ["test", "data/test"])
        if validation_dir and test_dir:
            return True
        if (dataset_path / "eval_results").is_dir() and (dataset_path / "README.md").exists():
            return True
        return bool((dataset_path / "evaluate_from_local.py").exists())

    def load(
        self, dataset_path: Path, max_samples: int, few_shot: int, random_seed: int
    ) -> PreparedDataset:
        validation_dir = first_existing_dir(dataset_path, ["validation", "val", "data/validation"])
        test_dir = first_existing_dir(dataset_path, ["test", "data/test"])
        if validation_dir and test_dir:
            demonstrations: dict[str, list[EvaluationSample]] = {}
            for path in sorted(validation_dir.glob("*")):
                if path.suffix not in {".json", ".jsonl"}:
                    continue
                for sample in self._load_records(path):
                    demonstrations.setdefault(sample.group, []).append(sample)

            samples: list[EvaluationSample] = []
            for path in sorted(test_dir.glob("*")):
                if path.suffix not in {".json", ".jsonl"}:
                    continue
                samples.extend(self._load_records(path))
        else:
            demonstrations, samples = self._load_from_official_repo_root(dataset_path)

        return PreparedDataset(
            dataset_key=self.key,
            dataset_name=self.label,
            dataset_path=str(dataset_path),
            samples=choose_random_samples(samples, max_samples, random_seed),
            demonstrations_by_group=demonstrations,
        )

    def _load_from_official_repo_root(
        self, dataset_path: Path
    ) -> tuple[dict[str, list[EvaluationSample]], list[EvaluationSample]]:
        zip_candidates = sorted((dataset_path / "eval_results").glob("model_outputs_*.zip"))
        if zip_candidates:
            zip_path = zip_candidates[0]
            # Prefer the official result archive shipped with the repository before using network fallback.
            with zipfile.ZipFile(zip_path) as archive:
                inner_name = next(
                    (name for name in archive.namelist() if name.endswith(".json")),
                    None,
                )
                if inner_name:
                    payload = json.loads(archive.read(inner_name).decode("utf-8"))
                    samples = self._convert_records(payload)
                    demos = self._make_demo_map(samples)
                    return demos, samples

        try:
            dataset = load_dataset("TIGER-Lab/MMLU-Pro", cache_dir=str(settings.hf_cache_dir))
        except Exception as exc:
            raise ValueError(
                "检测到传入路径为官方 MMLU-Pro 仓库根目录，但本地目录中没有 validation/test 原始数据。"
                "系统已尝试优先使用 eval_results 中的官方结果包，未命中后再从官方数据源 "
                f"TIGER-Lab/MMLU-Pro 拉取，最终失败：{exc}"
            ) from exc
        validation = self._convert_records(list(dataset["validation"]))
        test = self._convert_records(list(dataset["test"]))
        return self._make_demo_map(validation), test

    def _convert_records(self, records: list[dict]) -> list[EvaluationSample]:
        samples: list[EvaluationSample] = []
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            options = [item for item in record.get("options", []) if str(item).strip() and str(item) != "N/A"]
            answer = str(record.get("answer", "")).strip().upper()
            category = str(record.get("category", "general")).strip() or "general"
            answer_index = record.get("answer_index")
            if answer_index is None and answer:
                answer_index = ord(answer) - 65
            samples.append(
                EvaluationSample(
                    sample_id=str(record.get("question_id") or record.get("id") or index),
                    group=category,
                    question=str(record.get("question", "")).strip(),
                    options=[str(option).strip() for option in options],
                    answer=answer,
                    answer_index=int(answer_index) if answer_index is not None else None,
                    explanation=str(record.get("cot_content", "")).strip(),
                    metadata={
                        "category": category,
                        "source": str(record.get("src", "")),
                    },
                )
            )
        return samples

    def _make_demo_map(
        self, samples: list[EvaluationSample]
    ) -> dict[str, list[EvaluationSample]]:
        demos: dict[str, list[EvaluationSample]] = {}
        for sample in samples:
            demos.setdefault(sample.group, []).append(sample)
        return demos

    def _load_records(self, path: Path) -> list[EvaluationSample]:
        records = load_json_records(path)
        samples = self._convert_records(records)
        for sample in samples:
            sample.metadata["source_file"] = path.name
        return samples
