# Guide utilisateur — Gestion Scolaire

Guide rapide pour l'administrateur et les principaux rôles.

---

## 1. Première connexion

1. Ouvrir l'URL de l'application (ex. `https://ecole.votredomaine.fr`)
2. Se connecter avec le compte administrateur
3. **Changer le mot de passe** immédiatement (Configuration → Utilisateurs → votre compte)
4. Paramétrer l'établissement (nom, adresse, format matricule)

---

## 2. Configuration initiale (admin)

Ordre recommandé :

1. **Configuration → Années scolaires** — créer/activer l'année en cours
2. **Configuration → Trimestres** — vérifier les dates
3. **Configuration → Niveaux & Classes** — créer les classes par niveau
4. **Configuration → Matières & Coefficients** — matières et coefs par niveau
5. **Configuration → Frais scolaires** — montants et échéances par niveau
6. **Configuration → Utilisateurs** — comptes personnel et parents
7. **Emploi du temps → Enseignants** — fiches enseignants + lien compte utilisateur

---

## 3. Parcours par rôle

### Secrétariat — Inscrire un élève

1. **Élèves → Nouvel élève** — identité, photo, parents
2. **Inscription** — choisir classe et année, statut « inscrit »
3. **Documents** — carte scolaire, attestations si besoin

### Enseignant — Saisir des notes

1. **Notes & Bulletins → Évaluations** — créer une évaluation (classe, matière, trimestre)
2. **Saisie des notes** — saisir par élève (0–20 ou absent)
3. Les moyennes se calculent automatiquement

### Directeur — Publier un bulletin

1. **Notes & Bulletins → Bulletins** — générer en brouillon
2. Vérifier appréciations et moyennes
3. **Valider** puis **Publier** — visible par les parents

### Comptable — Encaisser un paiement

1. **Finance → Encaissement** — sélectionner élève, montant, mode
2. Un **reçu PDF** est généré (numéro unique)
3. **Finance → Arriérés** — suivi des impayés, relances parents

### Parent — Consulter

1. Connexion portail parent
2. Voir : notes/bulletins, paiements, absences de ses enfants uniquement

---

## 4. Notifications

Les notifications (absence, bulletin publié, arriérés) passent par une **file d'attente**.

- Emails : configurer `SMTP_*` dans `.env.prod`
- SMS : configurer `SMS_API_URL` (optionnel)
- Traitement automatique : cron `flask traiter-notifications` (toutes les 15 min)

---

## 5. Sauvegardes

- **Automatique** : cron quotidien 2h (`scripts/install-cron.sh`)
- **Manuelle** : `docker compose --profile backup run --rm backup`
- **Restauration** : `./scripts/restore-db.sh backups/fichier.sql.gz`
- Tester une restauration **au moins une fois par trimestre**

---

## 6. Dépannage courant

| Problème | Action |
|----------|--------|
| Mot de passe oublié | « Mot de passe oublié » sur la page login |
| Compte bloqué (5 échecs) | Admin → Utilisateurs → débloquer |
| PDF ne s'ouvre pas | Vérifier pop-ups navigateur |
| Parent ne voit pas son enfant | Vérifier lien parent ↔ élève (fiche élève) |

---

## 7. Support technique

- Logs backend : `docker compose logs backend`
- Health check : `GET /api/health` (doit retourner `{"status":"ok","redis":"ok"}`)
- Documentation déploiement : [deploy/DEPLOIEMENT.md](../deploy/DEPLOIEMENT.md)
