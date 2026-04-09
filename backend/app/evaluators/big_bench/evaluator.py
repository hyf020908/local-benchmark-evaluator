from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from app.evaluators.base import BaseEvaluator
from app.evaluators.common.models import EvaluationSample, PreparedDataset
from app.evaluators.common.parsing import (
    LETTERS,
    extract_final_answer_text,
    extract_single_choice,
    normalize_freeform_answer,
)


class BIGBenchEvaluator(BaseEvaluator):
    key = "big_bench"
    label = "BIG-bench"
    description = "JSON-defined BIG-bench tasks loaded from task.json files under bigbench/benchmark_tasks."

    def can_handle(self, dataset_path: Path) -> bool:
        return bool(self._resolve_task_paths(dataset_path))

    def load(self, dataset_path: Path, max_samples: int, few_shot: int) -> PreparedDataset:
        task_paths = self._resolve_task_paths(dataset_path)
        if not task_paths:
            raise ValueError("BIG-bench 目录格式不正确，需包含 task.json 或 bigbench/benchmark_tasks 下的 JSON 任务。")

        samples: list[EvaluationSample] = []
        demonstrations: dict[str, list[EvaluationSample]] = {}
        for task_path in task_paths:
            payload = json.loads(task_path.read_text(encoding="utf-8"))
            task_name = str(payload.get("name") or task_path.parent.name).strip() or task_path.parent.name
            task_samples = self._convert_task(task_name, payload)
            if not task_samples:
                continue
            demonstrations[task_name] = task_samples
            samples.extend(task_samples)

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
        task_name = str(sample.metadata.get("task_name") or sample.group)
        task_format = str(sample.metadata.get("format") or "text")
        demos = [
            item
            for item in dataset.demonstrations_by_group.get(sample.group, [])
            if item.sample_id != sample.sample_id
        ][:few_shot]

        if task_format == "choice":
            parts = [
                (
                    f"You are evaluating the BIG-bench task `{task_name}`. "
                    "Choose the best option and end with `Final Answer: X`."
                )
            ]
            for demo in demos:
                parts.append(self._format_choice_question(demo))
                parts.append(f"Final Answer: {demo.answer}")
            parts.append(self._format_choice_question(sample))
            parts.append("Final Answer:")
            return "\n\n".join(parts)

        parts = [
            (
                f"You are evaluating the BIG-bench task `{task_name}`. "
                "Answer the question exactly and end with `Final Answer: ...`."
            )
        ]
        for demo in demos:
            parts.append(f"Question:\n{demo.question}")
            parts.append(f"Final Answer: {demo.answer}")
        parts.append(f"Question:\n{sample.question}")
        parts.append("Final Answer:")
        return "\n\n".join(parts)

    def parse_prediction(self, raw_output: str, sample: EvaluationSample) -> Optional[str]:
        if sample.metadata.get("format") == "choice":
            return extract_single_choice(raw_output, len(sample.options))

        regex = str(sample.metadata.get("output_regex") or "").strip()
        if regex:
            matches = re.findall(regex, raw_output)
            if matches:
                value = matches[-1]
                if isinstance(value, tuple):
                    value = "".join(value)
                normalized = normalize_freeform_answer(value)
                if normalized:
                    return normalized
        return extract_final_answer_text(raw_output)

    def is_correct(self, sample: EvaluationSample, parsed_prediction: Optional[str]) -> bool:
        if not parsed_prediction:
            return False
        if sample.metadata.get("format") == "choice":
            accepted_letters = sample.metadata.get("accepted_letters") or [sample.answer]
            return parsed_prediction.upper() in accepted_letters

        accepted_answers = sample.metadata.get("accepted_answers") or [sample.answer]
        normalized_prediction = normalize_freeform_answer(parsed_prediction)
        return normalized_prediction in {
            normalize_freeform_answer(str(answer))
            for answer in accepted_answers
        }

    def _resolve_task_paths(self, dataset_path: Path) -> list[Path]:
        if (dataset_path / "task.json").is_file():
            return [dataset_path / "task.json"]

        candidates = []
        for root in [
            dataset_path / "bigbench" / "benchmark_tasks",
            dataset_path / "benchmark_tasks",
            dataset_path,
        ]:
            if not root.is_dir():
                continue
            candidates.extend(sorted(root.rglob("task.json")))
            if candidates:
                break
        return [
            path
            for path in candidates
            if path.is_file()
        ]

    def _convert_task(self, task_name: str, payload: dict) -> list[EvaluationSample]:
        examples = payload.get("examples") or []
        output_regex = str(payload.get("output_regex") or "").strip()
        samples: list[EvaluationSample] = []

        for index, example in enumerate(examples):
            if not isinstance(example, dict):
                continue
            question = str(example.get("input") or "").strip()
            if not question:
                continue

            if "target_scores" in example and isinstance(example["target_scores"], dict):
                options = [str(option).strip() for option in example["target_scores"].keys()]
                if not options:
                    continue
                score_values = [
                    float(score) if isinstance(score, (int, float)) else float(str(score))
                    for score in example["target_scores"].values()
                ]
                max_score = max(score_values)
                accepted_letters = [
                    LETTERS[position]
                    for position, score in enumerate(score_values)
                    if score == max_score
                ]
                samples.append(
                    EvaluationSample(
                        sample_id=f"{task_name}-{index}",
                        group=task_name,
                        question=question,
                        options=options,
                        answer=accepted_letters[0],
                        answer_index=ord(accepted_letters[0]) - 65,
                        metadata={
                            "format": "choice",
                            "task_name": task_name,
                            "accepted_letters": accepted_letters,
                            "preferred_score": payload.get("preferred_score"),
                        },
                    )
                )
                continue

            targets = example.get("target")
            if targets is None:
                continue
            if isinstance(targets, list):
                accepted_answers = [str(item).strip() for item in targets if str(item).strip()]
            else:
                accepted_answers = [str(targets).strip()]
            if not accepted_answers:
                continue
            samples.append(
                EvaluationSample(
                    sample_id=f"{task_name}-{index}",
                    group=task_name,
                    question=question,
                    answer=accepted_answers[0],
                    metadata={
                        "format": "text",
                        "task_name": task_name,
                        "accepted_answers": accepted_answers,
                        "output_regex": output_regex,
                        "preferred_score": payload.get("preferred_score"),
                    },
                )
            )
        return samples

    def _format_choice_question(self, sample: EvaluationSample) -> str:
        option_lines = [f"{LETTERS[index]}. {option}" for index, option in enumerate(sample.options)]
        return "\n".join([f"Question:\n{sample.question}", "Options:", *option_lines])
