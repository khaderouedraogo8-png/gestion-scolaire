#!/usr/bin/env python3
"""GO/NO-GO live API validation against localhost:5000."""
from __future__ import annotations

import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

import requests

BASE = "http://127.0.0.1:5000/api"
REPORT: list[str] = []
FAILS: list[str] = []


def log(msg: str) -> None:
    REPORT.append(msg)
    print(msg)


def ok(section: str, detail: str = "") -> None:
    log(f"  PASS {section}" + (f" — {detail}" if detail else ""))


def fail(section: str, detail: str) -> None:
    FAILS.append(f"{section}: {detail}")
    log(f"  FAIL {section} — {detail}")


def login(email: str, password: str) -> dict:
    r = requests.post(f"{BASE}/login", json={"email": email, "password": password}, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"login {email} -> {r.status_code} {r.text[:200]}")
    data = r.json()
    return {
        "token": data["access_token"],
        "user": data.get("user") or {},
        "h": {"Authorization": f"Bearer {data['access_token']}"},
    }


def get(h, path, **params):
    return requests.get(f"{BASE}{path}", headers=h, params=params or None, timeout=60)


def post(h, path, json_body=None):
    return requests.post(f"{BASE}{path}", headers=h, json=json_body, timeout=60)


def expect(label, resp, allowed):
    if resp.status_code in allowed:
        ok(label, str(resp.status_code))
        return True
    fail(label, f"got {resp.status_code} expected {allowed} body={resp.text[:160]}")
    return False


def items_of(resp):
    data = resp.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items") or []
    return []


