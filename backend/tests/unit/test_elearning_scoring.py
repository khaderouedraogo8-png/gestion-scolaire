"""Tests unitaires scoring QCM e-learning."""
from decimal import Decimal

from app.services.elearning_scoring import score_quiz, strip_answers_for_student


def test_score_quiz_all_correct():
    questions = [
        {"q": "2+2?", "choices": ["3", "4"], "answer": 1, "points": 1},
        {"q": "Capitale BF?", "choices": ["Ouaga", "Bobo"], "answer": 0, "points": 1},
    ]
    result = score_quiz(questions, [1, 0], note_max=20)
    assert result["nb_correctes"] == 2
    assert result["score_brut"] == Decimal(2)
    assert result["note"] == Decimal("20.00")


def test_score_quiz_partial_and_strip():
    questions = [
        {"q": "A", "choices": ["x", "y"], "answer": 0, "points": 2},
        {"q": "B", "choices": ["x", "y"], "answer": 1, "points": 2},
    ]
    result = score_quiz(questions, [0, 0], note_max=10)
    assert result["nb_correctes"] == 1
    assert result["note"] == Decimal("5.00")

    stripped = strip_answers_for_student(questions)
    assert "answer" not in stripped[0]
    assert stripped[0]["choices"] == ["x", "y"]


def test_score_quiz_multi_choice():
    questions = [{"q": "multi", "choices": ["a", "b", "c"], "answer": [0, 2], "points": 1}]
    ok = score_quiz(questions, [[0, 2]], note_max=20)
    assert ok["nb_correctes"] == 1
    bad = score_quiz(questions, [[0]], note_max=20)
    assert bad["nb_correctes"] == 0
