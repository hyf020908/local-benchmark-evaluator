from __future__ import annotations

from pathlib import Path

from app.evaluators.base import MultipleChoiceEvaluator
from app.evaluators.common.io import load_json_records
from app.evaluators.common.models import EvaluationSample, PreparedDataset


class TruthfulQAEvaluator(MultipleChoiceEvaluator):
    key = "truthfulqa"
    label = "TruthfulQA"
    description = "Official TruthfulQA repository using local mc_task.json multiple-choice data."

    def can_handle(self, dataset_path: Path) -> bool:
        return (dataset_path / "TruthfulQA.csv").exists() and (
            dataset_path / "data" / "mc_task.json"
        ).exists()

    def load(self, dataset_path: Path, max_samples: int, few_shot: int) -> PreparedDataset:
        mc_path = dataset_path / "data" / "mc_task.json"
        if not mc_path.exists():
            raise ValueError("TruthfulQA 目录缺少 data/mc_task.json。")

        records = load_json_records(mc_path)
        samples: list[EvaluationSample] = []
        demos: list[EvaluationSample] = []

        for index, record in enumerate(records):
            targets = record.get("mc0_targets") or {}
            if not targets:
                continue
            options = list(targets.keys())
            answer_index = next(
                (idx for idx, option in enumerate(options) if int(targets[option]) == 1),
                None,
            )
            if answer_index is None:
                continue
            answer = chr(65 + answer_index)
            sample = EvaluationSample(
                sample_id=str(index),
                group="truthfulqa",
                question=str(record.get("question", "")).strip(),
                options=options,
                answer=answer,
                answer_index=answer_index,
                metadata={"source": "mc0_targets"},
            )
            if len(demos) < max(2, few_shot):
                demos.append(sample)
            samples.append(sample)

        return PreparedDataset(
            dataset_key=self.key,
            dataset_name=self.label,
            dataset_path=str(dataset_path),
            samples=samples[:max_samples],
            demonstrations_by_group={"truthfulqa": demos},
        )
