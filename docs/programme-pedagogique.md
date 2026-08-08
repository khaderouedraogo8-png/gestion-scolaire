# PROGRAMME PÉDAGOGIQUE — DEVOIRS, COMPOSITIONS, PROGRAMME ENSEIGNANTS
### Spécification fonctionnelle et technique

---

## 1. CORRECTION RAPIDE — VISIBILITÉ DU MOT DE PASSE

Sur l'écran de connexion (et partout où un champ mot de passe existe : changement de mot de passe, réinitialisation) : ajouter une icône œil (Lucide `Eye` / `EyeOff`) à l'intérieur du champ, à droite, qui bascule `type="password"` ↔ `type="text"` au clic. Comportement standard, aucune logique serveur à toucher.

---

## 2. PROGRAMME DES DEVOIRS

### Principe
Chaque classe a un programme récurrent : quels jours de la semaine, pour quelle matière, un devoir est attendu. Ex : 6ème A — Mathématiques le mardi soir, Français le vendredi soir.

### Schéma
```sql
CREATE TABLE programme_devoir (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_classe         UUID NOT NULL REFERENCES classe(id) ON DELETE CASCADE,
    id_matiere        UUID NOT NULL REFERENCES matiere(id) ON DELETE CASCADE,
    jour_semaine      SMALLINT NOT NULL CHECK (jour_semaine BETWEEN 1 AND 7),
    frequence         VARCHAR(20) DEFAULT 'hebdomadaire' CHECK (frequence IN ('hebdomadaire', 'quinzomadaire')),
    note              VARCHAR(255),
    id_annee          UUID NOT NULL REFERENCES annee_scolaire(id) ON DELETE CASCADE,
    UNIQUE (id_classe, id_matiere, jour_semaine, id_annee)
);
```

### Écran
`/classes/:cycle/:classe` → nouvel onglet **Devoirs** : tableau jour de la semaine × matière, édition inline pour l'administration/enseignants concernés. Vue lecture seule pour les parents (limitée à la classe de leur enfant).

### Lien avec l'existant
Ce n'est pas une évaluation datée (`evaluation`/`note` existent déjà pour ça) — c'est un **planning récurrent**, la référence que les parents et élèves consultent pour savoir "qu'est-ce qui est dû ce soir". Un enseignant peut ensuite créer une `evaluation` de type `devoir` un jour donné, indépendamment de ce planning — le programme est indicatif, pas contraignant.

---

## 3. PROGRAMME DES COMPOSITIONS

### Principe
Une composition = `evaluation` avec `type_evaluation = 'examen'` — la structure de données existe déjà. Ce qui manque : une **vue calendrier dédiée**, par classe et par trimestre, et un statut de publication.

### Changement minimal
```sql
ALTER TABLE evaluation ADD COLUMN statut_publication VARCHAR(20) DEFAULT 'brouillon'
    CHECK (statut_publication IN ('brouillon', 'publie'));
```
Une composition en `brouillon` n'est visible que par l'administration/enseignants. Une fois `publie`, elle apparaît dans le programme consulté par élèves/parents — évite qu'une date encore provisoire soit communiquée trop tôt.

### Écran
`/classes/:cycle/:classe` → onglet **Compositions** : liste des évaluations de type `examen` de cette classe, groupées par trimestre, avec date, matière, coefficient. Bouton "Publier" pour les faire apparaître côté parent. Génération PDF du calendrier des compositions du trimestre (même moteur WeasyPrint que les bulletins).

