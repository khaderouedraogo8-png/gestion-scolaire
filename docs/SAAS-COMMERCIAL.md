# SaaS commercial — facturation plateforme

Boucle ops pour **10+ établissements** sans Stripe (paiement manuel / Mobile Money offline).

## Plans (seed auto)
| Code | Prix / mois | Max élèves | Essai |
|------|-------------|------------|-------|
| `essai` | 0 XOF | 100 | 14 j |
| `starter` | 25 000 XOF | 400 | 14 j |
| `pro` | 75 000 XOF | 1 500 | 14 j |

## Flux
1. **Onboarding** (`/platform/onboarding`) → école + admin + abo `starter` en **trial**
2. **Facturation** (`/platform/billing`) → assigner plan, émettre facture, marquer payée
3. **Expiration** : `POST /api/platform/billing/expire` ou `flask expire-subscriptions`
   - fin de période → `past_due` (grâce)
   - après grâce → `suspended` + `schools.is_active=false` (login bloqué)
4. **Paiement** d'une facture → période prolongée + réactivation école

## API (SUPER_ADMIN)
- `GET /api/platform/billing/plans`
- `GET /api/platform/billing/ops` — MRR, overdue, comptes
- `GET /api/platform/billing/subscriptions`
- `PUT /api/platform/billing/schools/:id/subscription`
- `POST /api/platform/billing/schools/:id/invoices`
- `POST /api/platform/billing/invoices/:id/pay`
- `POST /api/platform/billing/expire`

## Hors scope v1
Stripe / webhooks MM, signup public self-serve, invites email.
