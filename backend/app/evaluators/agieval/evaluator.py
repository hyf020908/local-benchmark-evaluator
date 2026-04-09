from __future__ import annotations

import ast
import csv
import re
from pathlib import Path
from typing import Optional

from app.evaluators.base import BaseEvaluator
from app.evaluators.common.io import load_json_records
from app.evaluators.common.models import EvaluationSample, PreparedDataset
from app.evaluators.common.parsing import (
    extract_final_answer_text,
    extract_multi_choice,
    extract_single_choice,
    normalize_freeform_answer,
    strip_option_prefix,
)
from app.evaluators.common.sampling import choose_random_samples


class AGIEvalEvaluator(BaseEvaluator):
    key = "agieval"
    label = "AGIEval"
    description = "Human exam benchmark with MCQ and cloze JSONL tasks under data/v1_1 or data/v1."

    def can_handle(self, dataset_path: Path) -> bool:
        data_dir = self._resolve_data_dir(dataset_path)
        return bool(data_dir and any(data_dir.glob("*.jsonl")))

    def load(
        self, dataset_path: Path, max_samples: int, few_shot: int, random_seed: int
    ) -> PreparedDataset:
        data_dir = self._resolve_data_dir(dataset_path)
        if not data_dir:
            raise ValueError("AGIEval 目录格式不正确，需包含 data/v1_1 或 data/v1 下的 JSONL 任务文件。")

        demonstrations = self._load_few_shot_prompts(dataset_path, data_dir)
        samples: list[EvaluationSample] = []
        for path in sorted(data_dir.glob("*.jsonl")):
            samples.extend(self._load_records(path))

        return PreparedDataset(
            dataset_key=self.key,
            dataset_name=self.label,
            dataset_path=str(dataset_path),
            samples=choose_random_samples(samples, max_samples, random_seed),
            demonstrations_by_group=demonstrations,
        )

    def build_prompt(
        self, sample: EvaluationSample, dataset: PreparedDataset, few_shot: int
    ) -> str:
        task_format = sample.metadata.get("format", "mcq")
        if task_format == "mcq":
            instructions = (
                "You are evaluating a model on the AGIEval benchmark. "
                "Answer the multiple-choice question and end with `Final Answer: X`."
            )
        elif task_format == "multi_choice":
            instructions = (
                "You are evaluating a model on the AGIEval benchmark. "
                "Answer the multiple-choice question and end with all correct options in "
                "`Final Answer: XYZ` format."
            )
        else:
            instructions = (
                "You are evaluating a model on the AGIEval benchmark. "
                "Answer the question and end with `Final Answer: ...`."
            )

        parts = [instructions]
        for demo in self.get_demos(dataset, sample.group, few_shot):
            parts.append(self._format_question(demo))
            parts.append(self._format_answer(demo))
        parts.append(self._format_question(sample))
        parts.append("Final Answer:")
        return "\n\n".join(parts)

    def parse_prediction(self, raw_output: str, sample: EvaluationSample) -> Optional[str]:
        task_format = sample.metadata.get("format")
        if task_format == "mcq":
            return extract_single_choice(raw_output, len(sample.options))
        if task_format == "multi_choice":
            return extract_multi_choice(raw_output, len(sample.options))
        return extract_final_answer_text(raw_output)

    def is_correct(self, sample: EvaluationSample, parsed_prediction: Optional[str]) -> bool:
        if not parsed_prediction:
            return False
        task_format = sample.metadata.get("format")
        if task_format == "mcq":
            return parsed_prediction.upper() == sample.answer.upper()
        if task_format == "multi_choice":
            return self._canonical_multi_answer(parsed_prediction) == self._canonical_multi_answer(
                sample.answer
            )
        return normalize_freeform_answer(parsed_prediction) == normalize_freeform_answer(sample.answer)

    def _resolve_data_dir(self, dataset_path: Path) -> Optional[Path]:
        for candidate in ["data/v1_1", "data/v1", "v1_1", "v1"]:
            target = dataset_path / candidate
            if target.is_dir():
                return target
        if any(dataset_path.glob("*.jsonl")):
            return dataset_path
        return None

    def _resolve_few_shot_file(self, dataset_path: Path, data_dir: Path) -> Optional[Path]:
        candidates = [
            dataset_path / "data" / "few_shot_prompts.csv",
            data_dir.parent / "few_shot_prompts.csv",
            dataset_path / "few_shot_prompts.csv",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return None

    def _load_few_shot_prompts(
        self, dataset_path: Path, data_dir: Path
    ) -> dict[str, list[EvaluationSample]]:
        prompt_file = self._resolve_few_shot_file(dataset_path, data_dir)
        if not prompt_file:
            return {}

        with prompt_file.open("r", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))
        if not rows:
            return {}

        headers = rows[0][1:]
        demonstrations: dict[str, list[EvaluationSample]] = {}
        for column, task_name in enumerate(headers, start=1):
            task_name = task_name.strip()
            if not task_name:
                continue
            task_samples: list[EvaluationSample] = []
            for row_index in range(1, len(rows), 2):
                if column >= len(rows[row_index]):
                    continue
                payload = rows[row_index][column].strip()
                if not payload:
                    continue
                explanation = ""
                if row_index + 1 < len(rows) and column < len(rows[row_index + 1]):
                    explanation = rows[row_index + 1][column].strip()
                try:
                    record = ast.literal_eval(payload)
                except Exception:
                    continue
                sample = self._convert_record(
                    task_name,
                    record,
                    row_index,
                    source_file=prompt_file.name,
                )
                if not sample.answer:
                    continue
                sample.explanation = explanation or sample.explanation
                task_samples.append(sample)
            if task_samples:
                demonstrations[task_name] = task_samples
        return demonstrations

    def _load_records(self, path: Path) -> list[EvaluationSample]:
        records = load_json_records(path)
        task_name = path.stem
        samples: list[EvaluationSample] = []
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            sample = self._convert_record(task_name, record, index, source_file=path.name)
            if sample.answer:
                samples.append(sample)
        return samples

    def _convert_record(
        self,
        task_name: str,
        record: dict,
        index: int,
        source_file: str,
    ) -> EvaluationSample:
        options = [strip_option_prefix(str(item)) for item in record.get("options") or [] if str(item).strip()]
        answer = ""
        task_format = "mcq"
        if not options:
            answer = str(record.get("answer") or "").strip()
            task_format = "text"
        else:
            raw_label = record.get("label")
            if isinstance(raw_label, list):
                raw_label = "".join(str(item) for item in raw_label)
            letters = re.findall(r"[A-Z]", str(raw_label or "").upper())
            if len(letters) > 1:
                answer = self._canonical_multi_answer("".join(letters))
                task_format = "multi_choice"
            else:
                answer = letters[0] if letters else ""
        return EvaluationSample(
            sample_id=str(record.get("id") or record.get("question_id") or f"{task_name}-{index}"),
            group=task_name,
            question=str(record.get("question") or "").strip(),
            options=options,
            answer=answer,
            answer_index=ord(answer) - 65 if task_format == "mcq" and answer else None,
            explanation=str(record.get("other", "")) if isinstance(record.get("other"), str) else None,
            metadata={
                "format": task_format,
                "passage": str(record.get("passage") or "").strip(),
                "source_file": source_file,
            },
        )

    def _format_question(self, sample: EvaluationSample) -> str:
        parts: list[str] = []
        passage = str(sample.metadata.get("passage") or "").strip()
        if passage:
            parts.append(f"Passage:\n{passage}")
        parts.append(f"Question:\n{sample.question}")
        if sample.options:
            option_lines = [f"{chr(65 + index)}. {option}" for index, option in enumerate(sample.options)]
            parts.extend(["Options:", *option_lines])
        return "\n".join(parts)

    def _format_answer(self, sample: EvaluationSample) -> str:
        return f"Final Answer: {sample.answer}"

    def _canonical_multi_answer(self, value: str) -> str:
        letters = re.findall(r"[A-Z]", str(value or "").upper())
        if not letters:
            return ""
        return "".join(sorted(dict.fromkeys(letters)))
