# Design System — Gestion Scolaire Premium SaaS (v2)

## Direction

Identité **SaaS B2B premium** inspirée Metric Flow / Wise / Zence / Linear, adaptée éducation UEMOA/CEMAC.
Un seul accent (pétrole) — pas de jaune/rose Dribbble décoratif.

## Choix (1 phrase)

| Décision | Pourquoi |
|---|---|
| Brand pétrole `#0F766E` | Accent unique crédible ; featured KPI = fill brand (comme Wise jaune, mais sobre) |
| Fond `#F4F6F9` / dark `#070B14` | Neutre froid aéré ; dark = surfaces élevées |
| Plus Jakarta Sans + `text-kpi` | Valeur KPI dominante, labels uppercase discrets |
| Radius card `16px` / input `10px` / badge pill | Langage 2025, coins cohérents |
| Ombres soft + ring 1px | Élévation sans drop-shadow dur |
| Accents sémantiques seuls | Vert / ambre / rose = statut uniquement |
| Motion 150–250ms | Hover lift discret (−2px) |

## Tokens

Voir `frontend/tailwind.config.js` — legacy `or-cachet` → pétrole.

## Surfaces

1. Sidebar claire + `nav-item-active` (pill + barre gauche)
2. KPI Metric Flow (label → valeur → pill + sparkline)
3. Une carte featured brand pour ancrer le regard
4. Charts pétrole (donut monochrome teal)
5. Dark mode composants (pas d’inversion brute)
