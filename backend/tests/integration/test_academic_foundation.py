"""PR #11 step 1 — fondation académique : invariants, contraintes DB, isolation tenant."""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.auth.jwt_handler import hash_password
from app.models import (
    PROGRAM_CODE_GENERAL,
    AcademicPeriod,
    AnneeScolaire,
    Classe,
    Etablissement,
    NiveauEtude,
    Program,
    School,
    Utilisateur,
)
from app.services.academic import build_legacy_period, get_or_create_general_program


@pytest.fixture
def academic_school_pair(db):
    """Deux écoles avec Program GENERAL + année/niveau/classe."""
    schools = {}
    for code, name, city in (
        ("ACAD-A", "École Acad Alpha", "Ouagadougou"),
        ("ACAD-B", "École Acad Beta", "Bobo-Dioulasso"),
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
        etab = db.query(Etablissement).filter(Etablissement.school_id == school.id).first()
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
        key = "a" if code.endswith("A") else "b"
        schools[key] = {
            "school": school,
            "program": program,
            "annee": annee,
            "niveau": niveau,
            "classe": classe,
            "email": email,
            "user": user,
        }
    db.commit()
    return schools


def _counts(db):
    from app.models import Bulletin, Evaluation, Inscription, Note

    return {
        "schools_count": db.query(School).count(),
        "academic_years_count": db.query(AnneeScolaire).count(),
        "trimesters_count": db.query(AcademicPeriod).count(),
        "evaluations_count": db.query(Evaluation).count(),
        "notes_count": db.query(Note).count(),
        "bulletins_count": db.query(Bulletin).count(),
        "inscriptions_count": db.query(Inscription).count(),
    }


class TestAcademicFoundationStructure:
    def test_general_program_backfill_per_school(self, db, default_school):
        program = get_or_create_general_program(db, default_school.id)
        db.commit()
        assert program.code == PROGRAM_CODE_GENERAL
        assert program.name == "Général"
        again = get_or_create_general_program(db, default_school.id)
        assert again.id == program.id

    def test_academic_period_table_and_uuid_stability(self, db, annee_classe):
        period = annee_classe["trimestre"]
        assert period.id is not None
        reloaded = db.query(AcademicPeriod).filter(AcademicPeriod.id == period.id).one()
        assert reloaded.sequence == 1
        assert reloaded.numero == 1  # synonym legacy
        assert reloaded.code == "T1"
        assert reloaded.period_type == "trimestre"
        assert reloaded.id_program == annee_classe["program"].id
        assert reloaded.school_id == annee_classe["annee"].school_id

    def test_invariants_counts_stable_within_session(self, db, annee_classe):
        before = _counts(db)
        after = _counts(db)
        assert before == after
        assert after["trimesters_count"] >= 1

    def test_homonymous_levels_two_programs(self, db, default_school):
        general = get_or_create_general_program(db, default_school.id)
        tech = Program(
            id=uuid.uuid4(),
            school_id=default_school.id,
            code=f"LDC-TECH-{uuid.uuid4().hex[:6]}",
            name="LDC Technique",
            program_type="technique",
            period_type_default="semestre",
            is_active=True,
        )
        db.add(tech)
        db.flush()
        n1 = NiveauEtude(
            id=uuid.uuid4(),
            school_id=default_school.id,
            id_program=general.id,
            libelle="Première",
            ordre=6,
            cycle="second",
        )
        n2 = NiveauEtude(
            id=uuid.uuid4(),
            school_id=default_school.id,
            id_program=tech.id,
            libelle="Première",
            ordre=6,
            cycle="second",
        )
        db.add_all([n1, n2])
        db.commit()
        assert n1.id != n2.id

    def test_more_than_three_periods_allowed(self, db, annee_classe, default_school):
        program = annee_classe["program"]
        annee = annee_classe["annee"]
        for seq in (4, 5):
            db.add(
                build_legacy_period(
                    id_annee=annee.id,
                    school_id=default_school.id,
                    id_program=program.id,
                    sequence=seq,
                    date_debut=date(2026, 5, 1),
                    date_fin=date(2026, 5, 15),
                    period_type="custom",
                )
            )
        db.commit()
        assert (
            db.query(AcademicPeriod)
            .filter(AcademicPeriod.id_annee == annee.id, AcademicPeriod.sequence >= 4)
            .count()
            >= 2
        )

    def test_semestre_and_custom_period_types(self, db, annee_classe, default_school):
        tech = Program(
            id=uuid.uuid4(),
            school_id=default_school.id,
            code=f"TECH-{uuid.uuid4().hex[:6]}",
            name="Technique Test",
            program_type="technique",
            period_type_default="semestre",
            is_active=True,
        )
        db.add(tech)
        db.flush()
        annee = annee_classe["annee"]
        s1 = build_legacy_period(
            id_annee=annee.id,
            school_id=default_school.id,
            id_program=tech.id,
            sequence=1,
            date_debut=date(2025, 9, 1),
            date_fin=date(2026, 1, 31),
            period_type="semestre",
        )
        c1 = build_legacy_period(
            id_annee=annee.id,
            school_id=default_school.id,
            id_program=tech.id,
            sequence=2,
            date_debut=date(2026, 2, 1),
            date_fin=date(2026, 6, 30),
            period_type="custom",
        )
        db.add_all([s1, c1])
        db.commit()
        assert s1.code == "S1"
        assert c1.code == "P2"


class TestAcademicFoundationDbConstraints:
    def test_reject_period_year_cross_school(self, db, academic_school_pair):
        """Cas 1 : Period.school_id=A + Year B impossible."""
        a, b = academic_school_pair["a"], academic_school_pair["b"]
        with pytest.raises(IntegrityError):
            db.add(
                AcademicPeriod(
                    id=uuid.uuid4(),
                    school_id=a["school"].id,
                    id_annee=b["annee"].id,
                    id_program=a["program"].id,
                    sequence=9,
                    code="X9",
                    label="Bad",
                    period_type="trimestre",
                    date_debut=date(2025, 9, 1),
                    date_fin=date(2025, 10, 1),
                )
            )
            db.flush()
        db.rollback()

    def test_reject_period_program_cross_school(self, db, academic_school_pair):
        """Cas 2 : Period.school_id=A + Program B impossible."""
        a, b = academic_school_pair["a"], academic_school_pair["b"]
        with pytest.raises(IntegrityError):
            db.add(
                AcademicPeriod(
                    id=uuid.uuid4(),
                    school_id=a["school"].id,
                    id_annee=a["annee"].id,
                    id_program=b["program"].id,
                    sequence=9,
                    code="X9",
                    label="Bad",
                    period_type="trimestre",
                    date_debut=date(2025, 9, 1),
                    date_fin=date(2025, 10, 1),
                )
            )
            db.flush()
        db.rollback()

    def test_reject_level_program_cross_school(self, db, academic_school_pair):
        """Cas 3 : Level.school_id=A + Program B impossible."""
        a, b = academic_school_pair["a"], academic_school_pair["b"]
        with pytest.raises(IntegrityError):
            db.add(
                NiveauEtude(
                    id=uuid.uuid4(),
                    school_id=a["school"].id,
                    id_program=b["program"].id,
                    libelle=f"Bad-{uuid.uuid4().hex[:6]}",
                    cycle="premier",
                )
            )
            db.flush()
        db.rollback()

    def test_reject_class_niveau_program_mismatch(self, db, academic_school_pair):
        """Cas 4 : Class.id_niveau=Level B + Class.id_program=Program A impossible."""
        a, b = academic_school_pair["a"], academic_school_pair["b"]
        with pytest.raises(IntegrityError):
            db.add(
                Classe(
                    id=uuid.uuid4(),
                    school_id=a["school"].id,
                    id_niveau=b["niveau"].id,
                    id_annee=a["annee"].id,
                    id_program=a["program"].id,
                    libelle=f"Mismatch-{uuid.uuid4().hex[:6]}",
                )
            )
            db.flush()
        db.rollback()

    def test_reject_sequence_zero(self, db, annee_classe, default_school):
        with pytest.raises(IntegrityError):
            db.add(
                AcademicPeriod(
                    id=uuid.uuid4(),
                    school_id=default_school.id,
                    id_annee=annee_classe["annee"].id,
                    id_program=annee_classe["program"].id,
                    sequence=0,
                    code="T0",
                    label="Bad",
                    period_type="trimestre",
                    date_debut=date(2025, 9, 1),
                    date_fin=date(2025, 10, 1),
                )
            )
            db.flush()
        db.rollback()


class TestAcademicFoundationTenantApiIsolation:
    def _auth(self, client, email: str) -> dict:
        resp = client.post("/api/login", json={"email": email, "password": "Admin123!"})
        assert resp.status_code == 200
        return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}

    def test_school_a_cannot_list_or_read_b_periods(self, client, db, academic_school_pair):
        a, b = academic_school_pair["a"], academic_school_pair["b"]
        period_b = build_legacy_period(
            id_annee=b["annee"].id,
            school_id=b["school"].id,
            id_program=b["program"].id,
            sequence=1,
            date_debut=date(2025, 9, 1),
            date_fin=date(2025, 12, 20),
        )
        db.add(period_b)
        db.commit()

        ha = self._auth(client, a["email"])
        listed = client.get(
            f"/api/etablissement/trimestres?id_annee={a['annee'].id}",
            headers=ha,
        )
        assert listed.status_code == 200
        ids = {row["id"] for row in listed.get_json()}
        assert str(period_b.id) not in ids

        detail = client.put(
            f"/api/etablissement/trimestres/{period_b.id}",
            headers=ha,
            json={
                "id_annee": str(a["annee"].id),
                "numero": 1,
                "date_debut": "2025-09-01",
                "date_fin": "2025-12-20",
            },
        )
        assert detail.status_code == 404

    def test_school_a_cannot_use_level_or_class_b(self, client, academic_school_pair):
        a, b = academic_school_pair["a"], academic_school_pair["b"]
        ha = self._auth(client, a["email"])

        create_classe = client.post(
            "/api/etablissement/classes",
            headers=ha,
            json={
                "id_niveau": str(b["niveau"].id),
                "id_annee": str(a["annee"].id),
                "libelle": f"Hack-{uuid.uuid4().hex[:6]}",
            },
        )
        assert create_classe.status_code in (403, 404)

        get_classes = client.get(
            f"/api/etablissement/classes?id_annee={a['annee'].id}",
            headers=ha,
        )
        assert get_classes.status_code == 200
        payload = get_classes.get_json()
        items = payload if isinstance(payload, list) else payload.get("items", payload)
        ids = {c["id"] for c in items}
        assert str(b["classe"].id) not in ids
