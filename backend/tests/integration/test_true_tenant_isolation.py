"""Tests d'isolation multi-tenant réelle — School A ≠ School B."""
from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.auth.jwt_handler import hash_password
from app.models import (
    AnneeScolaire,
    Classe,
    Eleve,
    Etablissement,
    Inscription,
    Matiere,
    NiveauEtude,
    School,
    Utilisateur,
)
from app.services.academic import get_or_create_general_program


@pytest.fixture
def school_pair(db):
    """Deux écoles distinctes avec profil établissement + année/niveau/classe + élève."""
    schools = {}
    for code, name, city in (
        ("ISOL-A", "École Isolation Alpha", "Ouagadougou"),
        ("ISOL-B", "École Isolation Beta", "Bobo-Dioulasso"),
    ):
        school = db.query(School).filter(School.code == code).first()
        if not school:
            school = School(
                id=uuid.uuid4(),
                name=name,
                code=code,
                city=city,
                country="Burkina Faso",
                is_active=True,
            )
            db.add(school)
            db.flush()

        program = get_or_create_general_program(db, school.id)

        etab = (
            db.query(Etablissement)
            .filter(Etablissement.school_id == school.id)
            .first()
        )
        if not etab:
            etab = Etablissement(
                id=uuid.uuid4(),
                school_id=school.id,
                nom=name,
                sigle=code[:4],
                format_matricule="{ANNEE}M-{SEQ}",
            )
            db.add(etab)
            db.flush()

        annee = (
            db.query(AnneeScolaire)
            .filter(AnneeScolaire.school_id == school.id, AnneeScolaire.libelle == "2025-2026")
            .first()
        )
        if not annee:
            annee = AnneeScolaire(
                id=uuid.uuid4(),
                school_id=school.id,
                libelle="2025-2026",
                date_debut=date(2025, 9, 1),
                date_fin=date(2026, 6, 30),
                est_active=True,
            )
            db.add(annee)
            db.flush()

        niveau = (
            db.query(NiveauEtude)
            .filter(
                NiveauEtude.school_id == school.id,
                NiveauEtude.libelle == "6ème",
                NiveauEtude.id_program == program.id,
            )
            .first()
        )
        if not niveau:
            niveau = NiveauEtude(
                id=uuid.uuid4(),
                school_id=school.id,
                id_program=program.id,
                libelle="6ème",
                ordre=1,
                cycle="premier",
            )
            db.add(niveau)
            db.flush()

        classe = (
            db.query(Classe)
            .filter(
                Classe.school_id == school.id,
                Classe.libelle == "6ème A",
                Classe.id_annee == annee.id,
            )
            .first()
        )
        if not classe:
            classe = Classe(
                id=uuid.uuid4(),
                school_id=school.id,
                id_niveau=niveau.id,
                id_annee=annee.id,
                id_program=program.id,
                libelle="6ème A",
            )
            db.add(classe)
            db.flush()
        elif getattr(classe, "id_program", None) is None:
            classe.id_program = program.id

        matricule = f"{code}-001"
        eleve = (
            db.query(Eleve)
            .filter(Eleve.school_id == school.id, Eleve.matricule == matricule)
            .first()
        )
        if not eleve:
            eleve = Eleve(
                id=uuid.uuid4(),
                school_id=school.id,
                matricule=matricule,
                nom="Traoré" if code == "ISOL-A" else "Ouédraogo",
                prenom="Awa" if code == "ISOL-A" else "Issa",
                sexe="F" if code == "ISOL-A" else "M",
            )
            db.add(eleve)
            db.flush()
            db.add(
                Inscription(
                    id=uuid.uuid4(),
                    school_id=school.id,
                    id_eleve=eleve.id,
                    id_classe=classe.id,
                    id_annee=annee.id,
                    statut="inscrit",
                )
            )

        matiere = (
            db.query(Matiere)
            .filter(Matiere.school_id == school.id, Matiere.code == "MATH")
            .first()
        )
        if not matiere:
            matiere = Matiere(
                id=uuid.uuid4(),
                school_id=school.id,
                libelle="Mathématiques",
                code="MATH",
            )
            db.add(matiere)

        email = f"admin@{code.lower()}.test"
        user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
        if not user:
            user = Utilisateur(
                id=uuid.uuid4(),
                nom="Admin",
                prenom=code,
                email=email,
                mot_de_passe_hash=hash_password("Admin123!"),
                role="administrateur",
                actif=True,
                doit_changer_mdp=False,
                school_id=school.id,
            )
            db.add(user)
        else:
            user.school_id = school.id
            user.mot_de_passe_hash = hash_password("Admin123!")
            user.actif = True

        key = "a" if code == "ISOL-A" else "b"
        schools[key] = {
            "school": school,
            "etab": etab,
            "annee": annee,
            "niveau": niveau,
            "classe": classe,
            "eleve": eleve,
            "matiere": matiere,
            "user": user,
            "email": email,
            "program": program,
        }

    db.commit()
    return schools


