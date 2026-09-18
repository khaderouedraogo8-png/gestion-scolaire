"""Facturation SaaS — plans, abonnements, factures, expiration → suspension."""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from flask import abort
from sqlalchemy import select

from app.extensions import get_db
from app.models import School
from app.models.billing import SaaSInvoice, SaaSPlan, SchoolSubscription
from app.utils.audit_logger import log_audit

DEFAULT_PLAN_CODE = "starter"
DEFAULT_PLANS = (
    {
        "code": "essai",
        "name": "Essai",
        "description": "Période d'essai 14 jours — jusqu'à 100 élèves",
        "price_xof": Decimal(0),
        "billing_interval": "mensuel",
        "max_eleves": 100,
        "trial_days": 14,
        "grace_days": 3,
        "sort_order": 0,
    },
    {
        "code": "starter",
        "name": "Starter",
        "description": "École primaire / collège — jusqu'à 400 élèves",
        "price_xof": Decimal(25000),
        "billing_interval": "mensuel",
        "max_eleves": 400,
        "trial_days": 14,
        "grace_days": 7,
        "sort_order": 10,
    },
    {
        "code": "pro",
        "name": "Pro",
        "description": "Lycée / multi-cycles — jusqu'à 1500 élèves",
        "price_xof": Decimal(75000),
        "billing_interval": "mensuel",
        "max_eleves": 1500,
        "trial_days": 14,
        "grace_days": 7,
        "sort_order": 20,
    },
)


def ensure_default_plans(db=None) -> list[SaaSPlan]:
    db = db or get_db()
    created: list[SaaSPlan] = []
    for spec in DEFAULT_PLANS:
        row = db.query(SaaSPlan).filter(SaaSPlan.code == spec["code"]).first()
        if row:
            continue
        row = SaaSPlan(id=uuid.uuid4(), is_active=True, **spec)
        db.add(row)
        created.append(row)
    if created:
        db.flush()
    return created


def get_plan_by_code(code: str, *, db=None) -> SaaSPlan:
    db = db or get_db()
    ensure_default_plans(db)
    plan = db.query(SaaSPlan).filter(SaaSPlan.code == code, SaaSPlan.is_active.is_(True)).first()
    if not plan:
        abort(404, description=f"Plan SaaS introuvable: {code}")
    return plan


def _period_delta(plan: SaaSPlan) -> timedelta:
    if plan.billing_interval == "annuel":
        return timedelta(days=365)
    return timedelta(days=30)


def start_subscription_for_school(
    school: School,
    *,
    plan_code: str = DEFAULT_PLAN_CODE,
    actor_id: uuid.UUID | None = None,
    db=None,
) -> SchoolSubscription:
    """Crée (ou remplace) un abonnement en trial pour une école nouvellement onboardée."""
    db = db or get_db()
    plan = get_plan_by_code(plan_code, db=db)
    today = date.today()
    trial_end = today + timedelta(days=plan.trial_days or 14)

    existing = (
        db.query(SchoolSubscription).filter(SchoolSubscription.school_id == school.id).first()
    )
    if existing:
        existing.plan_id = plan.id
        existing.status = "trial"
        existing.trial_ends_at = trial_end
        existing.current_period_start = today
        existing.current_period_end = trial_end
        existing.grace_days = plan.grace_days
        sub = existing
    else:
        sub = SchoolSubscription(
            id=uuid.uuid4(),
            school_id=school.id,
            plan_id=plan.id,
            status="trial",
            trial_ends_at=trial_end,
            current_period_start=today,
            current_period_end=trial_end,
            grace_days=plan.grace_days,
        )
        db.add(sub)
    db.flush()
    log_audit(
        "SAAS_SUBSCRIPTION_STARTED",
        actor_id,
        "school_subscription",
        sub.id,
        details={"plan": plan.code, "status": sub.status, "trial_ends_at": str(trial_end)},
        school_id=school.id,
    )
    return sub


