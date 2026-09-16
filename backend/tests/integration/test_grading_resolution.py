"""PR #12 Step 2 — résolution de rulesets (priorité, conflits, tenant, cohérence)."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.auth.jwt_handler import hash_password
from app.models import (
    AcademicPeriod,
    AnneeScolaire,
    Classe,
    Etablissement,
    EvaluationType,
    GradingRuleComponent,
    GradingRuleset,
    Matiere,
    NiveauEtude,
    Program,
    School,
    Utilisateur,
)
from app.services.academic import get_or_create_general_program
from app.services.evaluation_types import ensure_system_evaluation_types
from app.services.grading_rules import (
    SPEC_PROGRAM,
    SPEC_SUBJECT,
    GradingContextError,
    GradingRulesConflictError,
    GradingRulesInvalidError,
    GradingRulesNotFoundError,
    ResolutionContext,
    resolve_grading_rules,
)


@pytest.fixture
def resolve_pair(db: Session):
    """Deux écoles avec année unique (évite pollution inter-tests via commits)."""
    out = {}
    year_tag = uuid.uuid4().hex[:8]
    year_label = f"Y-{year_tag}"
    for code_prefix, name in (("RA", "Resolve Alpha"), ("RB", "Resolve Beta")):
        code = f"{code_prefix}-{year_tag}"
        school = School(
            id=uuid.uuid4(),
            name=f"{name} {year_tag}",
            code=code,
            city="Ouagadougou",
            country="Burkina Faso",
            is_active=True,
        )
        db.add(school)
        db.flush()
        ensure_system_evaluation_types(db, school.id)
        general = get_or_create_general_program(db, school.id)
        tech = Program(
            id=uuid.uuid4(),
            school_id=school.id,
            code=f"TECH-{year_tag[:6]}",
            name="LDC Technique",
            program_type="technique",
            period_type_default="semestre",
            is_active=True,
        )
        db.add(tech)
        db.flush()
        db.add(
            Etablissement(
                id=uuid.uuid4(),
                school_id=school.id,
                nom=school.name,
                sigle=code_prefix,
                format_matricule="{ANNEE}M-{SEQ}",
            )
        )
        db.flush()
        annee = AnneeScolaire(
            id=uuid.uuid4(),
            school_id=school.id,
            libelle=year_label,
            date_debut=date(2026, 9, 1),
            date_fin=date(2027, 6, 30),
            est_active=True,
        )
        db.add(annee)
        db.flush()

        school_id = school.id
        annee_id = annee.id

        def _niveau(program, label, ordre, *, _sid=school_id):
            n = NiveauEtude(
                id=uuid.uuid4(),
                school_id=_sid,
                id_program=program.id,
                libelle=label,
                ordre=ordre,
                cycle="premier",
            )
            db.add(n)
            db.flush()
            return n

        niv_g = _niveau(general, "2nde", 2)
        niv_t = _niveau(tech, "2nde", 2)

        def _classe(program, niveau, label, *, _sid=school_id, _aid=annee_id):
            c = Classe(
                id=uuid.uuid4(),
                school_id=_sid,
                id_niveau=niveau.id,
                id_annee=_aid,
                id_program=program.id,
                libelle=label,
            )
            db.add(c)
            db.flush()
            return c

        cl_ga = _classe(general, niv_g, "2nde A")
        cl_gb = _classe(general, niv_g, "2nde B")

        def _matiere(mcode, libelle, *, _sid=school_id):
            m = Matiere(
                id=uuid.uuid4(),
                school_id=_sid,
                code=mcode,
                libelle=libelle,
            )
            db.add(m)
            db.flush()
            return m

        math = _matiere("MATH", "Mathématiques")
        fr = _matiere("FR", "Français")

        def _period(program, seq, pcode, label, *, _sid=school_id, _aid=annee_id):
            p = AcademicPeriod(
                id=uuid.uuid4(),
                school_id=_sid,
                id_annee=_aid,
                id_program=program.id,
                sequence=seq,
                code=pcode,
                label=label,
                period_type="trimestre",
                date_debut=date(2026, 9, 1),
                date_fin=date(2026, 12, 20),
                is_active=True,
            )
            db.add(p)
            db.flush()
            return p

        period_g = _period(general, 1, "T1", "Trimestre 1")
        period_t = _period(tech, 1, "S1", "Semestre 1")

        email = f"admin-{code.lower()}@resolve.test"
        user = Utilisateur(
            id=uuid.uuid4(),
            nom="Admin",
            prenom=code_prefix,
            email=email,
            mot_de_passe_hash=hash_password("Admin123!"),
            role="administrateur",
            actif=True,
            doit_changer_mdp=False,
            school_id=school.id,
        )
        db.add(user)

        key = "a" if code_prefix == "RA" else "b"
        out[key] = {
            "school": school,
            "annee": annee,
            "general": general,
            "tech": tech,
            "niveau_g": niv_g,
            "niveau_t": niv_t,
            "classe_a": cl_ga,
            "classe_b": cl_gb,
            "math": math,
            "fr": fr,
            "period_g": period_g,
            "period_t": period_t,
            "user": user,
        }
    db.commit()
    return out


def _etype(db, school_id, code="devoir") -> EvaluationType:
    return (
        db.query(EvaluationType)
        .filter(EvaluationType.school_id == school_id, EvaluationType.code == code)
        .one()
    )


def _ruleset(
    db,
    ctx_school,
    *,
    code,
    version=1,
    status="active",
    id_program=None,
    id_niveau=None,
    id_matiere=None,
    weights: list[tuple[str, str, str]] | None = None,
) -> GradingRuleset:
    """weights: list of (comp_code, eval_type_code, weight_str). Default 60/40."""
    rs = GradingRuleset(
        id=uuid.uuid4(),
        school_id=ctx_school["school"].id,
        code=code,
        name=code,
        status=status,
        version=version,
        id_annee=ctx_school["annee"].id,
        id_program=id_program,
        id_niveau=id_niveau,
        id_matiere=id_matiere,
        scale_max=Decimal("20.00"),
        rounding_mode="half_up",
        rounding_precision=2,
        created_by=ctx_school["user"].id,
    )
    db.add(rs)
    db.flush()
    if weights is None:
        weights = [("DEV", "devoir", "60.00"), ("COMP", "composition", "40.00")]
    for i, (ccode, et_code, w) in enumerate(weights, start=1):
        et = _etype(db, ctx_school["school"].id, et_code)
        db.add(
            GradingRuleComponent(
                id=uuid.uuid4(),
                school_id=ctx_school["school"].id,
                ruleset_id=rs.id,
                code=ccode,
                label=ccode,
                id_evaluation_type=et.id,
                weight=Decimal(w),
                sequence=i,
                is_required=True,
            )
        )
    db.flush()
    return rs


def _ctx(s, *, program=None, level=None, classe=None, subject=None, period=None) -> ResolutionContext:
    return ResolutionContext(
        school_id=s["school"].id,
        academic_year_id=s["annee"].id,
        program_id=(program or s["general"]).id,
        level_id=level.id if level else None,
        class_id=classe.id if classe else None,
        subject_id=subject.id if subject else None,
        academic_period_id=period.id if period else None,
    )


# ---------------------------------------------------------------------------
# Happy path / priority
# ---------------------------------------------------------------------------


class TestResolutionPriority:
    def test_no_ruleset(self, db, resolve_pair):
        a = resolve_pair["a"]
        with pytest.raises(GradingRulesNotFoundError) as exc:
            resolve_grading_rules(db, _ctx(a, subject=a["math"]))
        assert exc.value.code == "NO_RULESET"

    def test_school_default(self, db, resolve_pair):
        a = resolve_pair["a"]
        rs = _ruleset(db, a, code=f"SCH-{uuid.uuid4().hex[:6]}")
        db.commit()
        result = resolve_grading_rules(db, _ctx(a, subject=a["math"]))
        assert result.ruleset_id == rs.id
        assert result.specificity == 0
        assert result.scope_level == "school"
        assert len(result.components) == 2
        assert result.trace.selected is not None

    def test_program_overrides_school(self, db, resolve_pair):
        a = resolve_pair["a"]
        _ruleset(db, a, code=f"SCH-{uuid.uuid4().hex[:6]}")
        prog = _ruleset(
            db,
            a,
            code=f"PRG-{uuid.uuid4().hex[:6]}",
            id_program=a["general"].id,
            weights=[("DEV", "devoir", "70.00"), ("COMP", "composition", "30.00")],
        )
        db.commit()
        result = resolve_grading_rules(db, _ctx(a, subject=a["math"]))
        assert result.ruleset_id == prog.id
        assert result.specificity == SPEC_PROGRAM
        assert result.components[0].weight == Decimal("70.00")

    def test_level_overrides_program(self, db, resolve_pair):
        a = resolve_pair["a"]
        _ruleset(db, a, code=f"PRG-{uuid.uuid4().hex[:6]}", id_program=a["general"].id)
        lvl = _ruleset(
            db,
            a,
            code=f"LVL-{uuid.uuid4().hex[:6]}",
            id_program=a["general"].id,
            id_niveau=a["niveau_g"].id,
            weights=[("DEV", "devoir", "55.00"), ("COMP", "composition", "45.00")],
        )
        db.commit()
        result = resolve_grading_rules(
            db, _ctx(a, level=a["niveau_g"], classe=a["classe_a"], subject=a["math"])
        )
        assert result.ruleset_id == lvl.id
        assert result.scope_level == "program+level"

    def test_subject_overrides_program(self, db, resolve_pair):
        a = resolve_pair["a"]
        _ruleset(
            db,
            a,
            code=f"PRG-{uuid.uuid4().hex[:6]}",
            id_program=a["general"].id,
            weights=[("DEV", "devoir", "50.00"), ("COMP", "composition", "50.00")],
        )
        subj = _ruleset(
            db,
            a,
            code=f"MATH-{uuid.uuid4().hex[:6]}",
            id_program=a["general"].id,
            id_matiere=a["math"].id,
            weights=[("DEV", "devoir", "60.00"), ("COMP", "composition", "40.00")],
        )
        db.commit()
        math_r = resolve_grading_rules(db, _ctx(a, subject=a["math"]))
        assert math_r.ruleset_id == subj.id
        assert math_r.components[0].weight == Decimal("60.00")
        fr_r = resolve_grading_rules(db, _ctx(a, subject=a["fr"]))
        assert fr_r.specificity == SPEC_PROGRAM
        assert fr_r.components[0].weight == Decimal("50.00")

    def test_program_level_subject_highest(self, db, resolve_pair):
        a = resolve_pair["a"]
        _ruleset(db, a, code=f"SCH-{uuid.uuid4().hex[:6]}")
        _ruleset(db, a, code=f"PRG-{uuid.uuid4().hex[:6]}", id_program=a["general"].id)
        _ruleset(
            db,
            a,
            code=f"SUB-{uuid.uuid4().hex[:6]}",
            id_program=a["general"].id,
            id_matiere=a["math"].id,
        )
        top = _ruleset(
            db,
            a,
            code=f"PLS-{uuid.uuid4().hex[:6]}",
            id_program=a["general"].id,
            id_niveau=a["niveau_g"].id,
            id_matiere=a["math"].id,
            weights=[("DEV", "devoir", "65.00"), ("COMP", "composition", "35.00")],
        )
        db.commit()
        result = resolve_grading_rules(
            db, _ctx(a, level=a["niveau_g"], classe=a["classe_a"], subject=a["math"])
        )
        assert result.ruleset_id == top.id
        assert result.scope_level == "program+level+subject"
        assert len(result.trace.candidates) >= 4

    def test_tech_program_not_general(self, db, resolve_pair):
        a = resolve_pair["a"]
        _ruleset(
            db,
            a,
            code=f"GEN-{uuid.uuid4().hex[:6]}",
            id_program=a["general"].id,
            weights=[("DEV", "devoir", "60.00"), ("COMP", "composition", "40.00")],
        )
        tech_rs = _ruleset(
            db,
            a,
            code=f"TECH-{uuid.uuid4().hex[:6]}",
            id_program=a["tech"].id,
            weights=[
                ("DEV", "devoir", "30.00"),
                ("TP", "tp", "20.00"),
                ("COMP", "composition", "50.00"),
            ],
        )
        db.commit()
        result = resolve_grading_rules(
            db, _ctx(a, program=a["tech"], level=a["niveau_t"], subject=a["math"])
        )
        assert result.ruleset_id == tech_rs.id
        assert len(result.components) == 3

    def test_same_label_levels_isolated_by_program(self, db, resolve_pair):
        a = resolve_pair["a"]
        g = _ruleset(
            db,
            a,
            code=f"G2-{uuid.uuid4().hex[:6]}",
            id_program=a["general"].id,
            id_niveau=a["niveau_g"].id,
        )
        t = _ruleset(
            db,
            a,
            code=f"T2-{uuid.uuid4().hex[:6]}",
            id_program=a["tech"].id,
            id_niveau=a["niveau_t"].id,
        )
        db.commit()
        rg = resolve_grading_rules(db, _ctx(a, level=a["niveau_g"], subject=a["math"]))
        rt = resolve_grading_rules(
            db, _ctx(a, program=a["tech"], level=a["niveau_t"], subject=a["math"])
        )
        assert rg.ruleset_id == g.id
        assert rt.ruleset_id == t.id
        assert a["niveau_g"].libelle == a["niveau_t"].libelle


# ---------------------------------------------------------------------------
# Status / versioning / conflicts
# ---------------------------------------------------------------------------


class TestResolutionConflictsAndStatus:
    def test_draft_ignored_active_wins(self, db, resolve_pair):
        a = resolve_pair["a"]
        active = _ruleset(db, a, code=f"ACT-{uuid.uuid4().hex[:6]}", status="active", version=1)
        _ruleset(
            db,
            a,
            code=active.code,
            status="draft",
            version=2,
            weights=[("DEV", "devoir", "100.00")],
        )
        db.commit()
        result = resolve_grading_rules(db, _ctx(a, subject=a["math"]))
        assert result.ruleset_id == active.id
        assert result.ruleset_version == 1

    def test_archived_ignored_active_wins(self, db, resolve_pair):
        a = resolve_pair["a"]
        code = f"ARC-{uuid.uuid4().hex[:6]}"
        _ruleset(db, a, code=code, status="archived", version=1)
        active = _ruleset(db, a, code=code, status="active", version=2)
        db.commit()
        result = resolve_grading_rules(db, _ctx(a, subject=a["math"]))
        assert result.ruleset_id == active.id
        assert result.ruleset_version == 2

    def test_two_active_same_scope_conflict(self, db, resolve_pair):
        a = resolve_pair["a"]
        _ruleset(db, a, code=f"C1-{uuid.uuid4().hex[:6]}", id_program=a["general"].id)
        _ruleset(db, a, code=f"C2-{uuid.uuid4().hex[:6]}", id_program=a["general"].id)
        db.commit()
        with pytest.raises(GradingRulesConflictError) as exc:
            resolve_grading_rules(db, _ctx(a, subject=a["math"]))
        assert exc.value.code == "RULESET_CONFLICT"
        assert len(exc.value.details["conflicting_ruleset_ids"]) == 2

    def test_active_v1_and_v2_same_scope_conflict(self, db, resolve_pair):
        """Version ≠ priorité : deux ACTIVE même scope → conflit."""
        a = resolve_pair["a"]
        code = f"VV-{uuid.uuid4().hex[:6]}"
        _ruleset(db, a, code=code, version=1, status="active", id_program=a["general"].id)
        _ruleset(db, a, code=code, version=2, status="active", id_program=a["general"].id)
        db.commit()
        with pytest.raises(GradingRulesConflictError):
            resolve_grading_rules(db, _ctx(a, subject=a["math"]))

    def test_draft_and_archived_only_no_ruleset(self, db, resolve_pair):
        a = resolve_pair["a"]
        code = f"DA-{uuid.uuid4().hex[:6]}"
        _ruleset(db, a, code=code, version=1, status="draft")
        _ruleset(db, a, code=code, version=2, status="archived")
        db.commit()
        with pytest.raises(GradingRulesNotFoundError):
            resolve_grading_rules(db, _ctx(a, subject=a["math"]))

    def test_different_specificity_no_conflict(self, db, resolve_pair):
        a = resolve_pair["a"]
        _ruleset(db, a, code=f"LO-{uuid.uuid4().hex[:6]}")
        hi = _ruleset(
            db,
            a,
            code=f"HI-{uuid.uuid4().hex[:6]}",
            id_program=a["general"].id,
            id_matiere=a["math"].id,
        )
        db.commit()
        result = resolve_grading_rules(db, _ctx(a, subject=a["math"]))
        assert result.ruleset_id == hi.id
        assert result.specificity == SPEC_PROGRAM + SPEC_SUBJECT

    def test_invalid_weight_sum_rejected(self, db, resolve_pair):
        a = resolve_pair["a"]
        rs = _ruleset(
            db,
            a,
            code=f"BAD-{uuid.uuid4().hex[:6]}",
            weights=[("DEV", "devoir", "60.00"), ("COMP", "composition", "30.00")],
        )
        db.commit()
        with pytest.raises(GradingRulesInvalidError):
            resolve_grading_rules(db, _ctx(a, subject=a["math"]))
        assert rs.id is not None


# ---------------------------------------------------------------------------
# Tenant + academic coherence
# ---------------------------------------------------------------------------


class TestResolutionTenantAndCoherence:
    def test_school_a_never_gets_school_b_ruleset(self, db, resolve_pair):
        a, b = resolve_pair["a"], resolve_pair["b"]
        rs_a = _ruleset(db, a, code=f"AA-{uuid.uuid4().hex[:6]}")
        _ruleset(
            db,
            b,
            code=f"BB-{uuid.uuid4().hex[:6]}",
            weights=[("DEV", "devoir", "100.00")],
        )
        db.commit()
        result = resolve_grading_rules(db, _ctx(a, subject=a["math"]))
        assert result.ruleset_id == rs_a.id
        assert result.school_id == a["school"].id

    def test_inject_program_b_into_school_a_rejected(self, db, resolve_pair):
        a, b = resolve_pair["a"], resolve_pair["b"]
        with pytest.raises(GradingContextError) as exc:
            resolve_grading_rules(
                db,
                ResolutionContext(
                    school_id=a["school"].id,
                    academic_year_id=a["annee"].id,
                    program_id=b["general"].id,
                    subject_id=a["math"].id,
                ),
            )
        assert exc.value.code == "TENANT_CONTEXT_ERROR"

    def test_homonymous_programs_stay_tenant_local(self, db, resolve_pair):
        a, b = resolve_pair["a"], resolve_pair["b"]
        assert a["general"].name == b["general"].name or True  # both GENERAL
        ra = _ruleset(db, a, code=f"HA-{uuid.uuid4().hex[:6]}", id_program=a["general"].id)
        rb = _ruleset(
            db,
            b,
            code=f"HB-{uuid.uuid4().hex[:6]}",
            id_program=b["general"].id,
            weights=[("DEV", "devoir", "100.00")],
        )
        db.commit()
        out_a = resolve_grading_rules(db, _ctx(a, subject=a["math"]))
        out_b = resolve_grading_rules(db, _ctx(b, subject=b["math"]))
        assert out_a.ruleset_id == ra.id
        assert out_b.ruleset_id == rb.id

    def test_program_a_level_b_invalid(self, db, resolve_pair):
        a, b = resolve_pair["a"], resolve_pair["b"]
        with pytest.raises(GradingContextError):
            resolve_grading_rules(
                db,
                ResolutionContext(
                    school_id=a["school"].id,
                    academic_year_id=a["annee"].id,
                    program_id=a["general"].id,
                    level_id=b["niveau_g"].id,
                    subject_id=a["math"].id,
                ),
            )

    def test_level_a_class_b_invalid(self, db, resolve_pair):
        a, b = resolve_pair["a"], resolve_pair["b"]
        with pytest.raises(GradingContextError):
            resolve_grading_rules(
                db,
                ResolutionContext(
                    school_id=a["school"].id,
                    academic_year_id=a["annee"].id,
                    program_id=a["general"].id,
                    level_id=a["niveau_g"].id,
                    class_id=b["classe_a"].id,
                    subject_id=a["math"].id,
                ),
            )

    def test_program_a_period_b_invalid(self, db, resolve_pair):
        a, b = resolve_pair["a"], resolve_pair["b"]
        with pytest.raises(GradingContextError):
            resolve_grading_rules(
                db,
                ResolutionContext(
                    school_id=a["school"].id,
                    academic_year_id=a["annee"].id,
                    program_id=a["general"].id,
                    subject_id=a["math"].id,
                    academic_period_id=b["period_g"].id,
                ),
            )

    def test_class_subject_other_school_invalid(self, db, resolve_pair):
        a, b = resolve_pair["a"], resolve_pair["b"]
        with pytest.raises(GradingContextError):
            resolve_grading_rules(
                db,
                ResolutionContext(
                    school_id=a["school"].id,
                    academic_year_id=a["annee"].id,
                    program_id=a["general"].id,
                    class_id=a["classe_a"].id,
                    level_id=a["niveau_g"].id,
                    subject_id=b["math"].id,
                ),
            )

    def test_level_wrong_program_same_school(self, db, resolve_pair):
        a = resolve_pair["a"]
        with pytest.raises(GradingContextError) as exc:
            resolve_grading_rules(
                db,
                ResolutionContext(
                    school_id=a["school"].id,
                    academic_year_id=a["annee"].id,
                    program_id=a["general"].id,
                    level_id=a["niveau_t"].id,  # tech level with general program
                    subject_id=a["math"].id,
                ),
            )
        assert "incohérent" in exc.value.message.lower() or "ACADEMIC" in str(
            exc.value.details.get("code", "")
        )

    def test_period_wrong_program_same_school(self, db, resolve_pair):
        a = resolve_pair["a"]
        with pytest.raises(GradingContextError):
            resolve_grading_rules(
                db,
                ResolutionContext(
                    school_id=a["school"].id,
                    academic_year_id=a["annee"].id,
                    program_id=a["general"].id,
                    subject_id=a["math"].id,
                    academic_period_id=a["period_t"].id,  # tech period
                ),
            )

    def test_resolution_is_read_only(self, db, resolve_pair):
        a = resolve_pair["a"]
        rs = _ruleset(db, a, code=f"RO-{uuid.uuid4().hex[:6]}")
        db.commit()
        before = db.query(GradingRuleset).filter(GradingRuleset.id == rs.id).one()
        status_before = before.status
        resolve_grading_rules(db, _ctx(a, subject=a["math"]))
        after = db.query(GradingRuleset).filter(GradingRuleset.id == rs.id).one()
        assert after.status == status_before
        assert after.version == rs.version
