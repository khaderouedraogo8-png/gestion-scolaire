#!/usr/bin/env python3
"""Validation E2E des modules via API."""
import json
import sys
import uuid
from pathlib import Path

# Permet l'exécution directe : python scripts/e2e_api_validation.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app


def ok(label, cond, detail=""):
    status = "OK" if cond else "FAIL"
    print(f"[{status}] {label}" + (f" — {detail}" if detail else ""))
    return cond


def main():
    app = create_app()
    client = app.test_client()
    results = []

    login = client.post("/api/login", json={"email": "admin@ecole.local", "password": "Admin123!"})
    results.append(ok("Auth login", login.status_code == 200, str(login.status_code)))
    if login.status_code != 200:
        print(json.dumps(login.get_json(), indent=2))
        return 1

    token = login.get_json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    annees = client.get("/api/etablissement/annees", headers=h)
    annee_id = annees.get_json()[0]["id"] if annees.status_code == 200 else None
    results.append(ok("Config années", annees.status_code == 200))

    eleves = client.get("/api/eleves/", headers=h, query_string={"id_annee": annee_id})
    results.append(ok("Module 1 — Élèves", eleves.status_code == 200 and eleves.get_json().get("total", 0) > 0,
                      f"{eleves.get_json().get('total', 0)} élèves"))

    matieres = client.get("/api/notes/matieres", headers=h)
    results.append(ok("Module 2 — Matières", matieres.status_code == 200 and len(matieres.get_json()) > 0))

    evals = client.get("/api/notes/evaluations", headers=h)
    results.append(ok("Module 2 — Évaluations", evals.status_code == 200))

    frais = client.get("/api/finance/frais", headers=h)
    results.append(ok("Module 3 — Frais", frais.status_code == 200 and len(frais.get_json()) > 0))

    arrieres = client.get("/api/finance/arrieres", headers=h, query_string={"id_annee": annee_id})
    results.append(ok("Module 3 — Arriérés", arrieres.status_code == 200))

    enseignants = client.get("/api/emploi-temps/enseignants", headers=h)
    results.append(ok("Module 4 — Enseignants", enseignants.status_code == 200 and len(enseignants.get_json()) > 0))

    creneaux = client.get("/api/emploi-temps/creneaux", headers=h)
    results.append(ok("Module 4 — Créneaux", creneaux.status_code == 200))

    absences = client.get("/api/absences/", headers=h)
    results.append(ok("Module 5 — Absences", absences.status_code == 200))

    docs = client.get("/api/documents/", headers=h)
    results.append(ok("Module 6 — Documents", docs.status_code == 200))

    notifs = client.get("/api/notifications/", headers=h)
    results.append(ok("Module 7 — Notifications", notifs.status_code == 200))

    stats = client.get("/api/dashboard/stats", headers=h, query_string={"id_annee": annee_id})
    d = stats.get_json() if stats.status_code == 200 else {}
    results.append(ok("Module 8 — Dashboard", stats.status_code == 200 and d.get("total_eleves_inscrits", 0) > 0,
                      f"{d.get('total_eleves_inscrits', 0)} inscrits, trésorerie {d.get('tresorerie', 0)}"))

    passed = sum(results)
    total = len(results)
    print(f"\n=== Résultat : {passed}/{total} modules validés ===")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
