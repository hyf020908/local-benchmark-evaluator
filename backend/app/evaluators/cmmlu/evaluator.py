from __future__ import annotations

from pathlib import Path

from app.evaluators.base import MultipleChoiceEvaluator
from app.evaluators.common.io import first_existing_dir, list_csv_files, normalize_stem, read_csv_rows
from app.evaluators.common.models import EvaluationSample, PreparedDataset


class CMMLUEvaluator(MultipleChoiceEvaluator):
    key = "cmmlu"
    label = "CMMLU"
    description = "Chinese multitask benchmark with CSVs under data/dev and data/test."

    def can_handle(self, dataset_path: Path) -> bool:
        dev_dir = first_existing_dir(dataset_path, ["data/dev", "dev"])
        test_dir = first_existing_dir(dataset_path, ["data/test", "test"])
        return bool(dev_dir and test_dir and list_csv_files(dev_dir) and list_csv_files(test_dir))

    def load(self, dataset_path: Path, max_samples: int, few_shot: int) -> PreparedDataset:
        dev_dir = first_existing_dir(dataset_path, ["data/dev", "dev"])
        test_dir = first_existing_dir(dataset_path, ["data/test", "test"])
        if not dev_dir or not test_dir:
            raise ValueError("CMMLU 数据目录格式不正确，需包含 data/dev 与 data/test。")

        demonstrations: dict[str, list[EvaluationSample]] = {}
        for path in list_csv_files(dev_dir):
            subject = normalize_stem(path, [])
            demonstrations[subject] = self._load_rows(path, subject)

        samples: list[EvaluationSample] = []
        for path in list_csv_files(test_dir):
            subject = normalize_stem(path, [])
            samples.extend(self._load_rows(path, subject))

        return PreparedDataset(
            dataset_key=self.key,
            dataset_name=self.label,
            dataset_path=str(dataset_path),
            samples=samples[:max_samples],
            demonstrations_by_group=demonstrations,
        )

    def _load_rows(self, csv_path: Path, subject: str) -> list[EvaluationSample]:
        rows = read_csv_rows(csv_path)
        if not rows:
            return []

        header = [item.strip().lower() for item in rows[0]]
        has_header = "question" in header
        data_rows = rows[1:] if has_header else rows

        samples: list[EvaluationSample] = []
        for index, row in enumerate(data_rows):
            if len(row) < 6:
                continue
            if has_header:
                mapping = {name: idx for idx, name in enumerate(header)}
                if "question" not in mapping:
                    continue
                question = row[mapping["question"]].strip()
                answer = row[mapping["answer"]].strip().upper()
                options = [row[mapping["a"]], row[mapping["b"]], row[mapping["c"]], row[mapping["d"]]]
                sample_id = row[mapping.get("", 0)].strip() if "" in mapping else f"{subject}-{index}"
            else:
                if len(row) == 7:
                    question = row[0].strip()
                    options = [row[1], row[2], row[3], row[4]]
                    answer = row[5].strip().upper()
                    sample_id = f"{subject}-{index}"
                else:
                    sample_id = row[0].strip() or f"{subject}-{index}"
                    question = row[1].strip()
                    options = [row[2], row[3], row[4], row[5]]
                    answer = row[6].strip().upper()
            samples.append(
                EvaluationSample(
                    sample_id=str(sample_id),
                    group=subject,
                    question=question,
                    options=[option.strip() for option in options],
                    answer=answer,
                    answer_index=ord(answer) - 65,
                    metadata={"subject": subject},
                )
            )
        return samples
