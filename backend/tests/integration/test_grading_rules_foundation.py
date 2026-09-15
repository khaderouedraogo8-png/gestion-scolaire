"""PR #12 step 1 — fondation DB grading ruleset / composants / evaluation_type."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.auth.jwt_handler import hash_password
from app.models import (
    AnneeScolaire,
    Classe,
    CoefficientMatiere,
    Etablissement,
    EvaluationType,
    GradingRuleComponent,
    GradingRuleset,
    Matiere,
    NiveauEtude,
    School,
    Utilisateur,
)
from app.services.academic import get_or_create_general_program
from app.services.evaluation_types import ensure_system_evaluation_types


@pytest.fixture
def grading_school_pair(db):
    """Deux écoles avec année, program, niveau, classe, matière + catalogue types."""
    schools = {}
    for code, name, city in (
        ("GRD-A", "École Grading Alpha", "Ouagadougou"),
        ("GRD-B", "École Grading Beta", "Bobo-Dioulasso"),
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
        ensure_system_evaluation_types(db, school.id)
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
            "matiere": matiere,
            "email": email,
            "user": user,
        }
    db.commit()
    return schools


def _eval_type(db, school_id: uuid.UUID, code: str) -> EvaluationType:
    return (
        db.query(EvaluationType)
        .filter(EvaluationType.school_id == school_id, EvaluationType.code == code)
        .one()
    )


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _make_ruleset(db, ctx, *, code=None, version=1, status="draft", **kwargs) -> GradingRuleset:
    """``code`` unique par défaut pour éviter les collisions entre tests (fixture commit)."""
    if code is None:
        code = f"RS-{_uid()}"
    rs = GradingRuleset(
        id=uuid.uuid4(),
        school_id=ctx["school"].id,
        code=code,
        name=kwargs.pop("name", "LDC Général"),
        status=status,
        version=version,
        id_annee=kwargs.pop("id_annee", ctx["annee"].id),
        id_program=kwargs.pop("id_program", None),
        id_niveau=kwargs.pop("id_niveau", None),
        id_matiere=kwargs.pop("id_matiere", None),
        scale_max=kwargs.pop("scale_max", Decimal("20.00")),
        rounding_mode=kwargs.pop("rounding_mode", "half_up"),
        rounding_precision=kwargs.pop("rounding_precision", 2),
        created_by=kwargs.pop("created_by", ctx["user"].id),
        **kwargs,
    )
    db.add(rs)
    db.flush()
    return rs


def _add_component(db, ruleset, ctx, *, code, label, eval_code, weight, sequence, **kwargs):
    et = _eval_type(db, ctx["school"].id, eval_code)
    comp = GradingRuleComponent(
        id=uuid.uuid4(),
        school_id=ctx["school"].id,
        ruleset_id=ruleset.id,
        code=code,
        label=label,
        id_evaluation_type=et.id,
        weight=Decimal(str(weight)),
        sequence=sequence,
        evaluation_context=kwargs.pop("evaluation_context", "normal"),
        is_required=kwargs.pop("is_required", True),
        **kwargs,
    )
    db.add(comp)
    db.flush()
    return comp


class TestGradingRulesetCreation:
    def test_create_ruleset_and_components_60_40(self, db, grading_school_pair):
        a = grading_school_pair["a"]
        rs = _make_ruleset(db, a, id_program=a["program"].id)
        c1 = _add_component(
            db, rs, a, code="DEV", label="Devoirs", eval_code="devoir", weight="60.00", sequence=1
        )
        c2 = _add_component(
            db, rs, a, code="COMP", label="Composition", eval_code="composition", weight="40.00", sequence=2
        )
        db.commit()
        reloaded = db.query(GradingRuleset).filter(GradingRuleset.id == rs.id).one()
        assert reloaded.status == "draft"
        assert reloaded.version == 1
        assert reloaded.scale_max == Decimal("20.00")
        assert len(reloaded.components) == 2
        assert {c.code for c in reloaded.components} == {"DEV", "COMP"}
        assert c1.weight + c2.weight == Decimal("100.00")
        assert c1.id_evaluation_type != c2.id_evaluation_type

    def test_create_technique_30_20_50(self, db, grading_school_pair):
        a = grading_school_pair["a"]
        rs = _make_ruleset(db, a, name="Technique")
        _add_component(db, rs, a, code="DEV", label="Devoirs", eval_code="devoir", weight="30", sequence=1)
        _add_component(db, rs, a, code="TP", label="TP", eval_code="tp", weight="20", sequence=2)
        _add_component(
            db, rs, a, code="COMP", label="Composition", eval_code="composition", weight="50", sequence=3
        )
        db.commit()
        assert db.query(GradingRuleComponent).filter(GradingRuleComponent.ruleset_id == rs.id).count() == 3

    def test_subject_scoped_ruleset(self, db, grading_school_pair):
        a = grading_school_pair["a"]
        rs = _make_ruleset(
            db,
            a,
            id_program=a["program"].id,
            id_niveau=a["niveau"].id,
            id_matiere=a["matiere"].id,
        )
        _add_component(db, rs, a, code="DEV", label="Devoirs", eval_code="devoir", weight="70", sequence=1)
        _add_component(
            db, rs, a, code="COMP", label="Composition", eval_code="composition", weight="30", sequence=2
        )
        db.commit()
        assert rs.id_matiere == a["matiere"].id

    def test_system_evaluation_types_seeded(self, db, grading_school_pair):
        a = grading_school_pair["a"]
        codes = {
            r.code
            for r in db.query(EvaluationType).filter(EvaluationType.school_id == a["school"].id).all()
        }
        assert {
            "devoir",
            "composition",
            "tp",
            "oral",
            "exam_blanc",
            "rattrapage",
        }.issubset(codes)
        assert _eval_type(db, a["school"].id, "devoir").is_system is True


class TestGradingConstraints:
    def test_reject_weight_zero(self, db, grading_school_pair):
        a = grading_school_pair["a"]
        rs = _make_ruleset(db, a, code="W0")
        with pytest.raises(IntegrityError):
            _add_component(db, rs, a, code="DEV", label="Devoirs", eval_code="devoir", weight="0", sequence=1)
            db.flush()
        db.rollback()

    def test_reject_weight_over_100(self, db, grading_school_pair):
        a = grading_school_pair["a"]
        rs = _make_ruleset(db, a, code="W101")
        with pytest.raises(IntegrityError):
            _add_component(
                db, rs, a, code="DEV", label="Devoirs", eval_code="devoir", weight="100.01", sequence=1
            )
            db.flush()
        db.rollback()

    def test_reject_scale_max_zero(self, db, grading_school_pair):
        a = grading_school_pair["a"]
        with pytest.raises(IntegrityError):
            _make_ruleset(db, a, code="SCALE0", scale_max=Decimal(0))
            db.flush()
        db.rollback()

    def test_reject_version_zero(self, db, grading_school_pair):
        a = grading_school_pair["a"]
        with pytest.raises(IntegrityError):
            _make_ruleset(db, a, code="VER0", version=0)
            db.flush()
        db.rollback()

    def test_reject_invalid_status(self, db, grading_school_pair):
        a = grading_school_pair["a"]
        with pytest.raises(IntegrityError):
            _make_ruleset(db, a, code="STBAD", status="published")
            db.flush()
        db.rollback()

    def test_reject_invalid_rounding(self, db, grading_school_pair):
        a = grading_school_pair["a"]
        with pytest.raises(IntegrityError):
            _make_ruleset(db, a, code="RND", rounding_mode="bankers")
            db.flush()
        db.rollback()

    def test_reject_sequence_zero(self, db, grading_school_pair):
        a = grading_school_pair["a"]
        rs = _make_ruleset(db, a, code="SEQ0")
        with pytest.raises(IntegrityError):
            _add_component(db, rs, a, code="DEV", label="Devoirs", eval_code="devoir", weight="50", sequence=0)
            db.flush()
        db.rollback()

    def test_reject_duplicate_code_version(self, db, grading_school_pair):
        a = grading_school_pair["a"]
        dup = f"DUP-{_uid()}"
        _make_ruleset(db, a, code=dup, version=1)
        db.flush()
        with pytest.raises(IntegrityError):
            _make_ruleset(db, a, code=dup, version=1, name="Other")
            db.flush()
        db.rollback()

    def test_reject_niveau_without_program(self, db, grading_school_pair):
        a = grading_school_pair["a"]
        with pytest.raises(IntegrityError):
            _make_ruleset(db, a, code="NIV", id_niveau=a["niveau"].id, id_program=None)
            db.flush()
        db.rollback()

    def test_reject_duplicate_component_sequence(self, db, grading_school_pair):
        a = grading_school_pair["a"]
        rs = _make_ruleset(db, a, code="SEQDUP")
        _add_component(db, rs, a, code="DEV", label="Devoirs", eval_code="devoir", weight="50", sequence=1)
        with pytest.raises(IntegrityError):
            _add_component(
                db, rs, a, code="COMP", label="Composition", eval_code="composition", weight="50", sequence=1
            )
            db.flush()
        db.rollback()

    def test_reject_invalid_context(self, db, grading_school_pair):
        a = grading_school_pair["a"]
        rs = _make_ruleset(db, a, code="CTX")
        with pytest.raises(IntegrityError):
            _add_component(
                db,
                rs,
                a,
                code="DEV",
                label="Devoirs",
                eval_code="devoir",
                weight="100",
                sequence=1,
                evaluation_context="custom_bad",
            )
            db.flush()
        db.rollback()


class TestGradingVersioning:
    def test_multiple_versions_same_code(self, db, grading_school_pair):
        a = grading_school_pair["a"]
        base = f"LDC-{_uid()}"
        v1 = _make_ruleset(db, a, code=base, version=1, status="archived")
        v2 = _make_ruleset(db, a, code=base, version=2, status="active")
        v3 = _make_ruleset(db, a, code=base, version=3, status="draft")
        db.commit()
        versions = (
            db.query(GradingRuleset)
            .filter(GradingRuleset.school_id == a["school"].id, GradingRuleset.code == base)
            .order_by(GradingRuleset.version)
            .all()
        )
        assert [v.version for v in versions] == [1, 2, 3]
        assert [v.status for v in versions] == ["archived", "active", "draft"]
        assert db.query(GradingRuleset).filter(GradingRuleset.id == v1.id).one().status == "archived"
        assert v2.id != v3.id


class TestGradingTenantIsolation:
    def test_ruleset_cannot_reference_year_b(self, db, grading_school_pair):
        a, b = grading_school_pair["a"], grading_school_pair["b"]
        with pytest.raises(IntegrityError):
            _make_ruleset(db, a, code="XYEAR", id_annee=b["annee"].id)
            db.flush()
        db.rollback()

    def test_ruleset_cannot_reference_program_b(self, db, grading_school_pair):
        a, b = grading_school_pair["a"], grading_school_pair["b"]
        with pytest.raises(IntegrityError):
            _make_ruleset(db, a, code="XPROG", id_program=b["program"].id)
            db.flush()
        db.rollback()

    def test_ruleset_cannot_reference_niveau_b(self, db, grading_school_pair):
        a, b = grading_school_pair["a"], grading_school_pair["b"]
        with pytest.raises(IntegrityError):
            _make_ruleset(
                db,
                a,
                code="XNIV",
                id_program=a["program"].id,
                id_niveau=b["niveau"].id,
            )
            db.flush()
        db.rollback()

    def test_ruleset_cannot_reference_matiere_b(self, db, grading_school_pair):
        a, b = grading_school_pair["a"], grading_school_pair["b"]
        with pytest.raises(IntegrityError):
            _make_ruleset(db, a, code="XMAT", id_matiere=b["matiere"].id)
            db.flush()
        db.rollback()

    def test_component_cannot_use_eval_type_from_school_b(self, db, grading_school_pair):
        a, b = grading_school_pair["a"], grading_school_pair["b"]
        rs = _make_ruleset(db, a, code="XET")
        et_b = _eval_type(db, b["school"].id, "devoir")
        with pytest.raises(IntegrityError):
            db.add(
                GradingRuleComponent(
                    id=uuid.uuid4(),
                    school_id=a["school"].id,
                    ruleset_id=rs.id,
                    code="DEV",
                    label="Devoirs",
                    id_evaluation_type=et_b.id,
                    weight=Decimal("100.00"),
                    sequence=1,
                )
            )
            db.flush()
        db.rollback()

    def test_component_cannot_attach_to_ruleset_school_b(self, db, grading_school_pair):
        a, b = grading_school_pair["a"], grading_school_pair["b"]
        rs_b = _make_ruleset(db, b, code="OWN")
        et_a = _eval_type(db, a["school"].id, "devoir")
        with pytest.raises(IntegrityError):
            db.add(
                GradingRuleComponent(
                    id=uuid.uuid4(),
                    school_id=a["school"].id,
                    ruleset_id=rs_b.id,
                    code="DEV",
                    label="Devoirs",
                    id_evaluation_type=et_a.id,
                    weight=Decimal("100.00"),
                    sequence=1,
                )
            )
            db.flush()
        db.rollback()

    def test_no_orm_leak_query_by_school(self, db, grading_school_pair):
        a, b = grading_school_pair["a"], grading_school_pair["b"]
        code_a = f"ONLYA-{_uid()}"
        code_b = f"ONLYB-{_uid()}"
        _make_ruleset(db, a, code=code_a)
        _make_ruleset(db, b, code=code_b)
        db.commit()
        a_codes = {
            r.code
            for r in db.query(GradingRuleset).filter(GradingRuleset.school_id == a["school"].id).all()
        }
        assert code_a in a_codes
        assert code_b not in a_codes


class TestWeightVsCoefficientSeparation:
    def test_coefficient_matiere_untouched_by_ruleset(self, db, grading_school_pair):
        a = grading_school_pair["a"]
        coef = (
            db.query(CoefficientMatiere)
            .filter(
                CoefficientMatiere.id_matiere == a["matiere"].id,
                CoefficientMatiere.id_niveau == a["niveau"].id,
            )
            .first()
        )
        if not coef:
            coef = CoefficientMatiere(
                id=uuid.uuid4(),
                id_matiere=a["matiere"].id,
                id_niveau=a["niveau"].id,
                coefficient=Decimal("4.00"),
            )
            db.add(coef)
            db.flush()
        else:
            coef.coefficient = Decimal("4.00")
            db.flush()
        rs = _make_ruleset(db, a, id_matiere=a["matiere"].id)
        _add_component(db, rs, a, code="DEV", label="Devoirs", eval_code="devoir", weight="60", sequence=1)
        _add_component(
            db, rs, a, code="COMP", label="Composition", eval_code="composition", weight="40", sequence=2
        )
        db.commit()
        reloaded = db.query(CoefficientMatiere).filter(CoefficientMatiere.id == coef.id).one()
        assert reloaded.coefficient == Decimal("4.00")
        assert rs.components[0].weight == Decimal("60.00")
        assert Decimal(str(reloaded.coefficient)) != rs.components[0].weight


class TestCustomEvaluationType:
    def test_school_can_add_custom_type(self, db, grading_school_pair):
        a = grading_school_pair["a"]
        custom_code = f"atelier-{_uid()}"
        custom = EvaluationType(
            id=uuid.uuid4(),
            school_id=a["school"].id,
            code=custom_code,
            label="Atelier",
            is_system=False,
            is_active=True,
        )
        db.add(custom)
        db.flush()
        rs = _make_ruleset(db, a)
        db.add(
            GradingRuleComponent(
                id=uuid.uuid4(),
                school_id=a["school"].id,
                ruleset_id=rs.id,
                code="AT",
                label="Atelier",
                id_evaluation_type=custom.id,
                weight=Decimal("100.00"),
                sequence=1,
            )
        )
        db.commit()
        assert custom.is_system is False
