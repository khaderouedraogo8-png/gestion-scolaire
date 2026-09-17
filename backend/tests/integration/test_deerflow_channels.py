"""Canaux WhatsApp / Mobile Money — NON_CONFIGURE vs SANDBOX."""


def test_whatsapp_non_configure_refuse(app, monkeypatch):
    monkeypatch.setitem(app.config, "WHATSAPP_SANDBOX", False)
    monkeypatch.setitem(app.config, "WHATSAPP_API_TOKEN", "")
    monkeypatch.setitem(app.config, "WHATSAPP_PHONE_NUMBER_ID", "")
    with app.app_context():
        from app.services.channels.whatsapp import envoyer_whatsapp, whatsapp_status

        st = whatsapp_status()
        assert st.status == "NON_CONFIGURE"
        ok, code = envoyer_whatsapp("+22670000000", "test")
        assert ok is False
        assert code == "NON_CONFIGURE"


def test_whatsapp_sandbox_simule(app, monkeypatch):
    monkeypatch.setitem(app.config, "WHATSAPP_SANDBOX", True)
    monkeypatch.setitem(app.config, "WHATSAPP_API_TOKEN", "")
    monkeypatch.setitem(app.config, "WHATSAPP_PHONE_NUMBER_ID", "")
    with app.app_context():
        from app.services.channels.whatsapp import envoyer_whatsapp, whatsapp_status

        assert whatsapp_status().status == "SANDBOX"
        ok, code = envoyer_whatsapp("+22670000000", "Bonjour parent")
        assert ok is True
        assert code == "SANDBOX_OK"


def test_mm_non_configure_refuse(app, monkeypatch):
    monkeypatch.setitem(app.config, "MM_SANDBOX", False)
    for op in ("ORANGE", "WAVE", "MOOV", "MTN"):
        monkeypatch.setitem(app.config, f"MM_{op}_API_KEY", "")
    with app.app_context():
        from app.services.channels.mobile_money import initier_paiement, mobile_money_status

        assert mobile_money_status().status == "NON_CONFIGURE"
        ok, code, payload = initier_paiement(
            operateur="orange", montant=1000, telephone="70000000", reference="R1"
        )
        assert ok is False
        assert code == "NON_CONFIGURE"
        assert payload["status"] == "NON_CONFIGURE"


def test_mm_sandbox_simule(app, monkeypatch):
    monkeypatch.setitem(app.config, "MM_SANDBOX", True)
    for op in ("ORANGE", "WAVE", "MOOV", "MTN"):
        monkeypatch.setitem(app.config, f"MM_{op}_API_KEY", "")
    with app.app_context():
        from app.services.channels.mobile_money import initier_paiement, mobile_money_status

        assert mobile_money_status().status == "SANDBOX"
        ok, code, payload = initier_paiement(
            operateur="wave", montant=5000, telephone="70000000", reference="R2"
        )
        assert ok is True
        assert code == "SANDBOX_OK"
        assert payload["status"] == "PENDING_SANDBOX"
