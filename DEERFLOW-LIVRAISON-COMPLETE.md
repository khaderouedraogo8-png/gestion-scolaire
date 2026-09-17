# Livraison complète — Audit Deerflow UEMOA/CEMAC

**Branche :** `cursor/deerflow-depth-8bcc` → profondeur métier  
**Objectif :** tout item du document audit — Quick wins + Vision LT + Volets A/B **en profondeur**.

Légende : ✅ profondeur métier livrée · 🔶 partiel / évolutif

## 10 écarts critiques
| # | Item | Statut |
|---|---|---|
| 1 | Recouvrement fractionné + relances | ✅ |
| 2 | Offline-first (IndexedDB + conflits 409/412 + badge sync) | ✅ |
| 3 | Bulletins multi-pays + ZIP | ✅ |
| 4 | Mobile Money natif (HTTP + SANDBOX) | ✅ |
| 5 | SYSCOHADA (auto-écritures paiement/paie + grand livre + bilan/CR) | ✅ |
| 6 | Dashboards par rôle (directeur/comptable/secrétaire/surveillant/enseignant/parent/élève) | ✅ |
| 7 | WhatsApp + **bot parent** (SOLDE/NOTES/ÉCHÉANCES/ABSENCES) + OTP SMS | ✅ |
| 8 | Échéanciers / impayés | ✅ |
| 9 | Onboarding assisté | ✅ |
| 10 | Calm density + aging recouvrement | ✅ |

## Modules
| Module | Statut | Profondeur |
|---|---|---|
| A.1 Admission | ✅ | Funnel + convert |
| A.2 Fratries / remises / dossier PDF | ✅ | Moteur remises appliqué aux arriérés + PDF WeasyPrint + réinscription batch |
| A.3 Finance MM + recouvrement | ✅ | Aging J0-30…J90+ + top débiteurs + remises |
| A.4 Conseil de classe | ✅ | Sessions + décisions passage |
| A.5 Assiduité | ✅ | Appel mobile + justificatifs + décrochage |
| A.6 EDT | ✅ | Génération auto + conflits + publication |
| A.7 Comptabilité / paie | ✅ | Calcul paie + écritures 661/421/431 |
| A.8 Vie scolaire | ✅ | Cantine facturation, pointage transport, retards biblio |
| A.9 RH | ✅ | Contrats/congés + alertes expiration 30j |
| A.10 Portails | ✅ | Bot WA + OTP SMS + portail élève `/me/portal` |
| A.11 E-learning | 🔶 | Devoirs/quiz CRUD (LMS complet hors scope immédiat) |
| A.12 Front office | ✅ | Sortie QR HMAC + validation parent |
| A.13 Inventaire | ✅ | Alertes seuil + écarts inventaire annuel |
| B Landing / PWA | ✅ | Landing + offline queue conflictuelle |

## Variables utiles
- `WHATSAPP_SANDBOX=1` / `MM_SANDBOX=1` pour simulation
- `PAIE_TAUX_RETENUE` (défaut 5.5)
- `SMS_API_URL` + `SMS_API_KEY` pour OTP SMS