**Hypothèse retenue** : le système reste organisé par trimestre (c'est déjà le modèle en place). Si un autre établissement utilisant ce même système fonctionnait par semestre, ce serait une extension séparée (renommage/config de la structure trimestre → période), pas nécessaire pour ton établissement actuel.

---

## 4. PROGRAMME DES ENSEIGNANTS

### Principe
Une vue consolidée, par enseignant : ses classes, ses matières, son volume horaire, son emploi du temps. Les données existent déjà (`enseignant`, `affectation_enseignant`, `creneau_emploi_temps`) — il s'agit surtout d'une page de synthèse qui n'existe pas encore.

### Écran
Nouvelle page `/emploi-temps/enseignants/:id` (fiche détail, actuellement seule la liste existe) :
- En-tête : nom, spécialité, contrat, volume horaire hebdomadaire total (somme de ses affectations).
- Tableau des affectations : classe, matière, volume horaire/semaine.
- Emploi du temps hebdomadaire visuel (grille jour × heure, réutilise les données de `creneau_emploi_temps`).
- Bouton "Imprimer la fiche" → PDF (nom, classes, horaires — utile en salle des professeurs).

---

## 5. IMPRESSION — PRINCIPE GÉNÉRAL

Tu as raison de le poser comme exigence transversale : **tout ce qui remplaçait un document papier doit être imprimable**. Liste des documents PDF à couvrir (au-delà de ceux déjà prévus — bulletins, reçus, attestations, cartes) :
- Programme des devoirs d'une classe (le tableau jour × matière)
- Calendrier des compositions d'un trimestre, par classe
- Fiche enseignant (programme + horaires)
- Liste des élèves d'une classe (utile en début d'année, pour l'appel)
- Liste d'émargement pour une composition (élève / présent / absent / signature)

Tous générés via le même moteur WeasyPrint déjà en place, gabarits ajoutés dans `backend/app/templates_pdf/`.

---

## 6. FICHES DE CLASSE IMPRIMABLES

### Principe
Trois documents distincts, générés depuis l'onglet d'une classe, réutilisant les données déjà en base — aucun nouveau modèle de données requis pour la scolarité et l'appel, un ajout mineur pour la fiche de correction.

### 6.1 Fiche de correction (feuille vierge pour l'enseignant)
Liste des élèves de la classe (nom, matricule) avec une colonne vide "Note /20" — l'enseignant l'imprime avant de corriger à la main, la remplit, la remet à l'administration qui saisit ensuite dans `Saisie des notes`. Générée depuis l'onglet **Notes & Bulletins** d'une classe, en sélectionnant l'évaluation concernée (pour que l'en-tête indique matière/coefficient/date).

### 6.2 Fiche d'appel (présence)
Liste des élèves avec colonnes Présent / Absent / Retard / Signature, pour une date donnée. Générée depuis l'onglet **Absences** d'une classe. Sert aussi de justificatif papier archivable en cas de contestation.

### 6.3 Fiche de situation de scolarité
Liste des élèves de la classe avec, pour chacun : total dû, montant payé, arriéré — pour une période/année scolaire donnée. Générée depuis l'onglet **Scolarité** d'une classe. C'est la vue par classe de ce qui existe déjà globalement dans `Finance > Arriérés`, simplement filtrée et mise en page pour impression.

Les trois réutilisent le même moteur PDF (WeasyPrint) déjà en place, avec un gabarit dédié par type dans `backend/app/templates_pdf/`.

---

## 7. PUBLICATION DES NOTES AUX PARENTS

### Principe
Un enseignant saisit les notes d'une évaluation au fur et à mesure de sa correction. Tant qu'il n'a pas terminé, ces notes restent invisibles côté parent — évite qu'une note provisoire ou une erreur de saisie en cours soit vue avant d'être finalisée. Une fois la saisie terminée, l'enseignant clôture explicitement l'évaluation, ce qui la rend visible aux parents concernés.

### Schéma
```sql
ALTER TABLE evaluation ADD COLUMN statut_saisie VARCHAR(20) NOT NULL DEFAULT 'en_cours'
    CHECK (statut_saisie IN ('en_cours', 'cloturee'));
```

### Comportement
- Tant que `statut_saisie = 'en_cours'` : les notes de cette évaluation ne sont retournées par l'API que pour les rôles administration/enseignant — jamais pour le rôle `parent` (filtrage serveur, comme le reste du RBAC parent déjà spécifié).
- Bouton **"Clôturer et publier"** sur l'écran de saisie des notes (visible une fois que toutes les notes de la classe sont entrées, ou à tout moment si l'enseignant veut publier un sous-ensemble déjà correct) → passe `statut_saisie` à `cloturee`.
- Dès la clôture : déclenche une notification automatique aux parents concernés (réutilise le Module 7 déjà en place) — cohérent avec la même mécanique déjà prévue pour la publication des compositions (§3) et des bulletins.
- Un enseignant peut rouvrir une évaluation clôturée pour corriger une erreur (repasse en `en_cours`, republie ensuite) — action tracée dans `journal_audit`.

---

## 8. PISTES D'AMÉLIORATION PROPOSÉES

Tu as demandé des idées — voici ce qui manque encore pour un système vraiment complet, dans l'esprit de ce que tu décris :

1. **Calendrier scolaire de l'établissement** : jours fériés, vacances, rentrée, examens officiels — un calendrier global qui alimente automatiquement les trimestres (dates de début/fin déjà en base) et bloque la programmation de devoirs/compositions sur les jours fériés.
2. **Cahier de texte numérique** : au-delà du simple programme de devoirs, un enseignant pourrait consigner, après chaque cours, ce qui a été vu (contenu de la séance) — trace pédagogique consultable par la direction et les parents, remplace le cahier de texte papier traditionnel dans les écoles francophones.
3. **Listes d'appel imprimables** en début d'année et à chaque rentrée de trimestre (déjà mentionné en §5, je le remets ici car c'est un vrai gain de temps administratif).
4. **Notification automatique aux parents** quand une composition passe de `brouillon` à `publie`, ou quand le programme de devoirs d'une classe est modifié — réutilise le système de notifications déjà en place (Module 7).
5. **Statistiques de charge de travail** : nombre de devoirs/compositions programmés par classe et par semaine, pour repérer si une classe est surchargée un jour donné (ex. 3 matières qui tombent toutes le même vendredi) — utile à la direction pédagogique pour arbitrer.
6. **Export du programme trimestriel complet** (devoirs + compositions + emploi du temps) en un seul document PDF par classe — le document que tu remettrais physiquement aux élèves/parents en début de trimestre.

Je ne les inclus pas tous dans le prompt Cursor immédiat (ça ferait un chantier trop large d'un coup) — dis-moi lesquels de ces 6 points tu veux prioriser en plus des §1 à 5 déjà spécifiés, et je les ajoute au prompt.
