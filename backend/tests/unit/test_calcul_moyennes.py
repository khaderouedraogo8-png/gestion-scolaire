"""Tests unitaires — calcul des moyennes."""
from app.services.calcul_moyennes import (
    calculer_moyenne_generale,
    calculer_moyenne_matiere,
    calculer_rangs,
    determiner_mention,
)


class TestCalculMoyennes:
    def test_moyenne_matiere_exclut_absents(self):
        notes = [
            {"valeur": 15, "coefficient": 2, "absent": False},
            {"valeur": 0, "coefficient": 1, "absent": True},  # absent ≠ 0
            {"valeur": 12, "coefficient": 1, "absent": False},
        ]
        moyenne = calculer_moyenne_matiere(notes)
        # (15*2 + 12*1) / (2+1) = 42/3 = 14.0
        assert moyenne == 14.0

    def test_moyenne_matiere_note_zero_compte(self):
        notes = [
            {"valeur": 0, "coefficient": 1, "absent": False},
            {"valeur": 10, "coefficient": 1, "absent": False},
        ]
        moyenne = calculer_moyenne_matiere(notes)
        assert moyenne == 5.0

    def test_moyenne_matiere_tous_absents(self):
        notes = [
            {"valeur": None, "coefficient": 1, "absent": True},
            {"valeur": None, "coefficient": 2, "absent": True},
        ]
        assert calculer_moyenne_matiere(notes) is None

    def test_moyenne_generale(self):
        matieres = [
            {"moyenne": 14.0, "coefficient_matiere": 3},
            {"moyenne": 12.0, "coefficient_matiere": 2},
        ]
        moyenne = calculer_moyenne_generale(matieres)
        # (14*3 + 12*2) / 5 = 66/5 = 13.2
        assert moyenne == 13.2

    def test_calculer_rangs(self):
        moyennes = {
            "a": 15.0,
            "b": 12.0,
            "c": 15.0,
            "d": None,
        }
        rangs = calculer_rangs(moyennes)
        assert rangs["a"] == 1
        assert rangs["c"] == 1
        assert rangs["b"] == 3
        assert rangs["d"] is None

    def test_determiner_mention(self):
        assert determiner_mention(16.5) == "Très Bien"
        assert determiner_mention(14.0) == "Bien"
        assert determiner_mention(12.0) == "Assez Bien"
        assert determiner_mention(10.0) == "Passable"
        assert determiner_mention(8.0) == "Insuffisant"
        assert determiner_mention(None) is None
