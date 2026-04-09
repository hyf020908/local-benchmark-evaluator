from __future__ import annotations

import re
from typing import Optional


LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def strip_option_prefix(text: str) -> str:
    cleaned = collapse_whitespace(text)
    return re.sub(r"^\s*[\(\[]?[A-Z][\)\]]?[\.、:：]?\s*", "", cleaned)


def build_choice_labels(option_count: int, prefer_letters: bool = True) -> list[str]:
    if prefer_letters and option_count <= len(LETTERS):
        return list(LETTERS[:option_count])
    return [str(index) for index in range(1, option_count + 1)]


def format_labeled_options(options: list[str], labels: list[str]) -> list[str]:
    return [f"{label}. {option}" for label, option in zip(labels, options)]


def normalize_freeform_answer(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.strip("`\"' ")
    text = re.sub(r"^\$+|\$+$", "", text)
    boxed = re.fullmatch(r"\\boxed\{(.+)\}", text)
    if boxed:
        text = boxed.group(1)
    text = collapse_whitespace(text)
    text = text.rstrip("。.;, ")
    return text.lower()


def extract_final_answer_text(
    raw_output: str,
    answer_prefix: str = "Final Answer",
) -> Optional[str]:
    patterns = [
        rf"{answer_prefix}\s*[:：]\s*(.+?)(?:\n|$)",
        r"答案\s*[:：]\s*(.+?)(?:\n|$)",
        r"the answer is\s+(.+?)(?:\n|$)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, raw_output, flags=re.IGNORECASE)
        if matches:
            value = normalize_freeform_answer(matches[-1])
            if value:
                return value

    lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
    if not lines:
        return None
    tail = re.sub(r"^(A|Answer)\s*[:：]\s*", "", lines[-1], flags=re.IGNORECASE)
    value = normalize_freeform_answer(tail)
    return value or None


def extract_single_choice(raw_output: str, option_count: int) -> Optional[str]:
    allowed = LETTERS[: max(option_count, 4)]
    patterns = [
        rf"Final Answer\s*[:：]?\s*\(?([{allowed}])\)?",
        rf"答案\s*[:：]?\s*\(?([{allowed}])\)?",
        rf"the answer is\s*\(?([{allowed}])\)?",
        rf"so the answer is\s*\(?([{allowed}])\)?",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, raw_output, flags=re.IGNORECASE)
        if matches:
            return matches[-1].upper()

    matches = re.findall(rf"\b([{allowed}])\b", raw_output.upper())
    if matches:
        return matches[-1].upper()
    return None


def extract_labeled_choice(
    raw_output: str,
    labels: list[str],
    options: list[str],
) -> Optional[str]:
    candidate_texts: list[str] = []
    final_text = extract_final_answer_text(raw_output)
    if final_text:
        candidate_texts.append(final_text)

    lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
    candidate_texts.extend(reversed(lines[-5:]))
    for candidate in candidate_texts:
        resolved = _resolve_choice_candidate(candidate, labels, options)
        if resolved:
            return resolved

    label_pattern = "|".join(re.escape(label) for label in sorted(labels, key=len, reverse=True))
    patterns = [
        rf"Final Answer\s*[:：]?\s*\(?({label_pattern})\)?",
        rf"答案\s*[:：]?\s*\(?({label_pattern})\)?",
        rf"the answer is\s*\(?({label_pattern})\)?",
        rf"so the answer is\s*\(?({label_pattern})\)?",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, raw_output, flags=re.IGNORECASE)
        if matches:
            return _match_label(matches[-1], labels)

    return None


def extract_multi_choice(raw_output: str, option_count: int) -> Optional[str]:
    allowed = LETTERS[: max(option_count, 4)]
    answer_markers = [
        re.search(r"Final Answer\s*[:：]?\s*(.+)", raw_output, flags=re.IGNORECASE | re.DOTALL),
        re.search(r"答案\s*[:：]?\s*(.+)", raw_output, flags=re.IGNORECASE | re.DOTALL),
    ]
    for match in answer_markers:
        if not match:
            continue
        letters = re.findall(rf"[{allowed}]", match.group(1).upper())
        if letters:
            return _canonical_choice_set(letters)

    letters = re.findall(rf"[{allowed}]", raw_output.upper()[-120:])
    if letters:
        return _canonical_choice_set(letters)
    return None


def extract_sequential_choices(
    raw_output: str,
    option_count: int,
    expected_count: int,
) -> list[str]:
    allowed = LETTERS[: max(option_count, 4)]
    patterns = [
        rf"答案\s*[:：]?\s*\(?([{allowed}])\)?",
        rf"Final Answer\s*[:：]?\s*\(?([{allowed}])\)?",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, raw_output, flags=re.IGNORECASE)
        if len(matches) >= expected_count:
            return [match.upper() for match in matches[:expected_count]]

    letters = re.findall(rf"[{allowed}]", raw_output.upper()[-240:])
    if len(letters) >= expected_count:
        return letters[:expected_count]
    return []


def extract_embedded_options(text: str) -> tuple[str, list[str]]:
    lines = text.splitlines()
    option_start = None
    for index, line in enumerate(lines):
        if line.strip().lower() == "options:":
            option_start = index + 1
            break
    if option_start is None:
        return text.strip(), []

    question_lines = lines[: index]
    options: list[str] = []
    for line in lines[option_start:]:
        match = re.match(r"^\s*\(([A-Z])\)\s*(.*)$", line)
        if not match:
            continue
        options.append(match.group(2).strip())
    if not options:
        return text.strip(), []
    return "\n".join(question_lines).strip(), options


def _canonical_choice_set(letters: list[str]) -> str:
    ordered: list[str] = []
    seen: set[str] = set()
    for letter in letters:
        if letter not in seen:
            ordered.append(letter)
            seen.add(letter)
    return "".join(sorted(ordered))


def _resolve_choice_candidate(
    candidate: str,
    labels: list[str],
    options: list[str],
) -> Optional[str]:
    normalized = normalize_freeform_answer(candidate)
    if not normalized:
        return None

    stripped = re.sub(r"^(final answer|answer|option|choice)\s*[:：]?\s*", "", normalized).strip()
    stripped = stripped.strip("()[] ")
    matched_label = _match_label(stripped, labels)
    if matched_label:
        return matched_label

    for label, option in zip(labels, options):
        if stripped == normalize_freeform_answer(option):
            return label
    return None


def _match_label(candidate: str, labels: list[str]) -> Optional[str]:
    lowered = candidate.lower()
    for label in labels:
        if lowered == label.lower():
            return label
    return None
