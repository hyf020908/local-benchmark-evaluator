from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.evaluators.base import BaseEvaluator
from app.evaluators.common.models import EvaluationSample, PreparedDataset
from app.evaluators.common.parsing import (
    extract_multi_choice,
    extract_sequential_choices,
    extract_single_choice,
)
from app.evaluators.common.sampling import choose_random_samples


class GAOKAOBenchEvaluator(BaseEvaluator):
    key = "gaokao_bench"
    label = "GAOKAO-Bench"
    description = "Objective GAOKAO benchmark tasks from Data/Objective_Questions with official prompt settings."

    def can_handle(self, dataset_path: Path) -> bool:
        objective_dir = self._resolve_objective_dir(dataset_path)
        return bool(objective_dir and any(objective_dir.glob("*.json")))

    def load(
        self, dataset_path: Path, max_samples: int, few_shot: int, random_seed: int
    ) -> PreparedDataset:
        objective_dir = self._resolve_objective_dir(dataset_path)
        if not objective_dir:
            raise ValueError("GAOKAO-Bench 目录格式不正确，需包含 Data/Objective_Questions。")

        prompt_map = self._load_prompt_map(dataset_path)
        samples: list[EvaluationSample] = []
        demonstrations: dict[str, list[EvaluationSample]] = {}
        for path in sorted(objective_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            keyword = str(data.get("keywords") or path.stem).strip() or path.stem
            prompt_config = prompt_map.get(keyword, {})
            question_type = str(prompt_config.get("type") or "single_choice")
            prompt_prefix = str(prompt_config.get("prefix_prompt") or "").strip()

            group_samples: list[EvaluationSample] = []
            for record in data.get("example", []):
                if not isinstance(record, dict):
                    continue
                serialized_answer = self._serialize_answer(record.get("answer"), question_type)
                if not serialized_answer:
                    continue
                group_samples.append(
                    EvaluationSample(
                        sample_id=f"{keyword}-{record.get('index', len(group_samples))}",
                        group=keyword,
                        question=str(record.get("question") or "").strip(),
                        answer=serialized_answer,
                        explanation=str(record.get("analysis") or "").strip(),
                        metadata={
                            "question_type": question_type,
                            "prompt_prefix": prompt_prefix,
                            "answer_length": len(record.get("answer") or []),
                            "year": str(record.get("year") or "").strip(),
                            "category": str(record.get("category") or "").strip(),
                            "score": record.get("score"),
                        },
                    )
                )
            if group_samples:
                demonstrations[keyword] = group_samples
                samples.extend(group_samples)

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
        parts = [str(sample.metadata.get("prompt_prefix") or "请作答：").strip()]
        demos = [
            item
            for item in dataset.demonstrations_by_group.get(sample.group, [])
            if item.sample_id != sample.sample_id
        ][:few_shot]
        for demo in demos:
            parts.append(demo.question)
            parts.append(self._format_demo_answer(demo))
        parts.append(sample.question)
        return "\n\n".join(part for part in parts if part)

    def parse_prediction(self, raw_output: str, sample: EvaluationSample) -> Optional[str]:
        question_type = str(sample.metadata.get("question_type") or "single_choice")
        if question_type == "single_choice":
            return extract_single_choice(raw_output, 4)
        if question_type == "multi_choice":
            return extract_multi_choice(raw_output, 4)
        if question_type == "multi_question_choice":
            answers = extract_sequential_choices(
                raw_output,
                4,
                int(sample.metadata.get("answer_length") or 0),
            )
            return "|".join(answers) if answers else None
        if question_type == "five_out_of_seven":
            answers = extract_sequential_choices(
                raw_output,
                7,
                int(sample.metadata.get("answer_length") or 0),
            )
            return "|".join(answers) if answers else None
        return None

    def is_correct(self, sample: EvaluationSample, parsed_prediction: Optional[str]) -> bool:
        return bool(parsed_prediction and parsed_prediction.upper() == sample.answer.upper())

    def _resolve_objective_dir(self, dataset_path: Path) -> Optional[Path]:
        for candidate in [
            "Data/Objective_Questions",
            "Objective_Questions",
            "data/objective_questions",
        ]:
            target = dataset_path / candidate
            if target.is_dir():
                return target
        return None

    def _load_prompt_map(self, dataset_path: Path) -> dict[str, dict]:
        candidates = [
            dataset_path / "Bench" / "Obj_Prompt.json",
            dataset_path / "Obj_Prompt.json",
            dataset_path.parent / "Bench" / "Obj_Prompt.json",
        ]
        for candidate in candidates:
            if candidate.is_file():
                data = json.loads(candidate.read_text(encoding="utf-8"))
                return {
                    str(item.get("keyword") or ""): item
                    for item in data.get("examples", [])
                    if isinstance(item, dict)
                }
        return {}

    def _serialize_answer(self, raw_answer: object, question_type: str) -> str:
        answers = [str(item).strip().upper() for item in raw_answer or [] if str(item).strip()]
        if not answers:
            return ""
        if question_type == "single_choice":
            return answers[0]
        if question_type == "multi_choice":
            letters = list(answers[0] if len(answers) == 1 else "".join(answers))
            return "".join(sorted({letter for letter in letters}))
        return "|".join(answers)

    def _format_demo_answer(self, sample: EvaluationSample) -> str:
        question_type = str(sample.metadata.get("question_type") or "single_choice")
        if question_type in {"single_choice", "multi_choice"}:
            return f"【答案】 {sample.answer} <eoa>"
        if question_type == "five_out_of_seven":
            return f"【答案】 {' '.join(sample.answer.split('|'))} <eoa>"
        return "\n".join(
            f"（{index}）【答案】 {answer} <eoa>"
            for index, answer in enumerate(sample.answer.split("|"), start=1)
        )