def assign_plan(
    school: School,
    plan_code: str,
    *,
    actor_id: uuid.UUID | None = None,
    start_active: bool = False,
) -> SchoolSubscription:
    db = get_db()
    plan = get_plan_by_code(plan_code, db=db)
    today = date.today()
    period_end = today + _period_delta(plan)
    sub = db.query(SchoolSubscription).filter(SchoolSubscription.school_id == school.id).first()
    if not sub:
        sub = start_subscription_for_school(school, plan_code=plan_code, actor_id=actor_id, db=db)
    sub.plan_id = plan.id
    sub.grace_days = plan.grace_days
    if start_active:
        sub.status = "active"
        sub.trial_ends_at = None
        sub.current_period_start = today
        sub.current_period_end = period_end
    else:
        sub.status = "trial"
        sub.trial_ends_at = today + timedelta(days=plan.trial_days or 14)
        sub.current_period_start = today
        sub.current_period_end = sub.trial_ends_at
    db.commit()
    log_audit(
        "SAAS_PLAN_ASSIGNED",
        actor_id,
        "school_subscription",
        sub.id,
        details={"plan": plan.code, "status": sub.status},
        school_id=school.id,
    )
    return sub


def _next_invoice_number(db, school: School) -> str:
    year = date.today().year
    prefix = f"SAAS-{school.code}-{year}-"
    last = (
        db.query(SaaSInvoice)
        .filter(SaaSInvoice.number.like(f"{prefix}%"))
        .order_by(SaaSInvoice.number.desc())
        .first()
    )
    seq = 1
    if last and last.number.rsplit("-", 1)[-1].isdigit():
        seq = int(last.number.rsplit("-", 1)[-1]) + 1
    return f"{prefix}{seq:04d}"


def issue_invoice(
    school: School,
    *,
    actor_id: uuid.UUID | None = None,
    amount_xof: Decimal | None = None,
    due_days: int = 7,
) -> SaaSInvoice:
    db = get_db()
    sub = db.query(SchoolSubscription).filter(SchoolSubscription.school_id == school.id).first()
    if not sub:
        abort(404, description="Aucun abonnement pour cette école")
    plan = db.get(SaaSPlan, sub.plan_id)
    if not plan:
        abort(404, description="Plan introuvable")
    amount = Decimal(str(amount_xof if amount_xof is not None else plan.price_xof))
    today = date.today()
    inv = SaaSInvoice(
        id=uuid.uuid4(),
        school_id=school.id,
        subscription_id=sub.id,
        number=_next_invoice_number(db, school),
        amount_xof=amount,
        status="issued",
        period_start=sub.current_period_start or today,
        period_end=sub.current_period_end or (today + _period_delta(plan)),
        due_at=today + timedelta(days=due_days),
    )
    db.add(inv)
    if sub.status == "trial":
        sub.status = "past_due" if amount > 0 else "active"
    elif sub.status == "active" and amount > 0:
        pass
    db.commit()
    log_audit(
        "SAAS_INVOICE_ISSUED",
        actor_id,
        "saas_invoice",
        inv.id,
        details={"number": inv.number, "amount": str(amount)},
        school_id=school.id,
    )
    return inv


def mark_invoice_paid(
    invoice: SaaSInvoice,
    *,
    actor_id: uuid.UUID | None = None,
    external_ref: str | None = None,
) -> SaaSInvoice:
    db = get_db()
    if invoice.status == "paid":
        return invoice
    if invoice.status == "void":
        abort(409, description="Facture annulée")
    invoice.status = "paid"
    invoice.paid_at = datetime.now(UTC)
    if external_ref:
        invoice.external_ref = external_ref

    sub = db.get(SchoolSubscription, invoice.subscription_id)
    school = db.get(School, invoice.school_id)
    plan = db.get(SaaSPlan, sub.plan_id) if sub else None
    if sub and plan:
        today = date.today()
        start = max(today, sub.current_period_end or today)
        sub.current_period_start = today
        sub.current_period_end = start + _period_delta(plan)
        sub.status = "active"
        sub.trial_ends_at = None
    if school and not school.is_active:
        school.is_active = True
        log_audit(
            "SCHOOL_ACTIVATED",
            actor_id,
            "schools",
            school.id,
            details={"reason": "invoice_paid"},
            school_id=school.id,
        )
    db.commit()
    log_audit(
        "SAAS_INVOICE_PAID",
        actor_id,
        "saas_invoice",
        invoice.id,
        details={"number": invoice.number, "external_ref": external_ref},
        school_id=invoice.school_id,
    )
    return invoice


