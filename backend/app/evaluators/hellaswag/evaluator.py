from __future__ import annotations

from pathlib import Path

from app.evaluators.base import MultipleChoiceEvaluator
from app.evaluators.common.io import load_json_records
from app.evaluators.common.models import EvaluationSample, PreparedDataset


class HellaSwagEvaluator(MultipleChoiceEvaluator):
    key = "hellaswag"
    label = "HellaSwag"
    description = "Commonsense completion benchmark with train/val/test JSONL files under data/."

    def can_handle(self, dataset_path: Path) -> bool:
        data_dir = self._resolve_data_dir(dataset_path)
        return bool(data_dir and (data_dir / "hellaswag_val.jsonl").is_file())

    def load(self, dataset_path: Path, max_samples: int, few_shot: int) -> PreparedDataset:
        data_dir = self._resolve_data_dir(dataset_path)
        if not data_dir:
            raise ValueError("HellaSwag 目录格式不正确，需包含 data/hellaswag_val.jsonl。")

        demos = (
            self._load_split(data_dir / "hellaswag_train.jsonl")
            if few_shot > 0 and (data_dir / "hellaswag_train.jsonl").is_file()
            else {}
        )
        samples = self._load_split(data_dir / "hellaswag_val.jsonl", limit=max_samples)

        return PreparedDataset(
            dataset_key=self.key,
            dataset_name=self.label,
            dataset_path=str(dataset_path),
            samples=samples[:max_samples],
            demonstrations_by_group=demos,
        )

    def build_prompt(
        self, sample: EvaluationSample, dataset: PreparedDataset, few_shot: int
    ) -> str:
        parts = [
            (
                "You are answering a HellaSwag commonsense completion question. "
                "Choose the most plausible ending and end with `Final Answer: X`."
            )
        ]
        for demo in self.get_demos(dataset, sample.group, few_shot):
            parts.append(self._format_question(demo))
            parts.append(f"{self.answer_prefix}: {demo.answer}")
        parts.append(self._format_question(sample))
        parts.append(f"{self.answer_prefix}:")
        return "\n\n".join(parts)

    def _resolve_data_dir(self, dataset_path: Path) -> Path | None:
        if (dataset_path / "data").is_dir():
            return dataset_path / "data"
        if (dataset_path / "hellaswag_val.jsonl").is_file():
            return dataset_path
        return None

    def _load_split(
        self,
        path: Path,
        limit: int | None = None,
    ) -> dict[str, list[EvaluationSample]] | list[EvaluationSample]:
        records = load_json_records(path)
        samples: list[EvaluationSample] = []
        for record in records:
            if limit is not None and len(samples) >= limit:
                break
            if not isinstance(record, dict):
                continue
            label = record.get("label")
            if label in {None, ""}:
                continue
            answer_index = int(label)
            group = str(record.get("activity_label") or "hellaswag").strip() or "hellaswag"
            samples.append(
                EvaluationSample(
                    sample_id=str(record.get("ind")),
                    group=group,
                    question=str(record.get("ctx") or "").strip(),
                    options=[str(item).strip() for item in record.get("endings", [])],
                    answer=chr(65 + answer_index),
                    answer_index=answer_index,
                    metadata={
                        "activity_label": group,
                        "split_type": str(record.get("split_type") or "").strip(),
                        "source_id": str(record.get("source_id") or "").strip(),
                    },
                )
            )

        if path.name.endswith("_train.jsonl"):
            grouped: dict[str, list[EvaluationSample]] = {}
            for sample in samples:
                grouped.setdefault(sample.group, []).append(sample)
            return grouped
        return samples

    def _format_question(self, sample: EvaluationSample) -> str:
        option_lines = [f"{chr(65 + index)}. {option}" for index, option in enumerate(sample.options)]
        return "\n".join(
            [
                f"Context:\n{sample.question}",
                "Endings:",
                *option_lines,
            ]
        )
