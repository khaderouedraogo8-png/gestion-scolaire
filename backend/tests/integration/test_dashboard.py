"""Tests d'intégration — dashboard."""
class TestDashboard:
    def test_stats(self, client, auth_headers, annee_classe):
        response = client.get(
            f"/api/dashboard/stats?id_annee={annee_classe['annee'].id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "effectifs_par_niveau" in data
        assert "total_eleves_inscrits" in data
