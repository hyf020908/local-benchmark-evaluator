from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from app.evaluators.base import NumericAnswerEvaluator
from app.evaluators.common.io import load_json_records
from app.evaluators.common.models import EvaluationSample, PreparedDataset


class GSM8KEvaluator(NumericAnswerEvaluator):
    key = "gsm8k"
    label = "GSM8K"
    description = "Grade-school math benchmark using local train/test JSONL or JSON files."

    def can_handle(self, dataset_path: Path) -> bool:
        return any(
            (dataset_path / filename).exists()
            for filename in ["train.jsonl", "train.json", "test.jsonl", "test.json"]
        ) or any(
            (dataset_path / "data" / filename).exists()
            for filename in ["train.jsonl", "train.json", "test.jsonl", "test.json"]
        )

    def load(self, dataset_path: Path, max_samples: int, few_shot: int) -> PreparedDataset:
        base_dir = dataset_path / "data" if (dataset_path / "data").is_dir() else dataset_path
        train_path = self._find_file(base_dir, ["train.jsonl", "train.json"])
        test_path = self._find_file(base_dir, ["test.jsonl", "test.json"])
        if not train_path or not test_path:
            raise ValueError("GSM8K 需要 train.jsonl/train.json 与 test.jsonl/test.json。")

        demos = {"gsm8k": self._load_records(train_path)}
        samples = self._load_records(test_path)

        return PreparedDataset(
            dataset_key=self.key,
            dataset_name=self.label,
            dataset_path=str(dataset_path),
            samples=samples[:max_samples],
            demonstrations_by_group=demos,
        )

    def _find_file(self, base_dir: Path, filenames: list[str]) -> Optional[Path]:
        for filename in filenames:
            target = base_dir / filename
            if target.exists():
                return target
        return None

    def _load_records(self, path: Path) -> list[EvaluationSample]:
        records = load_json_records(path)
        samples: list[EvaluationSample] = []
        for index, record in enumerate(records):
            answer_text = str(record.get("answer", "")).strip()
            final_answer = self._extract_reference_answer(answer_text)
            samples.append(
                EvaluationSample(
                    sample_id=str(record.get("id") or record.get("question_id") or index),
                    group="gsm8k",
                    question=str(record.get("question", "")).strip(),
                    answer=final_answer,
                    explanation=answer_text,
                )
            )
        return samples

    def _extract_reference_answer(self, answer_text: str) -> str:
        match = re.search(r"####\s*([-+]?[0-9][0-9,]*(?:\.[0-9]+)?)", answer_text)
        if match:
            return self.normalize_number(match.group(1))
        fallback = re.findall(r"[-+]?[0-9][0-9,]*(?:\.[0-9]+)?", answer_text)
        if not fallback:
            raise ValueError("GSM8K 标准答案中未找到数值。")
        return self.normalize_number(fallback[-1])
