# Livraison complète — Audit Deerflow UEMOA/CEMAC

**Branche :** `cursor/deerflow-full-delivery-8bcc`  
**Objectif :** tout item du document audit marché (Quick wins + Vision LT + Volets A/B).

Légende : ✅ livré utilisable · 🔶 livré MVP (API+UI, profondeur métier à enrichir) · ☐ non démarré

## 10 écarts critiques
| # | Item | Statut |
|---|---|---|
| 1 | Recouvrement fractionné + relances | ✅ |
| 2 | Offline-first (PWA + file sync notes/absences) | 🔶 |
| 3 | Bulletins multi-pays (templates BF/SN/CI/…) + ZIP | ✅ |
| 4 | Mobile Money natif (HTTP + SANDBOX) | ✅ |
| 5 | SYSCOHADA (plan + écritures + balance/bilan + paie) | 🔶 |
| 6 | Dashboards par rôle | 🔶 |
| 7 | WhatsApp (Meta Cloud + SANDBOX) + OTP parent | ✅ |
| 8 | Échéanciers / impayés | ✅ |
| 9 | Onboarding assisté | ✅ |
| 10 | Calm density | 🔶 |

## Modules
| Module | Statut |
|---|---|
| A.1 Admission (funnel + convert) | ✅ |
| A.2 Fratries / remises / dossier PDF | 🔶 |
| A.3 Finance MM + recouvrement détail | ✅ |
| A.4 Conseil de classe / décisions passage | ✅ |
| A.5 Justificatifs + décrochage + **appel mobile** | ✅ |
| A.6 EDT conflits / remplacements / publication / **génération auto** | ✅ |
| A.7 Comptabilité / paie | 🔶 |
| A.8 Vie scolaire (cantine, transport, internat, infirmière, biblio) | 🔶 |
| A.9 RH contrats / congés | 🔶 |
| A.10 OTP WhatsApp/SMS + portail élève | 🔶 |
| A.11 E-learning devoirs / quiz | 🔶 |
| A.12 Front office visiteurs / sorties | 🔶 |
| A.13 Inventaire | 🔶 |
| B Landing marketing | ✅ |
| B PWA offline queue | 🔶 |

## Notes d’honnêteté
- MM / WhatsApp : succès réel uniquement si clés API **ou** `*_SANDBOX=1`. Sinon `NON_CONFIGURE` (pas de faux succès).
- Offline-first : file locale + SW enrichi — pas encore sync conflictuelle multi-appareils complète type EduSahel.
- SYSCOHADA / paie / vie scolaire : CRUD + écrans opérationnels MVP, pas un ERP comptable certifié.
