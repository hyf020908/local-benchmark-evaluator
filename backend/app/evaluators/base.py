from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, Optional

from app.evaluators.common.models import EvaluationSample, PreparedDataset


class BaseEvaluator(ABC):
    key: str = ""
    label: str = ""
    description: str = ""

    @abstractmethod
    def can_handle(self, dataset_path: Path) -> bool:
        raise NotImplementedError

    @abstractmethod
    def load(self, dataset_path: Path, max_samples: int, few_shot: int) -> PreparedDataset:
        raise NotImplementedError

    @abstractmethod
    def build_prompt(
        self, sample: EvaluationSample, dataset: PreparedDataset, few_shot: int
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def parse_prediction(self, raw_output: str, sample: EvaluationSample) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def is_correct(self, sample: EvaluationSample, parsed_prediction: Optional[str]) -> bool:
        raise NotImplementedError

    def summarize_question(self, sample: EvaluationSample) -> str:
        compact = re.sub(r"\s+", " ", sample.question).strip()
        if len(compact) <= 140:
            return compact
        return f"{compact[:137]}..."

    def get_demos(
        self, dataset: PreparedDataset, group: str, few_shot: int
    ) -> Iterable[EvaluationSample]:
        if few_shot <= 0:
            return []
        demos = dataset.demonstrations_by_group.get(group, [])
        return demos[:few_shot]


class MultipleChoiceEvaluator(BaseEvaluator, ABC):
    answer_prefix: str = "Final Answer"

    def parse_prediction(self, raw_output: str, sample: EvaluationSample) -> Optional[str]:
        option_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[: max(len(sample.options), 4)]
        patterns = [
            rf"{self.answer_prefix}\s*[:：]\s*([{option_letters}])",
            rf"答案\s*[:：]\s*([{option_letters}])",
            rf"the answer is\s*\(?([{option_letters}])\)?",
            rf"\b([{option_letters}])\b(?!.*\b[{option_letters}]\b)",
        ]
        for pattern in patterns:
            match = re.search(pattern, raw_output, flags=re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).upper()
        return None

    def is_correct(self, sample: EvaluationSample, parsed_prediction: Optional[str]) -> bool:
        return bool(parsed_prediction and parsed_prediction.upper() == sample.answer.upper())

    def format_question_block(self, sample: EvaluationSample) -> str:
        option_lines = []
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for index, option in enumerate(sample.options):
            option_lines.append(f"{letters[index]}. {option}")
        return "\n".join(
            [
                f"Question:\n{sample.question}",
                "Options:",
                *option_lines,
            ]
        )

    def build_prompt(
        self, sample: EvaluationSample, dataset: PreparedDataset, few_shot: int
    ) -> str:
        parts = [
            (
                f"You are evaluating a model on the {self.label} benchmark. "
                f"Answer the multiple-choice question and end with `{self.answer_prefix}: X`."
            )
        ]
        for demo in self.get_demos(dataset, sample.group, few_shot):
            parts.append(self.format_question_block(demo))
            parts.append(f"{self.answer_prefix}: {demo.answer}")
        parts.append(self.format_question_block(sample))
        parts.append(f"{self.answer_prefix}:")
        return "\n\n".join(parts)


class NumericAnswerEvaluator(BaseEvaluator, ABC):
    answer_prefix: str = "Final Answer"

    def parse_prediction(self, raw_output: str, sample: EvaluationSample) -> Optional[str]:
        patterns = [
            rf"{self.answer_prefix}\s*[:：]\s*([-+]?[0-9][0-9,]*(?:\.[0-9]+)?)",
            r"####\s*([-+]?[0-9][0-9,]*(?:\.[0-9]+)?)",
            r"([-+]?[0-9][0-9,]*(?:\.[0-9]+)?)(?!.*[-+]?[0-9][0-9,]*(?:\.[0-9]+)?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, raw_output, flags=re.IGNORECASE | re.DOTALL)
            if match:
                return self.normalize_number(match.group(1))
        return None

    def normalize_number(self, value: str) -> str:
        return value.replace(",", "").strip()

    def is_correct(self, sample: EvaluationSample, parsed_prediction: Optional[str]) -> bool:
        return bool(
            parsed_prediction
            and self.normalize_number(parsed_prediction) == self.normalize_number(sample.answer)
        )

    def build_prompt(
        self, sample: EvaluationSample, dataset: PreparedDataset, few_shot: int
    ) -> str:
        parts = [
            (
                f"You are solving a grade-school math problem from {self.label}. "
                f"Show concise reasoning if needed and end with `{self.answer_prefix}: number`."
            )
        ]
        for demo in self.get_demos(dataset, sample.group, few_shot):
            parts.append(f"Question:\n{demo.question}")
            parts.append(f"{self.answer_prefix}: {demo.answer}")
        parts.append(f"Question:\n{sample.question}")
        parts.append(f"{self.answer_prefix}:")
        return "\n\n".join(parts)
