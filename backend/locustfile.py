"""Tests de charge Locust — saisie notes / auth.

Usage (depuis backend/) :
  pip install locust
  locust -f locustfile.py --host=http://localhost:5000

Scénario : connexion admin puis lecture des endpoints critiques.
"""
from locust import HttpUser, between, task


class GestionScolaireUser(HttpUser):
    wait_time = between(1, 3)
    token = None

    def on_start(self):
        response = self.client.post(
            "/api/login",
            json={"email": "admin@ecole.local", "password": "Admin123!"},
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token")

    @property
    def headers(self):
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def list_eleves(self):
        self.client.get("/api/eleves", headers=self.headers)

    @task(2)
    def list_evaluations(self):
        self.client.get("/api/notes/evaluations", headers=self.headers)

    @task(2)
    def dashboard_stats(self):
        self.client.get("/api/dashboard/stats", headers=self.headers)

    @task(1)
    def list_arrieres(self):
        annees = self.client.get("/api/etablissement/annees", headers=self.headers)
        if annees.status_code != 200:
            return
        data = annees.json()
        if not data:
            return
        active = next((a for a in data if a.get("est_active")), data[0])
        self.client.get(
            f"/api/finance/arrieres?id_annee={active['id']}",
            headers=self.headers,
        )
