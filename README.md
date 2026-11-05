# TOEIC Lab

Application personnelle d'entraînement à l'anglais : cours, exercices Reading, vocabulaire et progression. Démonstration : [ouvrir TOEIC Lab](https://eliasbellouti.com/demos/toeic/TOEIC_Lab.html).

Adresse de secours indépendante du serveur domestique : [TOEIC Lab sur GitHub Pages](https://skeeder1.github.io/toeic-lab/TOEIC_Lab.html). Chaque adresse conserve sa progression séparément ; utiliser l'export/import JSON pour la transférer.

Adaptation d'une application HTML fournie sous forme de ZIP. Les ajouts portent sur les expressions complètes, leurs sens dans le contexte anglais, l'ergonomie mobile et la mémorisation anonyme dans le navigateur. Ce projet n'est pas affilié à ETS et ne délivre pas de score officiel TOEIC.

## Utilisation

Avec Python 3, lancer `python3 -m http.server 8765 --bind 127.0.0.1` dans ce dossier, puis ouvrir <http://127.0.0.1:8765/TOEIC_Lab.html>. Aucun compte, dépendance réseau ou compilation nécessaire.

Survoler ou toucher un mot affiche une petite bulle de traduction. Une expression comme **take off** reste reconnue en entier, avec le sens suggéré par la phrase et cette proposition à la place du trou. Une case numérotée apparaît uniquement lorsqu’il existe plusieurs sens et ouvre leur liste : 57 expressions, 140 sens, exemples et sources. Un mot avec un seul sens ne porte pas de case « 1 ». Le contexte anglais seul sert à suggérer un sens ; une ambiguïté reste signalée.

Le bilan présente d’abord la note et son enregistrement, puis les erreurs à revoir. Les bonnes réponses et les notions travaillées se déplient à la demande. Une estimation de parcours n’est affichée que si ses compteurs ont réellement évolué ; elle ne représente pas des points TOEIC.

## Progression et confidentialité

Le panneau **Mémoriser sur cet appareil** propose de garder la séance, les réponses et les mots dans le stockage local du navigateur, avec un identifiant aléatoire local. Il n'utilise aucun cookie ni compte et n'envoie pas les réponses au serveur. En mode temporaire, les nouvelles réponses sont perdues au rechargement ou à la fermeture de la page ; les anciennes sauvegardes restent intactes.

La mémorisation dépend du domaine, de l'appareil et du profil du navigateur. Utiliser l'export JSON de **Progression** pour une copie de sécurité ou pour transférer les données depuis localhost vers la démonstration publique. La restauration remplace les données locales ; elle ne les fusionne pas.

Cette édition publique ne contient pas les résultats personnels intégrés à l'édition locale ni les sauvegardes privées. L'hébergement du portfolio reste soumis à sa propre infrastructure et à ses journaux d'accès.

## Fichiers

Conserver `TOEIC_Lab.html` et les six fichiers JS/CSS du dossier ensemble. `session-visiteur.js` doit être chargé avant tout script d'application. `mobile.css` est chargé à la fin pour compléter les styles intégrés.

## Vérifications

Les vérifications utilisent des profils de navigateur jetables : affichage et interactions tactiles dans six formats, expressions et sens, export, consentement, conservation après fermeture, refus et conflits entre onglets. Chromium/Brave sont vérifiés ; Safari réel n'a pas été validé.
