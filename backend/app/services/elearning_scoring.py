"""Scoring QCM e-learning — questions JSON + réponses élève."""
from __future__ import annotations

from decimal import Decimal
from typing import Any


def _as_list(questions: Any) -> list[dict]:
    if isinstance(questions, list):
        return [q for q in questions if isinstance(q, dict)]
    return []


def score_quiz(
    questions: Any,
    reponses: Any,
    *,
    note_max: Decimal | float = 20,
) -> dict:
    """Corrige un QCM.

    Format question attendu::
        {"q": "…", "choices": ["a", "b"], "answer": 0, "points": 1}

    ``answer`` peut être un int (index) ou une liste d'indexes (multi-choix).
    ``reponses`` : liste parallèle d'indexes (int ou list[int]), ou dict {idx: answer}.
    """
    qs = _as_list(questions)
    if isinstance(reponses, dict):
        answers_by_idx = {int(k): v for k, v in reponses.items() if str(k).isdigit()}
    elif isinstance(reponses, list):
        answers_by_idx = {i: v for i, v in enumerate(reponses)}
    else:
        answers_by_idx = {}

    detail: list[dict] = []
    score_brut = Decimal(0)
    score_max = Decimal(0)

    for i, q in enumerate(qs):
        pts = Decimal(str(q.get("points", 1) or 1))
        score_max += pts
        expected = q.get("answer")
        given = answers_by_idx.get(i)
        correct = _answers_match(expected, given)
        if correct:
            score_brut += pts
        detail.append(
            {
                "index": i,
                "correct": correct,
                "points": float(pts),
                "expected": expected,
                "given": given,
            }
        )

    note_max_d = Decimal(str(note_max or 20))
    if score_max > 0:
        note = (score_brut / score_max * note_max_d).quantize(Decimal("0.01"))
    else:
        note = Decimal(0)

    return {
        "score_brut": score_brut,
        "score_max": score_max,
        "note": note,
        "note_max": note_max_d,
        "detail": detail,
        "nb_questions": len(qs),
        "nb_correctes": sum(1 for d in detail if d["correct"]),
    }


def _answers_match(expected: Any, given: Any) -> bool:
    if expected is None:
        return False
    if isinstance(expected, list):
        exp_set = {int(x) for x in expected}
        if isinstance(given, list):
            return exp_set == {int(x) for x in given}
        if given is None:
            return False
        return exp_set == {int(given)}
    if given is None:
        return False
    if isinstance(given, list):
        return len(given) == 1 and int(given[0]) == int(expected)
    try:
        return int(given) == int(expected)
    except (TypeError, ValueError):
        return False


def strip_answers_for_student(questions: Any) -> list[dict]:
    """Masque les bonnes réponses avant passage du quiz."""
    out: list[dict] = []
    for q in _as_list(questions):
        out.append(
            {
                "q": q.get("q") or q.get("question") or "",
                "choices": q.get("choices") or [],
                "points": q.get("points", 1),
            }
        )
    return out
