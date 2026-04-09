from __future__ import annotations

import csv
import hashlib
import io
import random
import zipfile
from pathlib import Path

from app.evaluators.base import MultipleChoiceEvaluator
from app.evaluators.common.models import EvaluationSample, PreparedDataset


class GPQAEvaluator(MultipleChoiceEvaluator):
    key = "gpqa"
    label = "GPQA"
    description = "Graduate-level multiple-choice science questions from dataset.zip or dataset/gpqa_*.csv."

    _zip_password = b"deserted-untie-orchid"

    def can_handle(self, dataset_path: Path) -> bool:
        return bool(
            (dataset_path / "dataset.zip").is_file()
            or any((dataset_path / "dataset").glob("gpqa_*.csv"))
            or any(dataset_path.glob("gpqa_*.csv"))
        )

    def load(self, dataset_path: Path, max_samples: int, few_shot: int) -> PreparedDataset:
        file_contents = self._load_csv_sources(dataset_path)
        if not file_contents:
            raise ValueError("GPQA 目录格式不正确，需包含 dataset.zip 或 dataset/gpqa_*.csv。")

        samples: list[EvaluationSample] = []
        demonstrations: dict[str, list[EvaluationSample]] = {}
        for group, content in file_contents:
            if len(samples) >= max_samples:
                break
            group_samples = self._convert_csv(group, content)
            if not group_samples:
                continue
            demonstrations[group] = group_samples
            samples.extend(group_samples[: max_samples - len(samples)])

        return PreparedDataset(
            dataset_key=self.key,
            dataset_name=self.label,
            dataset_path=str(dataset_path),
            samples=samples[:max_samples],
            demonstrations_by_group=demonstrations,
        )

    def build_prompt(
        self, sample: EvaluationSample, dataset: PreparedDataset, few_shot: int
    ) -> str:
        parts = [
            (
                "You are answering a graduate-level GPQA multiple-choice question. "
                "Choose the best option and end with `Final Answer: X`."
            )
        ]
        demos = [
            item
            for item in dataset.demonstrations_by_group.get(sample.group, [])
            if item.sample_id != sample.sample_id
        ][:few_shot]
        for demo in demos:
            parts.append(self.format_question_block(demo))
            parts.append(f"{self.answer_prefix}: {demo.answer}")
        parts.append(self.format_question_block(sample))
        parts.append(f"{self.answer_prefix}:")
        return "\n\n".join(parts)

    def _load_csv_sources(self, dataset_path: Path) -> list[tuple[str, str]]:
        zip_path = dataset_path / "dataset.zip"
        if zip_path.is_file():
            items: list[tuple[str, str]] = []
            with zipfile.ZipFile(zip_path) as archive:
                for name in sorted(item for item in archive.namelist() if item.endswith(".csv")):
                    text = archive.read(name, pwd=self._zip_password).decode("utf-8")
                    items.append((Path(name).stem, text))
            return items

        csv_dir = dataset_path / "dataset" if (dataset_path / "dataset").is_dir() else dataset_path
        return [
            (path.stem, path.read_text(encoding="utf-8"))
            for path in sorted(csv_dir.glob("gpqa_*.csv"))
        ]

    def _convert_csv(self, group: str, content: str) -> list[EvaluationSample]:
        rows = csv.DictReader(io.StringIO(content))
        samples: list[EvaluationSample] = []
        for index, row in enumerate(rows):
            question = (
                row.get("Question")
                or row.get("Extra Revised Question")
                or row.get("Pre-Revision Question")
                or ""
            ).strip()
            explanation = (
                row.get("Explanation")
                or row.get("Extra Revised Explanation")
                or row.get("Pre-Revision Explanation")
                or ""
            ).strip()
            correct = (
                row.get("Correct Answer")
                or row.get("Extra Revised Correct Answer")
                or row.get("Pre-Revision Correct Answer")
                or ""
            ).strip()
            incorrects = [
                (
                    row.get(f"Incorrect Answer {position}")
                    or row.get(f"Extra Revised Incorrect Answer {position}")
                    or row.get(f"Pre-Revision Incorrect Answer {position}")
                    or ""
                ).strip()
                for position in range(1, 4)
            ]
            if not question or not correct or any(not item for item in incorrects):
                continue

            sample_id = str(row.get("Record ID") or f"{group}-{index}")
            shuffled = [(correct, True), *[(item, False) for item in incorrects]]
            random.Random(hashlib.md5(sample_id.encode("utf-8")).hexdigest()).shuffle(shuffled)
            answer_index = next(idx for idx, (_, is_correct) in enumerate(shuffled) if is_correct)

            samples.append(
                EvaluationSample(
                    sample_id=sample_id,
                    group=group,
                    question=question,
                    options=[text for text, _ in shuffled],
                    answer=chr(65 + answer_index),
                    answer_index=answer_index,
                    explanation=explanation,
                    metadata={
                        "subdomain": str(row.get("Subdomain") or "").strip(),
                        "domain": str(row.get("High-level domain") or "").strip(),
                    },
                )
            )
        return samples
