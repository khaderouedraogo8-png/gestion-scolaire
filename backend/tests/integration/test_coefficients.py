"""Tests coefficients matière."""


class TestCoefficients:
    def test_list_and_create_coefficient(self, client, auth_headers, db):
        from app.models import CoefficientMatiere, Matiere, NiveauEtude

        matiere = db.query(Matiere).first()
        niveau = db.query(NiveauEtude).first()
        assert matiere and niveau

        r = client.post(
            "/api/notes/coefficients",
            json={
                "id_matiere": str(matiere.id),
                "id_niveau": str(niveau.id),
                "coefficient": 3,
            },
            headers=auth_headers,
        )
        assert r.status_code in (200, 201)

        r2 = client.get(
            f"/api/notes/coefficients?id_niveau={niveau.id}",
            headers=auth_headers,
        )
        assert r2.status_code == 200
        data = r2.get_json()
        assert any(float(c["coefficient"]) == 3 for c in data)

        coef = db.query(CoefficientMatiere).filter(
            CoefficientMatiere.id_matiere == matiere.id,
            CoefficientMatiere.id_niveau == niveau.id,
        ).first()
        assert coef is not None
