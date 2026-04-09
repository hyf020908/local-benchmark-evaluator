from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.evaluators.base import BaseEvaluator
from app.evaluators.common.models import EvaluationSample, PreparedDataset
from app.evaluators.common.parsing import (
    build_choice_labels,
    extract_embedded_options,
    extract_final_answer_text,
    extract_labeled_choice,
    extract_single_choice,
    format_labeled_options,
    normalize_freeform_answer,
)


class BIGBenchHardEvaluator(BaseEvaluator):
    key = "big_bench_hard"
    label = "BIG-Bench-Hard"
    description = "Challenging BIG-Bench tasks stored as JSON files under bbh/ with optional CoT prompts."

    def can_handle(self, dataset_path: Path) -> bool:
        tasks_dir = self._resolve_tasks_dir(dataset_path)
        return bool(tasks_dir and any(tasks_dir.glob("*.json")))

    def load(self, dataset_path: Path, max_samples: int, few_shot: int) -> PreparedDataset:
        tasks_dir = self._resolve_tasks_dir(dataset_path)
        if not tasks_dir:
            raise ValueError("BIG-Bench-Hard 目录格式不正确，需包含 bbh/*.json。")

        cot_prompts = self._load_cot_prompts(dataset_path)
        samples: list[EvaluationSample] = []
        demonstrations: dict[str, list[EvaluationSample]] = {}
        for path in sorted(tasks_dir.glob("*.json")):
            if len(samples) >= max_samples:
                break
            payload = json.loads(path.read_text(encoding="utf-8"))
            task_name = path.stem
            task_samples: list[EvaluationSample] = []
            for index, example in enumerate(payload.get("examples", [])):
                if len(samples) + len(task_samples) >= max_samples:
                    break
                if not isinstance(example, dict):
                    continue
                raw_input = str(example.get("input") or "").strip()
                target = str(example.get("target") or "").strip()
                if not raw_input or not target:
                    continue

                question, options = extract_embedded_options(raw_input)
                task_format = "choice" if options and target.startswith("(") and target.endswith(")") else "text"
                answer = target[1:-1].strip().upper() if task_format == "choice" else target
                choice_labels = build_choice_labels(len(options), prefer_letters=True) if options else []
                task_samples.append(
                    EvaluationSample(
                        sample_id=f"{task_name}-{index}",
                        group=task_name,
                        question=question if task_format == "choice" else raw_input,
                        options=options,
                        answer=answer,
                        answer_index=ord(answer) - 65 if task_format == "choice" else None,
                        metadata={
                            "format": task_format,
                            "task_name": task_name,
                            "raw_input": raw_input,
                            "cot_prompt": cot_prompts.get(task_name, ""),
                            "choice_labels": choice_labels,
                        },
                    )
                )
            if task_samples:
                demonstrations[task_name] = task_samples
                samples.extend(task_samples)

        return PreparedDataset(
            dataset_key=self.key,
            dataset_name=self.label,
            dataset_path=str(dataset_path),
            samples=samples[:max_samples],
            demonstrations_by_group=demonstrations,
            metadata={"cot_prompts": cot_prompts},
        )

    def build_prompt(
        self, sample: EvaluationSample, dataset: PreparedDataset, few_shot: int
    ) -> str:
        cot_prompt = str(sample.metadata.get("cot_prompt") or "").strip()
        if few_shot > 0 and cot_prompt:
            parts = [cot_prompt, "", f"Q: {sample.metadata.get('raw_input', sample.question)}", "A: Let's think step by step."]
            return "\n".join(parts)

        if sample.metadata.get("format") == "choice":
            parts = [
                (
                    f"You are evaluating the BIG-Bench-Hard task `{sample.group}`. "
                    "Choose the best option and end with `Final Answer: X`."
                )
            ]
            demos = [
                item
                for item in dataset.demonstrations_by_group.get(sample.group, [])
                if item.sample_id != sample.sample_id
            ][:few_shot]
            for demo in demos:
                parts.append(self._format_choice_question(demo))
                parts.append(f"Final Answer: {demo.answer}")
            parts.append(self._format_choice_question(sample))
            parts.append("Final Answer:")
            return "\n\n".join(parts)

        parts = [
            (
                f"You are evaluating the BIG-Bench-Hard task `{sample.group}`. "
                "Answer the question exactly and end with `Final Answer: ...`."
            )
        ]
        demos = [
            item
            for item in dataset.demonstrations_by_group.get(sample.group, [])
            if item.sample_id != sample.sample_id
        ][:few_shot]
        for demo in demos:
            parts.append(f"Question:\n{demo.question}")
            parts.append(f"Final Answer: {demo.answer}")
        parts.append(f"Question:\n{sample.question}")
        parts.append("Final Answer:")
        return "\n\n".join(parts)

    def parse_prediction(self, raw_output: str, sample: EvaluationSample) -> Optional[str]:
        if sample.metadata.get("format") == "choice":
            choice_labels = list(sample.metadata.get("choice_labels") or [])
            if all(len(label) == 1 and label.isalpha() for label in choice_labels):
                return extract_single_choice(raw_output, len(sample.options))
            return extract_labeled_choice(raw_output, choice_labels, sample.options)
        return extract_final_answer_text(raw_output)

    def is_correct(self, sample: EvaluationSample, parsed_prediction: Optional[str]) -> bool:
        if not parsed_prediction:
            return False
        if sample.metadata.get("format") == "choice":
            return parsed_prediction.upper() == sample.answer.upper()
        return normalize_freeform_answer(parsed_prediction) == normalize_freeform_answer(sample.answer)

    def _resolve_tasks_dir(self, dataset_path: Path) -> Path | None:
        if (dataset_path / "bbh").is_dir():
            return dataset_path / "bbh"
        if any(dataset_path.glob("*.json")):
            return dataset_path
        return None

    def _load_cot_prompts(self, dataset_path: Path) -> dict[str, str]:
        candidates = [
            dataset_path / "cot-prompts",
            dataset_path.parent / "cot-prompts",
        ]
        for candidate in candidates:
            if not candidate.is_dir():
                continue
            return {
                path.stem: path.read_text(encoding="utf-8").strip()
                for path in candidate.glob("*.txt")
            }
        return {}

    def _format_choice_question(self, sample: EvaluationSample) -> str:
        choice_labels = list(sample.metadata.get("choice_labels") or build_choice_labels(len(sample.options), prefer_letters=True))
        option_lines = format_labeled_options(sample.options, choice_labels)
        return "\n".join([f"Question:\n{sample.question}", "Options:", *option_lines])
