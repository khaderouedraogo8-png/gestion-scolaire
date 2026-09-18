"""Routes facturation SaaS — console SUPER_ADMIN."""
from __future__ import annotations

from decimal import Decimal

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint, abort
from marshmallow import Schema, fields

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import require_super_admin
from app.extensions import get_db
from app.models import School
from app.models.billing import SaaSInvoice, SaaSPlan, SchoolSubscription
from app.services.billing import (
    assign_plan,
    ensure_default_plans,
    issue_invoice,
    mark_invoice_paid,
    ops_summary,
    process_expirations,
    subscription_snapshot,
)
from app.services.tenant import reject_client_school_id

blp = Blueprint(
    "platform_billing",
    __name__,
    description="Facturation SaaS plateforme",
)


class PlanSchema(Schema):
    id = fields.UUID(dump_only=True)
    code = fields.String()
    name = fields.String()
    description = fields.String(allow_none=True)
    price_xof = fields.Decimal(as_string=True)
    billing_interval = fields.String()
    max_eleves = fields.Integer(allow_none=True)
    trial_days = fields.Integer()
    grace_days = fields.Integer()
    is_active = fields.Boolean()


class AssignPlanSchema(Schema):
    plan_code = fields.String(required=True)
    start_active = fields.Boolean(load_default=False)


class IssueInvoiceSchema(Schema):
    amount_xof = fields.Decimal(as_string=True, allow_none=True)
    due_days = fields.Integer(load_default=7)


class PayInvoiceSchema(Schema):
    external_ref = fields.String(allow_none=True)


class InvoiceSchema(Schema):
    id = fields.UUID(dump_only=True)
    school_id = fields.UUID()
    subscription_id = fields.UUID()
    number = fields.String()
    amount_xof = fields.Decimal(as_string=True)
    status = fields.String()
    period_start = fields.Date(allow_none=True)
    period_end = fields.Date(allow_none=True)
    due_at = fields.Date(allow_none=True)
    paid_at = fields.DateTime(allow_none=True)
    external_ref = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)


@blp.route("/plans")
class PlansList(MethodView):
    @jwt_required()
    @require_super_admin
    def get(self):
        db = get_db()
        ensure_default_plans(db)
        db.commit()
        rows = (
            db.query(SaaSPlan)
            .filter(SaaSPlan.is_active.is_(True))
            .order_by(SaaSPlan.sort_order)
            .all()
        )
        return jsonify(PlanSchema(many=True).dump(rows))


@blp.route("/ops")
class PlatformOps(MethodView):
    @jwt_required()
    @require_super_admin
    def get(self):
        return jsonify(ops_summary())


@blp.route("/subscriptions")
class SubscriptionsList(MethodView):
    @jwt_required()
    @require_super_admin
    def get(self):
        db = get_db()
        ensure_default_plans(db)
        status = request.args.get("status")
        q = db.query(SchoolSubscription)
        if status:
            q = q.filter(SchoolSubscription.status == status)
        rows = q.order_by(SchoolSubscription.updated_at.desc()).all()
        out = []
        for sub in rows:
            school = db.get(School, sub.school_id)
            snap = subscription_snapshot(sub)
            out.append(
                {
                    "school_id": str(sub.school_id),
                    "school_code": school.code if school else None,
                    "school_name": school.name if school else None,
                    "school_active": school.is_active if school else None,
                    "subscription": snap,
                }
            )
        return jsonify(out)


@blp.route("/schools/<uuid:school_id>/subscription")
class SchoolSubscriptionDetail(MethodView):
    @jwt_required()
    @require_super_admin
    def get(self, school_id):
        db = get_db()
        school = db.get(School, school_id)
        if not school:
            abort(404, message="École introuvable")
        sub = (
            db.query(SchoolSubscription)
            .filter(SchoolSubscription.school_id == school_id)
            .first()
        )
        return jsonify(
            {
                "school_id": str(school.id),
                "school_code": school.code,
                "subscription": subscription_snapshot(sub),
            }
        )

    @jwt_required()
    @require_super_admin
    @blp.arguments(AssignPlanSchema)
    def put(self, data, school_id):
        reject_client_school_id(data)
        db = get_db()
        school = db.get(School, school_id)
        if not school:
            abort(404, message="École introuvable")
        actor = get_current_user()
        sub = assign_plan(
            school,
            data["plan_code"],
            actor_id=actor.id,
            start_active=bool(data.get("start_active")),
        )
        return jsonify(subscription_snapshot(sub))


@blp.route("/schools/<uuid:school_id>/invoices")
class SchoolInvoices(MethodView):
    @jwt_required()
    @require_super_admin
    def get(self, school_id):
        db = get_db()
        if not db.get(School, school_id):
            abort(404, message="École introuvable")
        rows = (
            db.query(SaaSInvoice)
            .filter(SaaSInvoice.school_id == school_id)
            .order_by(SaaSInvoice.created_at.desc())
            .all()
        )
        return jsonify(InvoiceSchema(many=True).dump(rows))

    @jwt_required()
    @require_super_admin
    @blp.arguments(IssueInvoiceSchema)
    def post(self, data, school_id):
        reject_client_school_id(data)
        db = get_db()
        school = db.get(School, school_id)
        if not school:
            abort(404, message="École introuvable")
        actor = get_current_user()
        amount = data.get("amount_xof")
        inv = issue_invoice(
            school,
            actor_id=actor.id,
            amount_xof=Decimal(str(amount)) if amount is not None else None,
            due_days=int(data.get("due_days") or 7),
        )
        return jsonify(InvoiceSchema().dump(inv)), 201


@blp.route("/invoices/<uuid:invoice_id>/pay")
class InvoicePay(MethodView):
    @jwt_required()
    @require_super_admin
    @blp.arguments(PayInvoiceSchema)
    def post(self, data, invoice_id):
        db = get_db()
        inv = db.get(SaaSInvoice, invoice_id)
        if not inv:
            abort(404, message="Facture introuvable")
        actor = get_current_user()
        inv = mark_invoice_paid(
            inv,
            actor_id=actor.id,
            external_ref=data.get("external_ref"),
        )
        return jsonify(InvoiceSchema().dump(inv))


@blp.route("/expire")
class ExpireSubscriptions(MethodView):
    @jwt_required()
    @require_super_admin
    def post(self):
        actor = get_current_user()
        stats = process_expirations(actor_id=actor.id)
        return jsonify(stats)