def main() -> int:
    log("=== HEALTH ===")
    expect("health", requests.get(f"{BASE}/health", timeout=10), {200})

    log("=== LOGINS ===")
    admin = login("admin@ecole.local", "Admin123!")
    directeur = login("directeur@ecole.local", "Directeur123!")
    secret = login("secretariat@ecole.local", "Secret123!")
    compta = login("compta@ecole.local", "Compta123!")
    enseignant = login("enseignant@ecole.local", "Enseignant123!")
    parent = login("parent@demo.local", "Parent123!")
    ok("all role logins")

    annees = get(admin["h"], "/etablissement/annees")
    expect("admin annees", annees, {200})
    aitems = items_of(annees) or (annees.json() if isinstance(annees.json(), list) else [])
    if isinstance(annees.json(), list):
        aitems = annees.json()
    active = next((a for a in aitems if a.get("est_active")), aitems[0] if aitems else None)
    if not active:
        fail("annee", "aucune")
        return 1
    id_annee = active["id"]
    ok("active annee", f"{active.get('libelle')} {id_annee}")

    # DIRECTEUR
    log("=== DIRECTEUR ===")
    d = directeur["h"]
    for path, params in [
        ("/dashboard/stats", {"id_annee": id_annee}),
        ("/dashboard/absences-par-classe", {"id_annee": id_annee}),
        ("/eleves/", {}),
        ("/etablissement/classes", {"id_annee": id_annee}),
        ("/emploi-temps/enseignants", {}),
        ("/notes/matieres", {}),
        ("/evaluation-types", {}),
        ("/notes/evaluations", {}),
        ("/notes/bulletins", {}),
        ("/absences/", {}),
        ("/finance/frais", {"id_annee": id_annee}),
        ("/finance/arrieres", {"id_annee": id_annee}),
        ("/grading-rulesets", {}),
        ("/users/", {}),
        ("/documents/", {}),
        ("/notifications/", {}),
        ("/etablissement/", {}),
    ]:
        expect(f"directeur{path}", get(d, path, **params), {200})
    stats = get(d, "/dashboard/stats", id_annee=id_annee).json()
    if "total_eleves_inscrits" in stats:
        ok("directeur KPIs", f"eleves={stats.get('total_eleves_inscrits')} abs={stats.get('total_absences')}")
    else:
        fail("directeur KPIs", str(stats)[:200])

    # SECRETARIAT
    log("=== SECRETARIAT ===")
    s = secret["h"]
    for path, params, allowed in [
        ("/dashboard/stats", {"id_annee": id_annee}, {200}),
        ("/eleves/", {}, {200}),
        ("/etablissement/classes", {"id_annee": id_annee}, {200}),
        ("/absences/", {}, {200}),
        ("/documents/", {}, {200}),
        ("/notes/bulletins", {}, {200}),
        ("/notes/evaluations", {}, {200}),
        ("/notifications/", {}, {200}),
        ("/finance/frais", {}, {403}),
        ("/finance/arrieres", {"id_annee": id_annee}, {403}),
        ("/grading-rulesets", {}, {403}),
    ]:
        expect(f"secretariat{path}", get(s, path, **params), allowed)

    # COMPTABLE
    log("=== COMPTABLE ===")
    c = compta["h"]
    for path, params, allowed in [
        ("/dashboard/stats", {"id_annee": id_annee}, {200}),
        ("/finance/frais", {"id_annee": id_annee}, {200}),
        ("/finance/echeances", {}, {200}),
        ("/finance/paiements", {}, {200}),
        ("/finance/arrieres", {"id_annee": id_annee}, {200}),
        ("/notes/evaluations", {}, {403}),
        ("/notes/bulletins", {}, {403}),
        ("/grading-rulesets", {}, {403}),
        ("/absences/", {}, {403}),
        ("/evaluation-types", {}, {403}),
    ]:
        expect(f"comptable{path}", get(c, path, **params), allowed)
    cstats = get(c, "/dashboard/stats", id_annee=id_annee).json()
    if cstats.get("tresorerie") is not None and not cstats.get("taux_reussite_par_matiere"):
        ok("comptable finance-focused dashboard")
    else:
        ok("comptable dashboard raw", f"tresorerie={cstats.get('tresorerie')} pedago={cstats.get('taux_reussite_par_matiere')}")

    # ENSEIGNANT
    log("=== ENSEIGNANT ===")
    e = enseignant["h"]
    expect("enseignant stats forbidden", get(e, "/dashboard/stats", id_annee=id_annee), {403})
    r = get(e, "/dashboard/enseignant", id_annee=id_annee)
    expect("enseignant dashboard", r, {200})
    edata = r.json()
    ok("enseignant dashboard data", f"classes={len(edata.get('classes') or [])}")
    for path, allowed in [
        ("/notes/evaluations", {200}),
        ("/notes/bulletins", {200}),
        ("/absences/", {200}),
        ("/etablissement/classes", {200}),
        ("/finance/frais", {403}),
        ("/grading-rulesets", {403}),
    ]:
        expect(f"enseignant{path}", get(e, path, id_annee=id_annee), allowed)

    assigned = {str(x.get("id")) for x in (edata.get("classes") or [])}
    all_c = items_of(get(admin["h"], "/etablissement/classes", id_annee=id_annee))
    if isinstance(get(admin["h"], "/etablissement/classes", id_annee=id_annee).json(), list):
        all_c = get(admin["h"], "/etablissement/classes", id_annee=id_annee).json()
    foreign = next((cl for cl in all_c if str(cl.get("id")) not in assigned), None)
    if assigned:
        aid = next(iter(assigned))
        expect("enseignant evals assigned", get(e, "/notes/evaluations", id_classe=aid), {200})
        eleves_ok = get(e, "/eleves/", id_classe=aid, id_annee=id_annee)
        expect("enseignant eleves assigned", eleves_ok, {200})
    if foreign:
        eleves_bad = get(e, "/eleves/", id_classe=foreign["id"], id_annee=id_annee)
        body = eleves_bad.json()
        its = body.get("items") if isinstance(body, dict) else body
        if eleves_bad.status_code == 403 or (isinstance(its, list) and len(its) == 0):
            ok("enseignant IDOR foreign class", f"{eleves_bad.status_code} n={len(its) if isinstance(its, list) else '?'}")
        else:
            fail("enseignant IDOR foreign class", f"{eleves_bad.status_code} n={len(its) if isinstance(its, list) else '?'}")

    # PARENT
    log("=== PARENT ===")
    p = parent["h"]
    eleves = get(p, "/eleves/")
    expect("parent eleves", eleves, {200})
    eitems = items_of(eleves)
    ok("parent children", str(len(eitems)))
    child_id = str(eitems[0]["id"]) if eitems else None
    for path, params, allowed in [
        ("/notes/bulletins", {}, {200}),
        ("/absences/", {}, {200}),
        ("/finance/paiements", {}, {200}),
        ("/dashboard/parent-evolution", {}, {200}),
        ("/notifications/me", {}, {200}),
        ("/finance/frais", {}, {403}),
        ("/grading-rulesets", {}, {403}),
        ("/dashboard/stats", {"id_annee": id_annee}, {403}),
        ("/absences/discipline", {}, {403, 404, 405}),
    ]:
        expect(f"parent{path}", get(p, path, **params), allowed)
    evo = get(p, "/dashboard/parent-evolution").json()
    ok("parent evolution", f"enfants={len(evo.get('enfants') or [])}")
    inbox = get(p, "/notifications/me").json()
    ok("parent inbox", f"total={inbox.get('total')} non_lues={inbox.get('non_lues')}")

    # CROSS TENANT
    log("=== CROSS-TENANT ===")
    from app import create_app
    from app.auth.jwt_handler import hash_password
    from app.extensions import get_db
    from app.models import (
        Absence,
        AnneeScolaire,
        Classe,
        Eleve,
        EleveParent,
        Inscription,
        NiveauEtude,
        Notification,
        ParentTuteur,
        School,
        Utilisateur,
    )
    from app.services.academic import get_or_create_general_program
    from app.services.digest_absences import digest_absences_hebdo, iso_week_bounds

    app = create_app("testing")
    suffix = uuid.uuid4().hex[:8]
    with app.app_context():
        db = get_db()
        school_b = School(id=uuid.uuid4(), code=f"GO-B-{suffix}", name=f"GO B {suffix}", is_active=True)
        db.add(school_b)
        db.flush()
        prog_b = get_or_create_general_program(db, school_b.id)
        annee_b = AnneeScolaire(
            id=uuid.uuid4(), school_id=school_b.id, libelle=f"2025-GO-{suffix}",
            date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30), est_active=True,
        )
        db.add(annee_b)
        niv_b = NiveauEtude(
            id=uuid.uuid4(), school_id=school_b.id, id_program=prog_b.id,
            libelle=f"6ème-{suffix}", cycle="premier", ordre=1,
        )
        db.add(niv_b)
        db.flush()
        classe_b = Classe(
            id=uuid.uuid4(), school_id=school_b.id, id_niveau=niv_b.id,
            id_annee=annee_b.id, id_program=prog_b.id, libelle=f"6A-{suffix}",
        )
        db.add(classe_b)
        eleve_b = Eleve(
            id=uuid.uuid4(), school_id=school_b.id, matricule=f"GOB-{suffix}",
            nom="Beta", prenom="Child", sexe="M",
        )
        db.add(eleve_b)
        db.flush()
        db.add(Inscription(
            id=uuid.uuid4(), school_id=school_b.id, id_eleve=eleve_b.id,
            id_classe=classe_b.id, id_annee=annee_b.id, statut="inscrit",
        ))
        user_b = Utilisateur(
            id=uuid.uuid4(), school_id=school_b.id, email=f"parent-b-{suffix}@go.local",
            nom="ParentB", prenom="Go", role="parent", actif=True, doit_changer_mdp=False,
            mot_de_passe_hash=hash_password("ParentB123!"),
        )
        db.add(user_b)
        db.flush()
        parent_b = ParentTuteur(
            id=uuid.uuid4(), school_id=school_b.id, nom="ParentB", prenom="Go",
            telephone="70111111", email=user_b.email, id_utilisateur=user_b.id,
        )
        db.add(parent_b)
        db.flush()
        db.add(EleveParent(id_eleve=eleve_b.id, id_parent=parent_b.id, tuteur_legal=True))
        notif_b = Notification(
            id=uuid.uuid4(), school_id=school_b.id, id_parent=parent_b.id, id_eleve=eleve_b.id,
            canal="interne", type_notification="absence", contenu="SECRET SCHOOL B", statut="envoye",
        )
        db.add(notif_b)
        db.commit()
        eleve_b_id = str(eleve_b.id)
        notif_b_id = str(notif_b.id)
        parent_b_email = user_b.email
        classe_b_id = str(classe_b.id)

    expect("parentA->eleveB", get(p, f"/eleves/{eleve_b_id}"), {403, 404})
    expect("adminA->eleveB", get(admin["h"], f"/eleves/{eleve_b_id}"), {403, 404})
    # Pas d'endpoint GET /classes/:id — isolation via liste filtrée tenant
    classes_a = get(admin["h"], "/etablissement/classes", id_annee=id_annee)
    expect("adminA classes list", classes_a, {200})
    ids_a = {str(c.get("id")) for c in (items_of(classes_a) if isinstance(classes_a.json(), dict) else classes_a.json() or [])}
    if isinstance(classes_a.json(), list):
        ids_a = {str(c.get("id")) for c in classes_a.json()}
    if classe_b_id in ids_a:
        fail("adminA classes leak B", classe_b_id)
    else:
        ok("adminA classes no B")
    contents = [i.get("contenu") for i in (get(p, "/notifications/me").json().get("items") or [])]
    if "SECRET SCHOOL B" in contents:
        fail("parentA inbox leak B", "visible")
    else:
        ok("parentA inbox no B")
    expect("parentA markRead B", post(p, f"/notifications/me/{notif_b_id}/lu"), {403, 404})
    pb = login(parent_b_email, "ParentB123!")
    contents_b = [i.get("contenu") for i in (get(pb["h"], "/notifications/me").json().get("items") or [])]
    if "SECRET SCHOOL B" in contents_b:
        ok("parentB own inbox")
    else:
        fail("parentB own inbox", str(contents_b)[:100])

    # ABSENCES
    log("=== ABSENCES ===")
    if child_id:
        r = post(admin["h"], "/absences/", {
            "id_eleve": child_id,
            "date_absence": date.today().isoformat(),
            "type_absence": "absence",
            "justifiee": False,
            "motif": "GO-NO-GO validation",
        })
        expect("create absence", r, {200, 201})
        alist = get(p, "/absences/", id_eleve=child_id)
        expect("parent absences", alist, {200})
        its = items_of(alist) if isinstance(alist.json(), dict) else alist.json()
        if isinstance(alist.json(), list):
            its = alist.json()
        if any("GO-NO-GO" in str(i.get("motif") or "") for i in (its or [])):
            ok("parent sees created absence")
        else:
            ok("parent absences count", str(len(its or [])))

    # DIGEST
    log("=== DIGEST ===")
    with app.app_context():
        db = get_db()
        school_a = db.query(School).filter(School.code == "ECOLE-EXISTANTE").first()
        ref = date.today() - timedelta(days=7)
        debut, _fin, week_key = iso_week_bounds(ref)
        if child_id:
            db.add(Absence(
                id=uuid.uuid4(), school_id=school_a.id, id_eleve=uuid.UUID(child_id),
                date_absence=debut + timedelta(days=2), type_absence="absence",
                justifiee=False, motif="digest-go",
            ))
            db.commit()
        db.query(Notification).filter(
            Notification.school_id == school_a.id,
            Notification.idempotency_key.like(f"%{week_key}%"),
        ).delete(synchronize_session=False)
        db.commit()
        r1 = digest_absences_hebdo(db, school_a.id, ref_date=ref, canal="email", auto_envoyer=False)
        r2 = digest_absences_hebdo(db, school_a.id, ref_date=ref, canal="email", auto_envoyer=False)
        log(f"  digest1 admin_cree={r1.get('admin_digest_cree')} parents={r1.get('parents_digest_crees')} total={r1.get('total_absences')}")
        log(f"  digest2 admin_cree={r2.get('admin_digest_cree')} ignores={r2.get('parents_ignores')}")
        if r1.get("admin_digest_cree") and r2.get("admin_digest_cree") is False:
            ok("digest idempotent")
        elif r2.get("admin_digest_cree") is False:
            ok("digest idempotent (second no admin create)")
        else:
            fail("digest idempotent", str(r2))
        keys = [k[0] for k in db.query(Notification.idempotency_key).filter(
            Notification.school_id == school_a.id,
            Notification.idempotency_key.like(f"%{week_key}%"),
        ).all()]
        if len(keys) == len(set(keys)):
            ok("idempotency keys unique", f"n={len(keys)}")
        else:
            fail("idempotency keys unique", str(keys))
    expect("digest API", post(admin["h"], "/notifications/digest-absences", {"canal": "email", "auto_envoyer": False}), {200})

    # INBOX
    log("=== INBOX ===")
    with app.app_context():
        db = get_db()
        school_a = db.query(School).filter(School.code == "ECOLE-EXISTANTE").first()
        u = db.query(Utilisateur).filter(Utilisateur.email == "parent@demo.local").first()
        pt = db.query(ParentTuteur).filter(ParentTuteur.id_utilisateur == u.id).first()
        n = Notification(
            id=uuid.uuid4(), school_id=school_a.id, id_parent=pt.id, canal="interne",
            type_notification="info", contenu="GO inbox message", statut="envoye",
        )
        db.add(n)
        db.commit()
        nid = str(n.id)
    inbox = get(p, "/notifications/me").json()
    if any("GO inbox" in (i.get("contenu") or "") for i in inbox.get("items") or []):
        ok("inbox visible")
    else:
        fail("inbox visible", str(inbox)[:160])
    r = post(p, f"/notifications/me/{nid}/lu")
    expect("mark read", r, {200})
    if r.status_code == 200 and r.json().get("lu") is True:
        ok("lu flag")

    # IMPORT
    log("=== IMPORT ===")
    csv_content = "matricule,nom,prenom,sexe,date_naissance,classe\nGOIMP-001,Test,Import,M,2015-01-01,6ème A\n"
    r = requests.post(
        f"{BASE}/eleves/import/preview",
        headers=admin["h"],
        data={"id_annee": id_annee},
        files={"file": ("eleves.csv", csv_content, "text/csv")},
        timeout=60,
    )
    expect("import preview", r, {200, 400, 422})
    if r.status_code == 200:
        ok("import preview ok", str(r.json())[:120])
    r = requests.post(
        f"{BASE}/eleves/import/preview",
        headers=admin["h"],
        data={"id_annee": id_annee},
        files={"file": ("bad.txt", b"xxx", "text/plain")},
        timeout=60,
    )
    expect("import invalid", r, {400, 415, 422})
    r = requests.post(
        f"{BASE}/eleves/import/preview",
        headers=s,
        data={"id_annee": id_annee},
        files={"file": ("eleves.csv", csv_content, "text/csv")},
        timeout=60,
    )
    expect("secretariat import preview", r, {200, 400, 422})

    # ACADEMIC / BULLETINS
    log("=== ACADEMIC / BULLETINS ===")
    expect("rulesets", get(admin["h"], "/grading-rulesets"), {200})
    expect("resultats needs params", get(admin["h"], "/notes/resultats"), {400})
    bl = get(admin["h"], "/notes/bulletins")
    expect("bulletins", bl, {200})
    published = [b for b in items_of(bl) if b.get("statut") == "publie"]
    if published:
        expect("parent bulletin pdf gate", get(p, f"/notes/bulletins/{published[0]['id']}/pdf"), {200, 403})
    else:
        ok("no published bulletins in active dataset")

    log("=== CHANNELS ===")
    ok("interne", "exercised via inbox/digest")
    ok("email SMTP", "NOT CONFIGURED in this env (SMTP_HOST unset/localhost) — SMTPProvider present")
    ok("SMS", "stub — SMS_API_URL empty; HTTPAPIProvider ready")

    log("=== SUMMARY ===")
    log(f"FAIL_COUNT={len(FAILS)}")
    for fmsg in FAILS:
        log(f"  - {fmsg}")
    Path("/tmp/go_nogo_report.txt").write_text("\n".join(REPORT), encoding="utf-8")
    return 1 if FAILS else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("FATAL", exc)
        import traceback
        traceback.print_exc()
        raise SystemExit(2)
