"""SaaS commercial billing — plans, abonnements, factures, expiration."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from app.auth.jwt_handler import hash_password
from app.models import School, Utilisateur
from app.models.billing import SchoolSubscription
from app.models.utilisateur import PLATFORM_ROLE_SUPER_ADMIN


@pytest.fixture
def super_admin(db):
    email = "super-billing@platform.local"
    user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
    if not user:
        user = Utilisateur(
            id=uuid.uuid4(),
            nom="Super",
            prenom="Billing",
            email=email,
            role=PLATFORM_ROLE_SUPER_ADMIN,
            mot_de_passe_hash=hash_password("SuperAdmin123!"),
            actif=True,
            doit_changer_mdp=False,
            school_id=None,
        )
        db.add(user)
        db.commit()
    return user


@pytest.fixture
def super_headers(client, super_admin):
    resp = client.post(
        "/api/login",
        json={"email": "super-billing@platform.local", "password": "SuperAdmin123!"},
    )
    assert resp.status_code == 200, resp.get_json()
    return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}


def test_plans_seed_and_ops(client, super_headers, default_school):
    plans = client.get("/api/platform/billing/plans", headers=super_headers)
    assert plans.status_code == 200, plans.get_json()
    codes = {p["code"] for p in plans.get_json()}
    assert {"essai", "starter", "pro"}.issubset(codes)

    ops = client.get("/api/platform/billing/ops", headers=super_headers)
    assert ops.status_code == 200
    body = ops.get_json()
    assert "mrr_xof" in body
    assert body["schools_total"] >= 1
    assert isinstance(body["plans"], list)
    assert len(body["plans"]) >= 3


def test_onboard_creates_trial_subscription(client, super_headers, db):
    code = f"SAAS{uuid.uuid4().hex[:6].upper()}"
    onboard = client.post(
        "/api/platform/schools/onboard",
        headers=super_headers,
        json={
            "name": "École SaaS Test",
            "code": code,
            "activate": True,
            "admin_nom": "Koné",
            "admin_prenom": "Awa",
            "admin_email": f"admin-{code.lower()}@saas.test",
            "admin_password": "AdminSaaS123!",
        },
    )
    assert onboard.status_code in (200, 201), onboard.get_json()
    school_id = onboard.get_json()["school"]["id"]

    sub = (
        db.query(SchoolSubscription)
        .filter(SchoolSubscription.school_id == uuid.UUID(school_id))
        .first()
    )
    assert sub is not None
    assert sub.status == "trial"

    listed = client.get("/api/platform/schools", headers=super_headers)
    assert listed.status_code == 200
    body = listed.get_json()
    rows = body if isinstance(body, list) else body.get("items", [])
    row = next(s for s in rows if s["id"] == school_id)
    assert row.get("subscription_status") == "trial"
    assert row.get("plan_code") == "starter"


def test_invoice_pay_and_expire_suspend(client, super_headers, db):
    code = f"PAY{uuid.uuid4().hex[:6].upper()}"
    onboard = client.post(
        "/api/platform/schools/onboard",
        headers=super_headers,
        json={
            "name": "École Pay",
            "code": code,
            "activate": True,
            "admin_nom": "Diallo",
            "admin_prenom": "Ibra",
            "admin_email": f"admin-{code.lower()}@saas.test",
            "admin_password": "AdminSaaS123!",
        },
    )
    school_id = onboard.get_json()["school"]["id"]

    assign = client.put(
        f"/api/platform/billing/schools/{school_id}/subscription",
        headers=super_headers,
        json={"plan_code": "pro", "start_active": True},
    )
    assert assign.status_code == 200, assign.get_json()
    assert assign.get_json()["status"] == "active"
    assert assign.get_json()["plan"]["code"] == "pro"

    inv = client.post(
        f"/api/platform/billing/schools/{school_id}/invoices",
        headers=super_headers,
        json={},
    )
    assert inv.status_code == 201, inv.get_json()
    invoice_id = inv.get_json()["id"]
    assert float(inv.get_json()["amount_xof"]) == 75000.0

    paid = client.post(
        f"/api/platform/billing/invoices/{invoice_id}/pay",
        headers=super_headers,
        json={"external_ref": "OM-TEST-001"},
    )
    assert paid.status_code == 200
    assert paid.get_json()["status"] == "paid"

    # Force expiration past grace → suspend
    sub = (
        db.query(SchoolSubscription)
        .filter(SchoolSubscription.school_id == uuid.UUID(school_id))
        .first()
    )
    sub.current_period_end = date.today() - timedelta(days=30)
    sub.grace_days = 0
    sub.status = "active"
    db.commit()

    expire = client.post("/api/platform/billing/expire", headers=super_headers)
    assert expire.status_code == 200
    assert expire.get_json()["suspended"] >= 1

    school = db.get(School, uuid.UUID(school_id))
    db.refresh(school)
    assert school.is_active is False
    db.refresh(sub)
    assert sub.status == "suspended"

    # Mark a new invoice paid → reactivate
    inv2 = client.post(
        f"/api/platform/billing/schools/{school_id}/invoices",
        headers=super_headers,
        json={"amount_xof": "75000"},
    )
    # School suspended — still can issue as super admin
    assert inv2.status_code == 201, inv2.get_json()
    pay2 = client.post(
        f"/api/platform/billing/invoices/{inv2.get_json()['id']}/pay",
        headers=super_headers,
        json={"external_ref": "WAVE-002"},
    )
    assert pay2.status_code == 200
    db.refresh(school)
    assert school.is_active is True
