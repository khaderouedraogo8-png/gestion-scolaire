"""Bot WhatsApp parent — commandes texte SOLDE / NOTES / ECHEANCES / ABSENCES / AIDE."""
from __future__ import annotations

import re
import uuid
from datetime import date, timedelta

from flask import current_app

from app.extensions import get_db
from app.models import (
    Absence,
    AnneeScolaire,
    EcheancePaiement,
    Eleve,
    EleveParent,
    Evaluation,
    FraisScolaire,
    Inscription,
    Note,
    ParentTuteur,
)
from app.services.channels.whatsapp import envoyer_whatsapp
from app.services.finance_arrieres import list_arrieres

COMMANDS = ("SOLDE", "NOTES", "ECHEANCES", "ABSENCES", "AIDE")

_AIDE_TEXT = (
    "Commandes disponibles :\n"
    "• SOLDE — solde / arriérés de scolarité\n"
    "• NOTES — dernières notes publiées\n"
    "• ECHEANCES — prochaines échéances (7 j)\n"
    "• ABSENCES — absences récentes\n"
    "• AIDE — cette aide"
)


def normalize_phone(raw: str | None) -> str:
    if not raw:
        return ""
    digits = re.sub(r"\D+", "", str(raw))
    # Comparaison souple : garder les 8–12 derniers chiffres
    return digits[-12:] if len(digits) > 12 else digits


def parse_command(text: str | None) -> str:
    raw = (text or "").strip().upper()
    if not raw:
        return "AIDE"
    first = re.split(r"[\s,;:]+", raw, maxsplit=1)[0]
    # Accents / variantes
    aliases = {
        "ÉCHÉANCES": "ECHEANCES",
        "ECHEANCE": "ECHEANCES",
        "ÉCHEANCES": "ECHEANCES",
        "HELP": "AIDE",
        "NOTE": "NOTES",
        "ABSENCE": "ABSENCES",
        "BALANCE": "SOLDE",
    }
    cmd = aliases.get(first, first)
    return cmd if cmd in COMMANDS else "AIDE"


def find_parent_by_phone(telephone: str) -> ParentTuteur | None:
    db = get_db()
    needle = normalize_phone(telephone)
    if not needle:
        return None
    parents = db.query(ParentTuteur).filter(ParentTuteur.telephone.isnot(None)).all()
    for p in parents:
        if normalize_phone(p.telephone) == needle or normalize_phone(p.telephone).endswith(
            needle[-8:]
        ):
            return p
    return None


def _linked_eleves(parent: ParentTuteur) -> list[Eleve]:
    db = get_db()
    links = db.query(EleveParent).filter(EleveParent.id_parent == parent.id).all()
    eleves = []
    for link in links:
        e = (
            db.query(Eleve)
            .filter(Eleve.id == link.id_eleve, Eleve.school_id == parent.school_id)
            .first()
        )
        if e:
            eleves.append(e)
    return eleves


def _active_annee(school_id: uuid.UUID) -> AnneeScolaire | None:
    db = get_db()
    return (
        db.query(AnneeScolaire)
        .filter(AnneeScolaire.school_id == school_id, AnneeScolaire.est_active.is_(True))
        .first()
    )


def _cmd_solde(eleves: list[Eleve], school_id: uuid.UUID) -> str:
    db = get_db()
    annee = _active_annee(school_id)
    if not annee:
        return "Aucune année scolaire active."
    rows = list_arrieres(db, annee.id, school_id=school_id, as_of=date.today())
    by_id = {r["id_eleve"]: r for r in rows}
    lines = ["💰 Solde scolarité :"]
    for e in eleves:
        r = by_id.get(e.id)
        if not r:
            lines.append(f"• {e.prenom} {e.nom} : à jour (0 FCFA)")
            continue
        arriere = float(r.get("arriere") or 0)
        if arriere <= 0:
            lines.append(f"• {e.prenom} {e.nom} : à jour")
        else:
            lines.append(
                f"• {e.prenom} {e.nom} : {arriere:,.0f} FCFA d'arriéré "
                f"(dû {float(r['total_du']):,.0f} / payé {float(r['total_paye']):,.0f})"
            )
    return "\n".join(lines).replace(",", " ")


def _cmd_notes(eleves: list[Eleve], school_id: uuid.UUID) -> str:
    db = get_db()
    lines = ["📝 Dernières notes :"]
    any_note = False
    for e in eleves:
        notes = (
            db.query(Note)
            .filter(Note.id_eleve == e.id, Note.school_id == school_id)
            .order_by(Note.saisi_le.desc())
            .limit(5)
            .all()
        )
        visible = []
        for n in notes:
            ev = db.query(Evaluation).filter(Evaluation.id == n.id_evaluation).first()
            if ev and getattr(ev, "statut_saisie", None) == "cloturee" or ev and getattr(ev, "statut_publication", None) == "publie":
                visible.append((n, ev))
            elif not ev:
                visible.append((n, None))
        if not visible:
            # Fallback : notes récentes même non clôturées (sandbox / démo)
            for n in notes[:3]:
                visible.append((n, db.query(Evaluation).filter(Evaluation.id == n.id_evaluation).first()))
        if not visible:
            lines.append(f"• {e.prenom} {e.nom} : aucune note récente")
            continue
        any_note = True
        lines.append(f"• {e.prenom} {e.nom} :")
        for n, ev in visible[:3]:
            label = getattr(ev, "libelle", None) or getattr(ev, "type_evaluation", None) or "Note"
            if n.absent:
                val = "Absent"
            elif n.valeur_note is not None:
                val = f"{float(n.valeur_note):g}"
            else:
                val = "—"
            lines.append(f"  – {label} : {val}")
    if not any_note and len(eleves) == 0:
        return "Aucun élève lié."
    return "\n".join(lines)


