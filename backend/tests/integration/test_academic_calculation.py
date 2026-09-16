"""PR #12 Step 4 — intégration Calculation Engine + tenant isolation."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from flask_jwt_extended import create_access_token

from app.auth.jwt_handler import hash_password
from app.models import (
    AnneeScolaire,
    Classe,
    CoefficientMatiere,
    Etablissement,
    Evaluation,
    EvaluationType,
    GradingRuleComponent,
    GradingRuleset,
    Inscription,
    Matiere,
    NiveauEtude,
    Note,
    School,
    Utilisateur,
)
from app.models.emploi_temps import Enseignant
from app.services.academic import build_legacy_period, get_or_create_general_program
from app.services.academic_calculation_service import (
    RulesResolutionCache,
    calculate_student_subject,
    load_grades_for_student_subject_period,
)
from app.services.evaluation_types import ensure_system_evaluation_types
from app.services.grading_rules import GradingContextError, ResolutionContext, resolve_grading_rules


@pytest.fixture
def calc_pair(db, app):
    """Deux écoles avec classe, période, matière, ruleset 60/40 ACTIVE, notes."""
    out = {}
    suffix = uuid.uuid4().hex[:8]
    for key, code, name in (
        ("a", f"CALC-A-{suffix}", f"École Calc A {suffix}"),
        ("b", f"CALC-B-{suffix}", f"École Calc B {suffix}"),
    ):
        school = School(id=uuid.uuid4(), name=name, code=code, is_active=True)
        db.add(school)
        db.flush()
        ensure_system_evaluation_types(db, school.id)
        program = get_or_create_general_program(db, school.id)
        db.add(
            Etablissement(
                id=uuid.uuid4(),
                school_id=school.id,
                nom=name,
                format_matricule="{ANNEE}M-{SEQ}",
            )
        )
        annee = AnneeScolaire(
            id=uuid.uuid4(),
            school_id=school.id,
            libelle=f"2025-2026-{suffix}-{key}",
            date_debut=date(2025, 9, 1),
            date_fin=date(2026, 6, 30),
            est_active=True,
        )
        db.add(annee)
        db.flush()
        niveau = NiveauEtude(
            id=uuid.uuid4(),
            school_id=school.id,
            id_program=program.id,
            libelle="2nde",
            ordre=2,
            cycle="second",
        )
        db.add(niveau)
        db.flush()
        classe = Classe(
            id=uuid.uuid4(),
            school_id=school.id,
            id_niveau=niveau.id,
            id_annee=annee.id,
            id_program=program.id,
            libelle="2nde A",
        )
        db.add(classe)
        period = build_legacy_period(
            id_annee=annee.id,
            school_id=school.id,
            id_program=program.id,
            sequence=1,
            date_debut=date(2025, 9, 1),
            date_fin=date(2025, 12, 20),
            period_type="trimestre",
        )
        db.add(period)
        period_s = build_legacy_period(
            id_annee=annee.id,
            school_id=school.id,
            id_program=program.id,
            sequence=2,
            date_debut=date(2026, 1, 5),
            date_fin=date(2026, 6, 30),
            period_type="semestre",
            code="S1",
            label="Semestre 1",
        )
        db.add(period_s)
        math = Matiere(
            id=uuid.uuid4(), school_id=school.id, libelle="Mathématiques", code="MATH"
        )
        db.add(math)
        db.flush()
        db.add(
            CoefficientMatiere(
                id=uuid.uuid4(),
                id_matiere=math.id,
                id_niveau=niveau.id,
                coefficient=Decimal(5),
            )
        )
        email = f"admin-{code.lower()}@calc.test"
        user = Utilisateur(
            id=uuid.uuid4(),
            nom="Admin",
            prenom=key.upper(),
            email=email,
            mot_de_passe_hash=hash_password("Admin123!"),
            role="administrateur",
            actif=True,
            doit_changer_mdp=False,
            school_id=school.id,
        )
        db.add(user)
        ens = Enseignant(
            id=uuid.uuid4(),
            school_id=school.id,
            nom="Prof",
            prenom=key.upper(),
            email=f"ens-{code.lower()}@calc.test",
        )
        db.add(ens)
        db.flush()

        devoir = (
            db.query(EvaluationType)
            .filter(EvaluationType.school_id == school.id, EvaluationType.code == "devoir")
            .one()
        )
        composition = (
            db.query(EvaluationType)
            .filter(EvaluationType.school_id == school.id, EvaluationType.code == "composition")
            .one()
        )
        rs = GradingRuleset(
            id=uuid.uuid4(),
            school_id=school.id,
            code=f"LDC-{key.upper()}-{suffix}",
            name="60/40",
            status="active",
            version=1,
            id_annee=annee.id,
            id_program=program.id,
            id_matiere=math.id,
            scale_max=Decimal("20.00"),
            rounding_mode="half_up",
            rounding_precision=2,
            created_by=user.id,
        )
        db.add(rs)
        db.flush()
        db.add(
            GradingRuleComponent(
                id=uuid.uuid4(),
                school_id=school.id,
                ruleset_id=rs.id,
                code="DEV",
                label="Devoirs",
                id_evaluation_type=devoir.id,
                weight=Decimal("60.00"),
                sequence=1,
            )
        )
        db.add(
            GradingRuleComponent(
                id=uuid.uuid4(),
                school_id=school.id,
                ruleset_id=rs.id,
                code="COMP",
                label="Composition",
                id_evaluation_type=composition.id,
                weight=Decimal("40.00"),
                sequence=2,
            )
        )

        from app.models import Eleve

        eleve = Eleve(
            id=uuid.uuid4(),
            school_id=school.id,
            matricule=f"C{suffix}{key.upper()}",
            nom="Eleve",
            prenom=key.upper(),
            date_naissance=date(2010, 1, 1),
            sexe="M",
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
        ev_dev = Evaluation(
            id=uuid.uuid4(),
            school_id=school.id,
            id_classe=classe.id,
            id_matiere=math.id,
            id_trimestre=period.id,
            id_enseignant=ens.id,
            type_evaluation="devoir",
            coefficient=1,
            date_evaluation=date(2025, 10, 1),
            statut_publication="publie",
            statut_saisie="cloturee",
        )
        ev_comp = Evaluation(
            id=uuid.uuid4(),
            school_id=school.id,
            id_classe=classe.id,
            id_matiere=math.id,
            id_trimestre=period.id,
            id_enseignant=ens.id,
            type_evaluation="composition",
            coefficient=1,
            date_evaluation=date(2025, 11, 1),
            statut_publication="publie",
            statut_saisie="cloturee",
        )
        db.add_all([ev_dev, ev_comp])
        db.flush()
        db.add(
            Note(
                id=uuid.uuid4(),
                school_id=school.id,
                id_evaluation=ev_dev.id,
                id_eleve=eleve.id,
                valeur_note=Decimal("14.00"),
                absent=False,
            )
        )
        db.add(
            Note(
                id=uuid.uuid4(),
                school_id=school.id,
                id_evaluation=ev_comp.id,
                id_eleve=eleve.id,
                valeur_note=Decimal("10.00"),
                absent=False,
            )
        )

        out[key] = {
            "school": school,
            "program": program,
            "annee": annee,
            "niveau": niveau,
            "classe": classe,
            "period": period,
            "period_semestre": period_s,
            "math": math,
            "eleve": eleve,
            "user": user,
            "email": email,
            "ruleset": rs,
        }
    db.commit()
    return out


def _auth_ctx(app, user):
    """Push request context with JWT for tenant helpers."""
    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "email": user.email},
    )
    return app.test_request_context(headers={"Authorization": f"Bearer {token}"})


class TestCalculationIntegration:
    def test_60_40_via_service(self, app, db, calc_pair):
        a = calc_pair["a"]
        with _auth_ctx(app, a["user"]):
            from flask_jwt_extended import verify_jwt_in_request

            verify_jwt_in_request()
            result = calculate_student_subject(
                db,
                id_eleve=a["eleve"].id,
                classe=a["classe"],
                period=a["period"],
                subject_id=a["math"].id,
                cache=RulesResolutionCache(),
            )
        assert result.subject_average == Decimal("12.40")
        assert result.coefficient == Decimal("5.00")
        assert result.weighted_score == Decimal("62.00")
        assert result.ruleset_id == a["ruleset"].id
        assert result.ruleset_version == 1

    def test_semester_period_resolves(self, app, db, calc_pair):
        a = calc_pair["a"]
        with _auth_ctx(app, a["user"]):
            from flask_jwt_extended import verify_jwt_in_request

            verify_jwt_in_request()
            # No notes on semestre period → incomplete but ruleset resolves
            result = calculate_student_subject(
                db,
                id_eleve=a["eleve"].id,
                classe=a["classe"],
                period=a["period_semestre"],
                subject_id=a["math"].id,
            )
        assert result.incomplete
        assert result.ruleset_id == a["ruleset"].id

    def test_tenant_isolation_rejects_cross_school(self, app, db, calc_pair):
        a, b = calc_pair["a"], calc_pair["b"]
        with _auth_ctx(app, a["user"]):
            from flask_jwt_extended import verify_jwt_in_request

            verify_jwt_in_request()
            with pytest.raises(GradingContextError):
                calculate_student_subject(
                    db,
                    id_eleve=a["eleve"].id,
                    classe=a["classe"],
                    period=b["period"],  # période école B
                    subject_id=a["math"].id,
                )

    def test_school_a_never_gets_ruleset_b(self, app, db, calc_pair):
        a, b = calc_pair["a"], calc_pair["b"]
        with _auth_ctx(app, a["user"]):
            from flask_jwt_extended import verify_jwt_in_request

            verify_jwt_in_request()
            ctx = ResolutionContext(
                school_id=a["school"].id,
                academic_year_id=a["annee"].id,
                program_id=a["program"].id,
                level_id=a["niveau"].id,
                class_id=a["classe"].id,
                subject_id=a["math"].id,
                academic_period_id=a["period"].id,
            )
            rules = resolve_grading_rules(db, ctx)
            assert rules.ruleset_id == a["ruleset"].id
            assert rules.ruleset_id != b["ruleset"].id

    def test_cache_reuses_same_ruleset(self, app, db, calc_pair):
        a = calc_pair["a"]
        cache = RulesResolutionCache()
        with _auth_ctx(app, a["user"]):
            from flask_jwt_extended import verify_jwt_in_request

            verify_jwt_in_request()
            r1 = calculate_student_subject(
                db,
                id_eleve=a["eleve"].id,
                classe=a["classe"],
                period=a["period"],
                subject_id=a["math"].id,
                cache=cache,
            )
            r2 = calculate_student_subject(
                db,
                id_eleve=a["eleve"].id,
                classe=a["classe"],
                period=a["period"],
                subject_id=a["math"].id,
                cache=cache,
            )
        assert r1.ruleset_id == r2.ruleset_id
        assert len(cache._hits) == 1

    def test_load_grades_tenant_safe(self, app, db, calc_pair):
        a = calc_pair["a"]
        with _auth_ctx(app, a["user"]):
            from flask_jwt_extended import verify_jwt_in_request

            verify_jwt_in_request()
            grades = load_grades_for_student_subject_period(
                db,
                id_eleve=a["eleve"].id,
                id_classe=a["classe"].id,
                id_matiere=a["math"].id,
                id_period=a["period"].id,
            )
        assert len(grades) == 2
        types = {g.evaluation_type_code for g in grades}
        assert types == {"devoir", "composition"}
