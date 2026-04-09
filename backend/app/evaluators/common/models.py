from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class EvaluationSample:
    sample_id: str
    group: str
    question: str
    answer: str
    options: list[str] = field(default_factory=list)
    answer_index: Optional[int] = None
    explanation: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PreparedDataset:
    dataset_key: str
    dataset_name: str
    dataset_path: str
    samples: list[EvaluationSample]
    demonstrations_by_group: dict[str, list[EvaluationSample]] = field(
        default_factory=dict
    )
    metadata: dict[str, Any] = field(default_factory=dict)