def subscription_snapshot(sub: SchoolSubscription | None, plan: SaaSPlan | None = None) -> dict | None:
    if not sub:
        return None
    db = get_db()
    plan = plan or db.get(SaaSPlan, sub.plan_id)
    return {
        "id": str(sub.id),
        "status": sub.status,
        "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
        "current_period_start": (
            sub.current_period_start.isoformat() if sub.current_period_start else None
        ),
        "current_period_end": (
            sub.current_period_end.isoformat() if sub.current_period_end else None
        ),
        "grace_days": sub.grace_days,
        "plan": (
            {
                "id": str(plan.id),
                "code": plan.code,
                "name": plan.name,
                "price_xof": str(plan.price_xof),
                "billing_interval": plan.billing_interval,
                "max_eleves": plan.max_eleves,
            }
            if plan
            else None
        ),
    }


def process_expirations(*, as_of: date | None = None, actor_id: uuid.UUID | None = None) -> dict:
    """Passe trial/active → past_due → suspended + désactive l'école après grâce."""
    db = get_db()
    ensure_default_plans(db)
    today = as_of or date.today()
    stats = {"past_due": 0, "suspended": 0, "checked": 0}

    subs = db.execute(select(SchoolSubscription)).scalars().all()
    for sub in subs:
        stats["checked"] += 1
        if sub.status in ("canceled", "suspended"):
            continue
        period_end = sub.current_period_end or sub.trial_ends_at
        if not period_end or period_end >= today:
            continue

        grace = sub.grace_days or 0
        grace_end = period_end + timedelta(days=grace)
        school = db.get(School, sub.school_id)
        if today <= grace_end:
            if sub.status != "past_due":
                sub.status = "past_due"
                stats["past_due"] += 1
                log_audit(
                    "SAAS_SUBSCRIPTION_PAST_DUE",
                    actor_id,
                    "school_subscription",
                    sub.id,
                    details={"period_end": str(period_end)},
                    school_id=sub.school_id,
                )
            continue

        sub.status = "suspended"
        stats["suspended"] += 1
        if school and school.is_active:
            school.is_active = False
            log_audit(
                "SCHOOL_SUSPENDED_NONPAYMENT",
                actor_id,
                "schools",
                school.id,
                details={"subscription_id": str(sub.id), "period_end": str(period_end)},
                school_id=school.id,
            )
        log_audit(
            "SAAS_SUBSCRIPTION_SUSPENDED",
            actor_id,
            "school_subscription",
            sub.id,
            school_id=sub.school_id,
        )

    db.commit()
    return stats


def ops_summary() -> dict:
    db = get_db()
    ensure_default_plans(db)
    schools = db.query(School).all()
    subs = {s.school_id: s for s in db.query(SchoolSubscription).all()}
    by_status: dict[str, int] = {}
    overdue = 0
    mrr = Decimal(0)
    for school in schools:
        sub = subs.get(school.id)
        status = sub.status if sub else ("inactive" if not school.is_active else "none")
        by_status[status] = by_status.get(status, 0) + 1
        if sub and sub.status in ("past_due", "suspended"):
            overdue += 1
        if sub and sub.status == "active":
            plan = db.get(SaaSPlan, sub.plan_id)
            if plan and plan.billing_interval == "mensuel":
                mrr += Decimal(plan.price_xof or 0)
            elif plan and plan.billing_interval == "annuel":
                mrr += Decimal(plan.price_xof or 0) / 12
    return {
        "schools_total": len(schools),
        "schools_active": sum(1 for s in schools if s.is_active),
        "schools_inactive": sum(1 for s in schools if not s.is_active),
        "subscriptions_by_status": by_status,
        "overdue_count": overdue,
        "mrr_xof": float(mrr.quantize(Decimal(1))),
        "plans": [
            {
                "code": p.code,
                "name": p.name,
                "price_xof": float(p.price_xof),
                "max_eleves": p.max_eleves,
            }
            for p in db.query(SaaSPlan).filter(SaaSPlan.is_active.is_(True)).order_by(SaaSPlan.sort_order)
        ],
    }