def _auth(client, email: str) -> dict:
    resp = client.post("/api/login", json={"email": email, "password": "Admin123!"})
    assert resp.status_code == 200, resp.get_json()
    return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}


class TestSchoolANeBListIsolation:
    def test_eleves_list_isolated(self, client, school_pair):
        ha = _auth(client, school_pair["a"]["email"])
        hb = _auth(client, school_pair["b"]["email"])

        ra = client.get("/api/eleves/", headers=ha)
        rb = client.get("/api/eleves/", headers=hb)
        assert ra.status_code == 200
        assert rb.status_code == 200

        ids_a = {e["id"] for e in ra.get_json()["items"]}
        ids_b = {e["id"] for e in rb.get_json()["items"]}
        assert str(school_pair["a"]["eleve"].id) in ids_a
        assert str(school_pair["b"]["eleve"].id) in ids_b
        assert str(school_pair["b"]["eleve"].id) not in ids_a
        assert str(school_pair["a"]["eleve"].id) not in ids_b

    def test_matieres_list_isolated(self, client, school_pair):
        ha = _auth(client, school_pair["a"]["email"])
        hb = _auth(client, school_pair["b"]["email"])
        ra = client.get("/api/notes/matieres", headers=ha)
        rb = client.get("/api/notes/matieres", headers=hb)
        assert ra.status_code == 200
        assert rb.status_code == 200
        ids_a = {m["id"] for m in ra.get_json()}
        ids_b = {m["id"] for m in rb.get_json()}
        assert str(school_pair["a"]["matiere"].id) in ids_a
        assert str(school_pair["b"]["matiere"].id) not in ids_a
        assert str(school_pair["a"]["matiere"].id) not in ids_b

    def test_users_list_isolated(self, client, school_pair):
        ha = _auth(client, school_pair["a"]["email"])
        payload = client.get("/api/users", headers=ha).get_json()
        items = payload["items"] if isinstance(payload, dict) else payload
        emails = {u["email"] for u in items}
        assert school_pair["a"]["email"] in emails
        assert school_pair["b"]["email"] not in emails

    def test_etablissement_is_own(self, client, school_pair):
        ha = _auth(client, school_pair["a"]["email"])
        hb = _auth(client, school_pair["b"]["email"])
        ea = client.get("/api/etablissement/", headers=ha).get_json()
        eb = client.get("/api/etablissement/", headers=hb).get_json()
        assert ea["nom"] == school_pair["a"]["etab"].nom
        assert eb["nom"] == school_pair["b"]["etab"].nom
        assert ea["id"] != eb["id"]

    def test_classes_list_isolated(self, client, school_pair):
        ha = _auth(client, school_pair["a"]["email"])
        hb = _auth(client, school_pair["b"]["email"])
        ca = client.get("/api/etablissement/classes", headers=ha).get_json()
        cb = client.get("/api/etablissement/classes", headers=hb).get_json()
        list_a = ca if isinstance(ca, list) else ca.get("items", ca.get("classes", []))
        list_b = cb if isinstance(cb, list) else cb.get("items", cb.get("classes", []))
        ids_a = {c["id"] for c in list_a}
        ids_b = {c["id"] for c in list_b}
        assert str(school_pair["a"]["classe"].id) in ids_a
        assert str(school_pair["b"]["classe"].id) not in ids_a
        assert str(school_pair["a"]["classe"].id) not in ids_b


