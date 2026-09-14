# Design System — Gestion Scolaire Premium SaaS

## Direction

Identité **SaaS B2B premium** (Linear / Vercel / Stripe Dashboard), adaptée à l’éducation UEMOA/CEMAC.
Objectif : convaincre un directeur d’établissement de payer un abonnement — crédibilité, clarté, zéro look “template admin”.

## Choix (1 phrase chacun)

| Décision | Pourquoi |
|---|---|
| Brand pétrole `#0F766E` | Sobre, distinctif, crédible éducation ; évite le purple générique AI |
| Fond `craie` `#F8FAFC` | Neutre froid aéré, contraste doux avec le blanc des surfaces |
| Dark anthracite `#020617` / `#1E293B` | Surfaces élevées, pas d’inversion brute |
| Plus Jakarta Sans | Sans moderne à personnalité (remplace Fraunces institutional) |
| Radius 10 / 8 / 6 | Un seul langage de coins (card / input / badge) |
| Ombres soft 1px | Jamais de drop-shadow dur — lecture “produit soigné” |
| Accents sémantiques seuls | Vert / ambre / rose = statut, jamais décoratifs |
| Motion 150–250ms | Hover/focus fluides sans bruit |

## Tokens Tailwind

Voir `frontend/tailwind.config.js` — mapping legacy `or-cachet` → pétrole pour zéro churn métier.

## Surfaces clés livrées

1. **Sidebar** — claire, active muted brand, collapsible, Lucide cohérent
2. **Header** — recherche, dark toggle, identité, notifications
3. **Dashboard** — KPI + sparklines, quick actions
4. **Auth** — panneau sombre + formulaires aérés (première impression)
5. **Table / forms** — `table-shell`, inputs focus brand

## Dark mode

Classe `.dark` sur `<html>` (boot script + toggle Header, `localStorage gs-theme`).
Overrides composants dans `index.css` (`.dark .card`, `.sidebar-premium`, etc.).
