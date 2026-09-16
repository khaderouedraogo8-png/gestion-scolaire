"""Tests ERP finalisation — RBAC rôles + digest absences + inbox parent."""
import uuid
from datetime import date, timedelta

from app.auth.jwt_handler import hash_password
from app.models import (
    Absence,
    Eleve,
    EleveParent,
    Inscription,
    Notification,
    ParentTuteur,
    Utilisateur,
)
from app.services.digest_absences import digest_absences_hebdo, iso_week_bounds


def _auth(client, email, password="Pass1234!"):
    res = client.post("/api/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.get_json()
    return {"Authorization": f"Bearer {res.get_json()['access_token']}"}


def _make_user(db, school_id, role, suffix):
    user = Utilisateur(
        id=uuid.uuid4(),
        nom=role.title(),
        prenom="Test",
        email=f"{role}-{suffix}@ecole.local",
        mot_de_passe_hash=hash_password("Pass1234!"),
        role=role,
        actif=True,
        doit_changer_mdp=False,
        school_id=school_id,
    )
    db.add(user)
    db.flush()
    return user


def test_secretariat_forbidden_finance_and_rulesets(
    client, db, annee_classe, default_school
):
    suffix = uuid.uuid4().hex[:8]
    user = _make_user(db, default_school.id, "secretariat", suffix)
    db.commit()
    headers = _auth(client, user.email)

    assert client.get("/api/finance/frais", headers=headers).status_code == 403
    assert client.get(
        f"/api/finance/arrieres?id_annee={annee_classe['annee'].id}",
        headers=headers,
    ).status_code == 403
    assert client.get("/api/grading-rulesets", headers=headers).status_code == 403


def test_comptable_finance_ok_notes_rulesets_forbidden(
    client, db, annee_classe, default_school
):
    suffix = uuid.uuid4().hex[:8]
    user = _make_user(db, default_school.id, "agent_comptable", suffix)
    db.commit()
    headers = _auth(client, user.email)

    assert client.get("/api/finance/frais", headers=headers).status_code == 200
    assert client.get(
        f"/api/dashboard/stats?id_annee={annee_classe['annee'].id}",
        headers=headers,
    ).status_code == 200
    assert client.get("/api/grading-rulesets", headers=headers).status_code == 403
    assert client.get("/api/notes/evaluations", headers=headers).status_code == 403


def test_enseignant_dashboard_accessible(client, db, default_school):
    suffix = uuid.uuid4().hex[:8]
    user = _make_user(db, default_school.id, "enseignant", suffix)
    db.commit()
    headers = _auth(client, user.email)

    # Ancien bug : /dashboard/stats 403 — désormais endpoint dédié
    assert client.get("/api/dashboard/stats", headers=headers).status_code == 403
    r = client.get("/api/dashboard/enseignant", headers=headers)
    assert r.status_code == 200
    data = r.get_json()
    assert "classes" in data
    assert "evaluations_ouvertes" in data


def test_directeur_dashboard_stats(client, db, annee_classe, default_school):
    suffix = uuid.uuid4().hex[:8]
    user = _make_user(db, default_school.id, "directeur", suffix)
    db.commit()
    headers = _auth(client, user.email)
    r = client.get(
        f"/api/dashboard/stats?id_annee={annee_classe['annee'].id}",
        headers=headers,
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "total_eleves_inscrits" in data
    assert data.get("role_view") == "directeur"


def test_parent_inbox_and_isolation(client, db, annee_classe, default_school):
    suffix = uuid.uuid4().hex[:8]
    sid = default_school.id
    annee = annee_classe["annee"]
    classe = annee_classe["classe"]

    eleve_a = Eleve(
        id=uuid.uuid4(),
        matricule=f"INB-A-{suffix}",
        nom="Alpha",
        prenom="Enfant",
        sexe="M",
        school_id=sid,
    )
    eleve_b = Eleve(
        id=uuid.uuid4(),
        matricule=f"INB-B-{suffix}",
        nom="Beta",
        prenom="Enfant",
        sexe="F",
        school_id=sid,
    )
    db.add_all([eleve_a, eleve_b])
    db.flush()
    for e in (eleve_a, eleve_b):
        db.add(
            Inscription(
                id=uuid.uuid4(),
                id_eleve=e.id,
                id_classe=classe.id,
                id_annee=annee.id,
                statut="inscrit",
                school_id=sid,
            )
        )

    user_a = _make_user(db, sid, "parent", f"a-{suffix}")
    user_b = _make_user(db, sid, "parent", f"b-{suffix}")
    parent_a = ParentTuteur(
        id=uuid.uuid4(),
        nom="A",
        prenom="Parent",
        telephone="70000001",
        email=user_a.email,
        id_utilisateur=user_a.id,
        school_id=sid,
    )
    parent_b = ParentTuteur(
        id=uuid.uuid4(),
        nom="B",
        prenom="Parent",
        telephone="70000002",
        email=user_b.email,
        id_utilisateur=user_b.id,
        school_id=sid,
    )
    db.add_all([parent_a, parent_b])
    db.flush()
    db.add(EleveParent(id_eleve=eleve_a.id, id_parent=parent_a.id, tuteur_legal=True))
    db.add(EleveParent(id_eleve=eleve_b.id, id_parent=parent_b.id, tuteur_legal=True))

    notif_a = Notification(
        id=uuid.uuid4(),
        school_id=sid,
        id_parent=parent_a.id,
        id_eleve=eleve_a.id,
        canal="interne",
        type_notification="absence",
        contenu="Absence enfant A",
        statut="envoye",
    )
    notif_b = Notification(
        id=uuid.uuid4(),
        school_id=sid,
        id_parent=parent_b.id,
        id_eleve=eleve_b.id,
        canal="interne",
        type_notification="absence",
        contenu="Absence enfant B",
        statut="envoye",
    )
    db.add_all([notif_a, notif_b])
    db.commit()

    headers_a = _auth(client, user_a.email)
    inbox = client.get("/api/notifications/me", headers=headers_a)
    assert inbox.status_code == 200
    items = inbox.get_json()["items"]
    assert any(i["contenu"] == "Absence enfant A" for i in items)
    assert not any(i["contenu"] == "Absence enfant B" for i in items)

    # Mark read
    mark = client.post(f"/api/notifications/me/{notif_a.id}/lu", headers=headers_a)
    assert mark.status_code == 200
    assert mark.get_json()["lu"] is True

    # Parent A cannot mark parent B notification
    forbidden = client.post(f"/api/notifications/me/{notif_b.id}/lu", headers=headers_a)
    assert forbidden.status_code == 403


def test_digest_absences_idempotent_and_multi_children(
    client, db, annee_classe, default_school, auth_headers
):
    suffix = uuid.uuid4().hex[:8]
    sid = default_school.id
    annee = annee_classe["annee"]
    classe = annee_classe["classe"]
    # Semaine déterministe unique pour éviter collisions entre runs
    ref = date(2019, 3, 12)  # mardi → semaine ISO 2019-W11
    debut, _fin, week_key = iso_week_bounds(ref)

    e1 = Eleve(
        id=uuid.uuid4(),
        matricule=f"DIG1-{suffix}",
        nom="Diallo",
        prenom="Awa",
        sexe="F",
        school_id=sid,
    )
    e2 = Eleve(
        id=uuid.uuid4(),
        matricule=f"DIG2-{suffix}",
        nom="Diallo",
        prenom="Ibra",
        sexe="M",
        school_id=sid,
    )
    db.add_all([e1, e2])
    db.flush()
    for e in (e1, e2):
        db.add(
            Inscription(
                id=uuid.uuid4(),
                id_eleve=e.id,
                id_classe=classe.id,
                id_annee=annee.id,
                statut="inscrit",
                school_id=sid,
            )
        )

    user = _make_user(db, sid, "parent", f"dig-{suffix}")
    parent = ParentTuteur(
        id=uuid.uuid4(),
        nom="Diallo",
        prenom="Parent",
        telephone="70000999",
        email=user.email,
        id_utilisateur=user.id,
        school_id=sid,
    )
    db.add(parent)
    db.flush()
    db.add(EleveParent(id_eleve=e1.id, id_parent=parent.id, tuteur_legal=True))
    db.add(EleveParent(id_eleve=e2.id, id_parent=parent.id, tuteur_legal=True))

    for e in (e1, e2):
        db.add(
            Absence(
                id=uuid.uuid4(),
                id_eleve=e.id,
                date_absence=debut + timedelta(days=1),
                justifiee=False,
                motif="Test digest",
                type_absence="absence",
                school_id=sid,
            )
        )
    db.commit()

    # Nettoyer d'éventuels digests d'un run précédent (même semaine déterministe)
    db.query(Notification).filter(
        Notification.school_id == sid,
        Notification.idempotency_key.like(f"%:{week_key}%"),
    ).delete(synchronize_session=False)
    db.commit()

    r1 = digest_absences_hebdo(db, sid, ref_date=ref, canal="email", auto_envoyer=False)
    assert r1["week_key"] == week_key
    assert r1["admin_digest_cree"] is True
    assert r1["parents_digest_crees"] >= 1
    assert r1["total_absences"] >= 2

    r2 = digest_absences_hebdo(db, sid, ref_date=ref, canal="email", auto_envoyer=False)
    assert r2["admin_digest_cree"] is False
    assert r2["parents_ignores"] >= 1

    parent_notifs = (
        db.query(Notification)
        .filter(
            Notification.id_parent == parent.id,
            Notification.type_notification == "digest_absences",
            Notification.canal == "interne",
        )
        .all()
    )
    assert len(parent_notifs) == 1
    assert "Awa" in (parent_notifs[0].contenu or "")
    assert "Ibra" in (parent_notifs[0].contenu or "")

    # API trigger admin (semaine courante — idempotent si déjà généré)
    api = client.post("/api/notifications/digest-absences", headers=auth_headers, json={})
    assert api.status_code == 200
    assert "week_key" in api.get_json()


def test_parent_evolution_endpoint(client, db, annee_classe, default_school):
    suffix = uuid.uuid4().hex[:8]
    sid = default_school.id
    annee = annee_classe["annee"]
    classe = annee_classe["classe"]

    eleve = Eleve(
        id=uuid.uuid4(),
        matricule=f"EVO-{suffix}",
        nom="Test",
        prenom="Evo",
        sexe="M",
        school_id=sid,
    )
    db.add(eleve)
    db.flush()
    db.add(
        Inscription(
            id=uuid.uuid4(),
            id_eleve=eleve.id,
            id_classe=classe.id,
            id_annee=annee.id,
            statut="inscrit",
            school_id=sid,
        )
    )
    user = _make_user(db, sid, "parent", f"evo-{suffix}")
    parent = ParentTuteur(
        id=uuid.uuid4(),
        nom="P",
        prenom="Evo",
        telephone="70111111",
        id_utilisateur=user.id,
        school_id=sid,
    )
    db.add(parent)
    db.flush()
    db.add(EleveParent(id_eleve=eleve.id, id_parent=parent.id, tuteur_legal=True))
    db.commit()

    headers = _auth(client, user.email)
    r = client.get("/api/dashboard/parent-evolution", headers=headers)
    assert r.status_code == 200
    data = r.get_json()
    assert any(e["id_eleve"] == str(eleve.id) for e in data["enfants"])
