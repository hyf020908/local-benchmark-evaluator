from __future__ import annotations

from pathlib import Path

from app.evaluators.base import MultipleChoiceEvaluator
from app.evaluators.common.io import first_existing_dir, list_csv_files, normalize_stem, read_csv_rows
from app.evaluators.common.models import EvaluationSample, PreparedDataset


class MMLUEvaluator(MultipleChoiceEvaluator):
    key = "mmlu"
    label = "MMLU"
    description = "English four-choice benchmark with dev/val/test CSV files."

    def can_handle(self, dataset_path: Path) -> bool:
        dev_dir = first_existing_dir(dataset_path, ["data/dev", "dev"])
        test_dir = first_existing_dir(dataset_path, ["data/test", "data/val", "test", "val"])
        if not dev_dir or not test_dir:
            return False
        dev_files = list_csv_files(dev_dir)
        test_files = list_csv_files(test_dir)
        return any(path.name.endswith("_dev.csv") for path in dev_files) and any(
            path.name.endswith("_test.csv") or path.name.endswith("_val.csv")
            for path in test_files
        )

    def load(self, dataset_path: Path, max_samples: int, few_shot: int) -> PreparedDataset:
        dev_dir = first_existing_dir(dataset_path, ["data/dev", "dev"])
        test_dir = first_existing_dir(dataset_path, ["data/test", "data/val", "test", "val"])
        if not dev_dir or not test_dir:
            raise ValueError("MMLU 数据目录格式不正确，需包含 dev 与 test/val 子目录。")

        demonstrations: dict[str, list[EvaluationSample]] = {}
        for path in list_csv_files(dev_dir):
            subject = normalize_stem(path, ["_dev"])
            demonstrations[subject] = self._load_rows(path, subject)

        samples: list[EvaluationSample] = []
        for path in list_csv_files(test_dir):
            subject = normalize_stem(path, ["_test", "_val"])
            subject_samples = self._load_rows(path, subject)
            samples.extend(subject_samples)

        return PreparedDataset(
            dataset_key=self.key,
            dataset_name=self.label,
            dataset_path=str(dataset_path),
            samples=samples[:max_samples],
            demonstrations_by_group=demonstrations,
        )

    def _load_rows(self, csv_path: Path, subject: str) -> list[EvaluationSample]:
        rows = read_csv_rows(csv_path)
        samples: list[EvaluationSample] = []
        for index, row in enumerate(rows):
            if len(row) < 6:
                continue
            samples.append(
                EvaluationSample(
                    sample_id=f"{subject}-{index}",
                    group=subject,
                    question=row[0].strip(),
                    options=[row[1].strip(), row[2].strip(), row[3].strip(), row[4].strip()],
                    answer=row[5].strip().upper(),
                    answer_index=ord(row[5].strip().upper()) - 65,
                    metadata={"subject": subject},
                )
            )
        return samples
