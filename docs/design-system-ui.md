# SYSTÈME DE DESIGN — GESTION SCOLAIRE
### Identité "sceau institutionnel" — spécification complète pour implémentation

---

## 1. PRINCIPE DIRECTEUR

Ce produit délivre des documents officiels (bulletins visés, attestations, cartes avec QR signé) et gère de l'argent. L'identité visuelle s'appuie sur ça : un sceau/cachet institutionnel, pas une esthétique de start-up générique. Sobre, dense en données, mais avec un vrai point de caractère.

---

## 2. COULEURS (valeurs exactes)

| Nom | Hex | Usage |
|---|---|---|
| `encre` | `#14213D` | Sidebar, texte principal, titres |
| `encre-clair` | `#1F3A5F` | Hover sidebar, éléments secondaires foncés |
| `or-cachet` | `#B8862E` | Accent unique — boutons primaires, liens actifs, soulignés de stats, motif sceau |
| `or-cachet-clair` | `rgba(184,134,46,0.12)` | Fond des états actifs/sélectionnés |
| `craie` | `#F6F5F1` | Fond de page (remplace le blanc plat actuel) |
| `blanc` | `#FFFFFF` | Fond des cartes |
| `bordure` | `#E4E2D9` | Bordures fines (1px, jamais d'ombre portée lourde) |
| `texte-secondaire` | `#6B6D6A` | Labels, sous-titres, texte muet |
| `feuille` | `#2F6E4F` | Succès, statuts positifs (remplace le vert Tailwind par défaut) |
| `feuille-clair` | `#E7F0EA` | Fond des badges succès |
| `brique` | `#A6432E` | Erreur, alertes, montants dus (remplace le rouge Tailwind par défaut) |
| `brique-clair` | `#F5E8E4` | Fond des badges erreur |
| `ambre` | `#B8862E` | Avertissement (même famille que l'accent — pas d'ambre Tailwind générique) |
| `ambre-clair` | `#F7EEDD` | Fond des badges avertissement |

**Règle stricte** : plus aucune couleur Tailwind par défaut (`indigo-600`, `red-500`, `green-500`, `yellow-400` etc.) ne doit apparaître dans le code. Tout passe par ces tokens, déclarés comme variables CSS custom (`--color-encre`, `--color-or-cachet`, etc.) dans `tailwind.config.js` sous `theme.extend.colors`.

---

## 3. TYPOGRAPHIE

- **Display** (titres de page, gros chiffres des cartes stat) : **Fraunces** (Google Fonts, variable, optical sizing). Poids 500 pour les titres, 500 pour les chiffres.
- **UI/corps** (tout le reste — labels, tableaux, formulaires, navigation) : **Public Sans**. Poids 400 (texte courant) et 500 (emphase, jamais de 700 — trop lourd).
- **Données numériques** (montants FCFA, matricules, numéros de reçu) : Public Sans avec `font-variant-numeric: tabular-nums` pour l'alignement en colonne — critique pour les tableaux financiers (arriérés, encaissements).

Import dans `index.html` ou via `@fontsource` :
```
Fraunces: opsz 9..144, wght 400;500;600
Public Sans: wght 400;500;600
```

---

## 4. COMPOSANTS

### Sidebar
- Fond `encre` (`#14213D`), texte `craie` à 70% d'opacité pour les liens inactifs, `craie` plein pour le lien actif.
- Lien actif : bordure gauche 2px `or-cachet`, fond `or-cachet-clair`, coins arrondis côté droit uniquement (0 8px 8px 0).
- Logo : remplacer le carré arrondi "GS" actuel par un **médaillon circulaire** — cercle 28px, liseré 1.5px `or-cachet`, fond transparent, initiales en Fraunces 12px couleur `or-cachet`. C'est l'élément signature — il doit réapparaître identique sur l'écran de connexion (en grand, 64px) et comme micro-icône de confirmation quand un document/bulletin est validé.
- Icônes de navigation : remplacer les emoji actuels (🎓💰📋🔔) par des icônes **Lucide React** (déjà dans les dépendances frontend autorisées), trait fin, 18px, couleur héritée du texte du lien. Mapping suggéré : `LayoutDashboard`, `GraduationCap`, `FileText`, `Wallet`, `Calendar`, `ClipboardList`, `FolderOpen`, `Bell`, `Settings`.

### Cartes (stat cards du dashboard, cartes de contenu)
- Fond `blanc`, bordure 1px `bordure`, coins 8px, **jamais d'ombre portée** — juste la bordure fine.
- Carte stat : label 11px `texte-secondaire` en haut, chiffre 26px Fraunces 500 en dessous, puis un **soulignement de 24px de large, 2px de haut**, coloré selon le sens de la donnée (or-cachet = neutre, feuille = positif, brique = négatif/alerte). C'est la signature visuelle des chiffres clés.

### Tableaux (élèves, arriérés, notifications, notes)
- Pas de zébrage (lignes alternées) — bordure basse 0.5px `bordure` entre les lignes seulement.
- En-têtes de colonnes : 11px, majuscules, `texte-secondaire`, `letter-spacing: 0.03em`.
- Colonnes monétaires : alignées à droite, `tabular-nums`.
- Badges de statut (inscrit/abandon, en attente/envoyé, justifiée/non justifiée) : fond `-clair` de la couleur sémantique correspondante, texte plein de la même famille, coins 4px (pas de pilule complète), padding 2px 8px.

### Formulaires
- Champs : bordure 1px `bordure` au repos, `or-cachet` au focus (pas de bleu Tailwind par défaut), coins 6px.
- Bouton primaire : fond `encre`, texte `craie`, hover `encre-clair`. **Un seul bouton primaire par écran** — les actions secondaires restent en style outline (bordure `bordure`, fond transparent).
- Erreurs de validation : texte `brique`, jamais de fond rouge plein sur le champ lui-même — juste une bordure `brique` et un message sous le champ.

### États vides et erreurs (copie à revoir, pas seulement le style)
Le ton actuel est correct mais mécanique. Reformuler selon ces règles :
- Un état vide est une invitation, pas une excuse. "Aucun bulletin" → **"Aucun bulletin pour l'instant"** + sous-ligne actionnable déjà présente, c'est bien — garder ce pattern partout où c'est manquant (ex: Documents, Enseignants).
- Une erreur dit ce qui s'est passé et quoi faire, jamais en double, jamais générique. Le bug des deux toasts identiques "Erreur chargement enseignants" (voir §6) doit devenir un seul message : **"Impossible de charger les enseignants. Réessayer."** avec un bouton d'action, pas juste un texte qui disparaît.

### Page de connexion
- Garder la structure deux colonnes actuelle (bon choix), mais :
  - Colonne gauche : fond `encre` uni (pas de dégradé indigo actuel — les dégradés sont à bannir de toute l'interface), médaillon-sceau 64px centré verticalement avec le nom en Fraunces.
  - Colonne droite : fond `craie`, champs et bouton selon §4 Formulaires.

---

## 5. RESPONSIVE / MOBILE

- Corriger le bug d'overlay du menu mobile (voir §6) : le fond semi-transparent doit couvrir toute la hauteur du contenu scrollable, pas une hauteur fixe `100vh` qui se désynchronise du scroll.
- Cartes stat du dashboard mobile : conserver l'empilement vertical actuel (déjà correct), juste appliquer la nouvelle palette/typo.

---

## 6. BUGS À CORRIGER DANS LA MÊME PASSE

1. **Page Enseignants** : double toast d'erreur identique au chargement — probablement un double appel API (`useEffect` déclenché deux times). Corriger la cause, pas juste dédupliquer l'affichage du toast.
2. **Overlay menu mobile** : se désynchronise du scroll sur la page Élèves (voir capture fournie), grisant certaines lignes et pas d'autres. Corriger la hauteur de l'overlay pour qu'elle suive le contenu réel.

---

## 7. PORTÉE

Cette identité s'applique à **toutes les pages** listées dans l'arborescence frontend : dashboard, élèves (liste + fiche détail), notes (évaluations, saisie, bulletins), finance (frais, encaissement, arriérés, reçus), emploi du temps (enseignants, créneaux, affectations, salles), absences et discipline, documents, notifications, configuration (établissement, années, trimestres, niveaux, classes, matières, coefficients, utilisateurs, journal audit), et le portail parent s'il existe déjà.

Aucune page ne doit rester dans l'ancien style indigo générique après cette passe.