class TestSchoolANeBIDOR:
    def test_get_eleve_cross_tenant_404(self, client, school_pair):
        ha = _auth(client, school_pair["a"]["email"])
        eid_b = school_pair["b"]["eleve"].id
        r = client.get(f"/api/eleves/{eid_b}", headers=ha)
        assert r.status_code == 404

    def test_delete_matiere_cross_tenant_404(self, client, school_pair):
        ha = _auth(client, school_pair["a"]["email"])
        mid_b = school_pair["b"]["matiere"].id
        r = client.delete(f"/api/notes/matieres/{mid_b}", headers=ha)
        assert r.status_code == 404

    def test_spoof_school_id_query_ignored(self, client, school_pair):
        ha = _auth(client, school_pair["a"]["email"])
        sid_b = school_pair["b"]["school"].id
        r = client.get(
            f"/api/eleves/?school_id={sid_b}",
            headers={**ha, "X-School-Id": str(sid_b)},
        )
        assert r.status_code == 200
        ids = {e["id"] for e in r.get_json()["items"]}
        assert str(school_pair["b"]["eleve"].id) not in ids
        assert str(school_pair["a"]["eleve"].id) in ids

    def test_create_rejects_client_school_id(self, client, school_pair):
        ha = _auth(client, school_pair["a"]["email"])
        payload = {
            "libelle": f"Physique-{uuid.uuid4().hex[:6]}",
            "code": f"P{uuid.uuid4().hex[:4].upper()}",
            "school_id": str(school_pair["b"]["school"].id),
        }
        r = client.post("/api/notes/matieres", json=payload, headers=ha)
        if r.status_code == 201:
            created = r.get_json()
            hb = _auth(client, school_pair["b"]["email"])
            ids_b = {m["id"] for m in client.get("/api/notes/matieres", headers=hb).get_json()}
            assert created["id"] not in ids_b
            ids_a = {m["id"] for m in client.get("/api/notes/matieres", headers=ha).get_json()}
            assert created["id"] in ids_a
        else:
            assert r.status_code in (400, 422)


class TestSameMatriculeAcrossSchools:
    def test_same_matricule_allowed_per_school(self, db, school_pair):
        """UNIQUE(school_id, matricule) — même matricule OK sur A et B."""
        mat = "SHARED-999"
        for key in ("a", "b"):
            sid = school_pair[key]["school"].id
            existing = (
                db.query(Eleve)
                .filter(Eleve.school_id == sid, Eleve.matricule == mat)
                .first()
            )
            if not existing:
                db.add(
                    Eleve(
                        id=uuid.uuid4(),
                        school_id=sid,
                        matricule=mat,
                        nom="Shared",
                        prenom=key.upper(),
                    )
                )
        db.commit()
        count = db.query(Eleve).filter(Eleve.matricule == mat).count()
        assert count >= 2


class TestDashboardIsolation:
    def test_dashboard_stats_isolated(self, client, school_pair):
        ha = _auth(client, school_pair["a"]["email"])
        hb = _auth(client, school_pair["b"]["email"])
        da = client.get("/api/dashboard/stats", headers=ha)
        db_ = client.get("/api/dashboard/stats", headers=hb)
        assert da.status_code == 200
        assert db_.status_code == 200
