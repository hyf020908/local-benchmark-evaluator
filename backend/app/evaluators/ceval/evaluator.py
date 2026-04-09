from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from datasets import load_dataset
from app.evaluators.base import MultipleChoiceEvaluator
from app.evaluators.common.io import first_existing_dir, list_csv_files, normalize_stem, read_csv_rows
from app.evaluators.common.models import EvaluationSample, PreparedDataset


class CEvalEvaluator(MultipleChoiceEvaluator):
    key = "ceval"
    label = "C-Eval"
    description = "Chinese exam benchmark with *_dev.csv and *_val.csv files."

    def can_handle(self, dataset_path: Path) -> bool:
        dev_dir = first_existing_dir(dataset_path, ["data/dev", "dev"])
        val_dir = first_existing_dir(dataset_path, ["data/val", "val", "data/test", "test"])
        if not dev_dir or not val_dir:
            return bool((dataset_path / "subject_mapping.json").exists() and (dataset_path / "README.md").exists())
        return any(path.name.endswith("_dev.csv") for path in list_csv_files(dev_dir)) or bool(
            (dataset_path / "subject_mapping.json").exists()
        )

    def load(self, dataset_path: Path, max_samples: int, few_shot: int) -> PreparedDataset:
        dev_dir = first_existing_dir(dataset_path, ["data/dev", "dev"])
        eval_dir = first_existing_dir(dataset_path, ["data/val", "val", "data/test", "test"])
        if dev_dir and eval_dir:
            demonstrations: dict[str, list[EvaluationSample]] = {}
            for path in list_csv_files(dev_dir):
                subject = normalize_stem(path, ["_dev"])
                demonstrations[subject] = self._load_rows(path, subject)

            samples: list[EvaluationSample] = []
            for path in list_csv_files(eval_dir):
                subject = normalize_stem(path, ["_val", "_test"])
                samples.extend(self._load_rows(path, subject))
        elif (dataset_path / "subject_mapping.json").exists():
            demonstrations, samples = self._load_from_official_repo_root(dataset_path, max_samples)
        else:
            raise ValueError(
                "C-Eval 数据目录格式不正确，需包含 data/dev 与 data/val；"
                "若传入官方 ceval 仓库根目录，系统将尝试从官方 Hugging Face 数据源读取。"
            )

        return PreparedDataset(
            dataset_key=self.key,
            dataset_name=self.label,
            dataset_path=str(dataset_path),
            samples=samples[:max_samples],
            demonstrations_by_group=demonstrations,
        )

    def _load_from_official_repo_root(
        self, dataset_path: Path, max_samples: int
    ) -> tuple[dict[str, list[EvaluationSample]], list[EvaluationSample]]:
        import json

        subject_mapping = json.loads((dataset_path / "subject_mapping.json").read_text(encoding="utf-8"))
        subjects = list(subject_mapping.keys())
        demonstrations: dict[str, list[EvaluationSample]] = {}
        samples: list[EvaluationSample] = []

        # The official repository root does not consistently include raw CSV files.
        # In that case, load the authoritative split definitions from Hugging Face.
        for subject in subjects:
            try:
                dataset = load_dataset(
                    "ceval/ceval-exam",
                    name=subject,
                    cache_dir=str(settings.hf_cache_dir),
                )
            except Exception as exc:
                raise ValueError(
                    "检测到传入路径为官方 ceval 仓库根目录，但本地目录中不包含题目数据。"
                    "系统已尝试从官方 Hugging Face 数据源 ceval/ceval-exam 拉取，"
                    f"但失败了：{exc}"
                ) from exc
            demonstrations[subject] = self._convert_hf_split(subject, list(dataset["dev"]))
            eval_split = "test" if "test" in dataset else "val"
            samples.extend(self._convert_hf_split(subject, list(dataset[eval_split])))
            if len(samples) >= max_samples:
                break

        return demonstrations, samples

    def _convert_hf_split(
        self, subject: str, records: list[dict]
    ) -> list[EvaluationSample]:
        samples: list[EvaluationSample] = []
        for index, record in enumerate(records):
            answer = str(record.get("answer", "")).strip().upper()
            samples.append(
                EvaluationSample(
                    sample_id=str(record.get("id", f"{subject}-{index}")),
                    group=subject,
                    question=str(record.get("question", "")).strip(),
                    options=[
                        str(record.get("A", "")).strip(),
                        str(record.get("B", "")).strip(),
                        str(record.get("C", "")).strip(),
                        str(record.get("D", "")).strip(),
                    ],
                    answer=answer,
                    answer_index=ord(answer) - 65 if answer else None,
                    explanation=str(record.get("explanation", "")).strip(),
                    metadata={"subject": subject, "source": "hf"},
                )
            )
        return samples

    def _load_rows(self, csv_path: Path, subject: str) -> list[EvaluationSample]:
        rows = read_csv_rows(csv_path)
        if not rows:
            return []
        header = [item.strip().lower() for item in rows[0]]
        data_rows = rows[1:] if "question" in header else rows

        samples: list[EvaluationSample] = []
        for index, row in enumerate(data_rows):
            if len(row) < 7:
                continue
            if "question" in header:
                mapping = {name: idx for idx, name in enumerate(header)}
                question = row[mapping["question"]].strip()
                answer = row[mapping["answer"]].strip().upper()
                sample_id = row[mapping.get("id", 0)].strip() or f"{subject}-{index}"
                explanation = row[mapping["explanation"]].strip() if "explanation" in mapping and len(row) > mapping["explanation"] else ""
                options = [row[mapping["a"]], row[mapping["b"]], row[mapping["c"]], row[mapping["d"]]]
            else:
                sample_id = row[0].strip() or f"{subject}-{index}"
                question = row[1].strip()
                options = [row[2], row[3], row[4], row[5]]
                answer = row[6].strip().upper()
                explanation = row[7].strip() if len(row) > 7 else ""

            samples.append(
                EvaluationSample(
                    sample_id=str(sample_id),
                    group=subject,
                    question=question,
                    options=[option.strip() for option in options],
                    answer=answer,
                    answer_index=ord(answer) - 65,
                    explanation=explanation,
                    metadata={"subject": subject},
                )
            )
        return samples
