from __future__ import annotations

from pathlib import Path

from app.evaluators.agieval.evaluator import AGIEvalEvaluator
from app.evaluators.base import BaseEvaluator
from app.evaluators.big_bench.evaluator import BIGBenchEvaluator
from app.evaluators.big_bench_hard.evaluator import BIGBenchHardEvaluator
from app.evaluators.ceval.evaluator import CEvalEvaluator
from app.evaluators.cmmlu.evaluator import CMMLUEvaluator
from app.evaluators.gaokao_bench.evaluator import GAOKAOBenchEvaluator
from app.evaluators.gpqa.evaluator import GPQAEvaluator
from app.evaluators.hellaswag.evaluator import HellaSwagEvaluator
from app.evaluators.mmlu_pro.evaluator import MMLUProEvaluator
from app.evaluators.truthfulqa.evaluator import TruthfulQAEvaluator


class EvaluatorRegistry:
    def __init__(self) -> None:
        self._evaluators: dict[str, BaseEvaluator] = {
            evaluator.key: evaluator
            for evaluator in [
                MMLUProEvaluator(),
                CEvalEvaluator(),
                CMMLUEvaluator(),
                TruthfulQAEvaluator(),
                AGIEvalEvaluator(),
                GPQAEvaluator(),
                HellaSwagEvaluator(),
                GAOKAOBenchEvaluator(),
                BIGBenchEvaluator(),
                BIGBenchHardEvaluator(),
            ]
        }

    def list(self) -> list[BaseEvaluator]:
        return list(self._evaluators.values())

    def get(self, key: str) -> BaseEvaluator:
        if key not in self._evaluators:
            raise KeyError(f"Unsupported dataset type: {key}")
        return self._evaluators[key]

    def detect(self, dataset_path: Path) -> BaseEvaluator:
        for evaluator in self._evaluators.values():
            if evaluator.can_handle(dataset_path):
                return evaluator
        raise ValueError("无法根据当前路径自动识别评测集类型，请手动选择。")


registry = EvaluatorRegistry()