def _cmd_echeances(eleves: list[Eleve], school_id: uuid.UUID) -> str:
    db = get_db()
    annee = _active_annee(school_id)
    if not annee:
        return "Aucune année scolaire active."
    today = date.today()
    until = today + timedelta(days=7)
    lines = ["📅 Échéances (7 jours) :"]
    found = False
    for e in eleves:
        insc = (
            db.query(Inscription)
            .filter(
                Inscription.id_eleve == e.id,
                Inscription.id_annee == annee.id,
                Inscription.statut.in_(("inscrit", "reinscrit")),
            )
            .first()
        )
        if not insc:
            continue
        from app.models import Classe

        classe = db.query(Classe).filter(Classe.id == insc.id_classe).first()
        if not classe:
            continue
        frais_list = (
            db.query(FraisScolaire)
            .filter(
                FraisScolaire.id_niveau == classe.id_niveau,
                FraisScolaire.id_annee == annee.id,
                FraisScolaire.school_id == school_id,
            )
            .all()
        )
        child_lines = []
        for frais in frais_list:
            for ec in (
                db.query(EcheancePaiement)
                .filter(EcheancePaiement.id_frais == frais.id)
                .order_by(EcheancePaiement.date_echeance)
                .all()
            ):
                if today <= ec.date_echeance <= until:
                    child_lines.append(
                        f"  – {ec.libelle or frais.motif} : "
                        f"{float(ec.montant):,.0f} FCFA le {ec.date_echeance.isoformat()}"
                    )
        if child_lines:
            found = True
            lines.append(f"• {e.prenom} {e.nom} :")
            lines.extend(child_lines)
    if not found:
        lines.append("Aucune échéance dans les 7 prochains jours.")
    return "\n".join(lines).replace(",", " ")


def _cmd_absences(eleves: list[Eleve], school_id: uuid.UUID) -> str:
    db = get_db()
    since = date.today() - timedelta(days=30)
    lines = ["📋 Absences récentes (30 j) :"]
    for e in eleves:
        absences = (
            db.query(Absence)
            .filter(
                Absence.id_eleve == e.id,
                Absence.school_id == school_id,
                Absence.date_absence >= since,
            )
            .order_by(Absence.date_absence.desc())
            .limit(5)
            .all()
        )
        if not absences:
            lines.append(f"• {e.prenom} {e.nom} : aucune")
            continue
        lines.append(f"• {e.prenom} {e.nom} :")
        for a in absences:
            just = "justifiée" if a.justifiee else "non justifiée"
            typ = a.type_absence or "absence"
            lines.append(f"  – {a.date_absence.isoformat()} ({typ}, {just})")
    return "\n".join(lines)


def build_reply(telephone: str, text: str) -> dict:
    """Construit la réponse bot pour un message entrant.

    Returns dict: {ok, command, reply, parent_found, eleves_count, sent}
    """
    cmd = parse_command(text)
    parent = find_parent_by_phone(telephone)
    if not parent:
        reply = (
            "Numéro non reconnu. Contactez le secrétariat pour lier votre téléphone "
            "à votre fiche parent.\n\n" + _AIDE_TEXT
        )
        return {
            "ok": False,
            "command": cmd,
            "reply": reply,
            "parent_found": False,
            "eleves_count": 0,
            "sent": False,
        }

    eleves = _linked_eleves(parent)
    if not eleves and cmd != "AIDE":
        reply = (
            f"Bonjour {parent.prenom},\n"
            "Aucun élève n'est lié à votre fiche parent.\n\n" + _AIDE_TEXT
        )
        return {
            "ok": True,
            "command": cmd,
            "reply": reply,
            "parent_found": True,
            "eleves_count": 0,
            "sent": False,
        }

    if cmd == "AIDE":
        reply = f"Bonjour {parent.prenom},\n\n{_AIDE_TEXT}"
    elif cmd == "SOLDE":
        reply = _cmd_solde(eleves, parent.school_id)
    elif cmd == "NOTES":
        reply = _cmd_notes(eleves, parent.school_id)
    elif cmd == "ECHEANCES":
        reply = _cmd_echeances(eleves, parent.school_id)
    elif cmd == "ABSENCES":
        reply = _cmd_absences(eleves, parent.school_id)
    else:
        reply = _AIDE_TEXT

    return {
        "ok": True,
        "command": cmd,
        "reply": reply,
        "parent_found": True,
        "eleves_count": len(eleves),
        "sent": False,
    }


def handle_inbound(telephone: str, text: str, *, send: bool = True) -> dict:
    """Traite un inbound : construit la réponse et optionnellement envoie via WhatsApp."""
    result = build_reply(telephone, text)
    if send and result.get("reply"):
        ok, code = envoyer_whatsapp(telephone, result["reply"])
        result["sent"] = bool(ok)
        result["send_code"] = code
        current_app.logger.info(
            "WhatsApp bot cmd=%s parent=%s sent=%s code=%s",
            result.get("command"),
            result.get("parent_found"),
            ok,
            code,
        )
    return result


def extract_meta_inbound(payload: dict) -> list[tuple[str, str]]:
    """Extrait (from, text) depuis un webhook Meta Cloud API."""
    messages: list[tuple[str, str]] = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            for msg in value.get("messages") or []:
                if msg.get("type") != "text":
                    continue
                frm = msg.get("from") or ""
                body = (msg.get("text") or {}).get("body") or ""
                if frm:
                    messages.append((frm, body))
    # Format plat sandbox déjà normalisé
    if not messages and payload.get("from"):
        messages.append((str(payload["from"]), str(payload.get("text") or "")))
    return messages
