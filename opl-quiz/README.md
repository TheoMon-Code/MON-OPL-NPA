# MON NPA — OPL Quiz

PWA de quiz quotidien pour les employés de l'entrepôt (MON Transport / NPA).
Les employés se connectent avec leur badge et répondent à 3 questions sur les
KSR/OPL/WI de leur département. Les managers ont un dashboard (résultats,
streaks, skill matrix, gestion des employés, banque de questions).

## Stack

- **Front** : `index.html` unique (vanilla JS, bilingue EN/TH), PWA (`sw.js`, `manifest.json`)
- **Base de données** : Supabase (PostgREST, clé anon) — 3 tables : `employees`, `questions`, `quiz_results`
- **Hébergement** : Netlify (+ 1 fonction planifiée)

## Structure

```
index.html                       # Toute l'app (UI + logique)
sw.js                            # Service worker (network-first)
manifest.json                    # PWA
netlify.toml                     # Publish, redirects, cache headers
netlify/functions/keep-alive.mjs # Ping quotidien Supabase (anti-pause plan gratuit)
supabase/schema.sql              # Schéma complet de la base
```

## Déploiement

1. **Supabase** : créer un projet, exécuter `supabase/schema.sql` dans le SQL Editor
2. **index.html** : renseigner `SURL` et `SKEY` (bloc "SUPABASE CLIENT")
3. **Netlify** : connecter ce repo (build command : aucune, publish : `.`)
4. **Variables d'environnement Netlify** (pour keep-alive) :
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`

## Gestion du contenu

- **Employés** : dashboard manager → Employees → import Excel (Badge, Name, Department, Position, Shift, Role)
- **Questions** : dashboard manager → Questions → import Excel (template téléchargeable), puis validation dans la Question Bank
- **Mot de passe manager** : constante `MGR_PASSWORD` dans `index.html`

## Notes

- Après toute modification d'`index.html`, incrémenter la version du cache dans `sw.js` (`mon-npa-vX`)
- Le plan gratuit Supabase met en pause les projets inactifs ~7 jours ; la fonction `keep-alive` (cron quotidien) l'empêche
