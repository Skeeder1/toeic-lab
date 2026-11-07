# TOEIC Lab

Application personnelle d'entraînement à l'anglais : cours, exercices Reading, vocabulaire et progression. Démonstration : [ouvrir TOEIC Lab](https://eliasbellouti.com/demos/toeic/TOEIC_Lab.html).

Adresse de secours indépendante du serveur domestique : [TOEIC Lab sur GitHub Pages](https://skeeder1.github.io/toeic-lab/TOEIC_Lab.html). Chaque adresse conserve sa progression séparément ; utiliser l'export/import JSON pour la transférer.

Adaptation d'une application HTML fournie sous forme de ZIP. Les ajouts portent sur les expressions complètes, leurs sens dans le contexte anglais, l'ergonomie mobile et la mémorisation anonyme dans le navigateur. Ce projet n'est pas affilié à ETS et ne délivre pas de score officiel TOEIC.

## Utilisation

Avec Python 3, lancer `python3 -m http.server 8765 --bind 127.0.0.1` dans ce dossier, puis ouvrir <http://127.0.0.1:8765/TOEIC_Lab.html>. Aucun compte, dépendance réseau ou compilation nécessaire.

Survoler un mot affiche une petite bulle de traduction. Cliquer ou toucher un mot, dans la phrase **ou dans un choix**, ouvre sa fiche avec **Ajouter à Mes mots**, sans sélectionner la réponse. Une expression comme **take off** reste reconnue en entier, avec le sens suggéré par la phrase et cette proposition à la place du trou. Une case numérotée apparaît uniquement lorsqu’il existe plusieurs sens et ouvre leur liste : 73 expressions, 192 sens, exemples et sources. Un mot avec un seul sens ne porte pas de case « 1 ». Le contexte anglais seul sert à suggérer un sens ; une ambiguïté reste signalée.

L’exercice garde une seule commande **Traduire la phrase**. La correction présente la bonne réponse, une explication et un accès au cours, sans traduction automatique répétée ni encadrés imbriqués. Les indications de survol, les boutons de traduction des choix et les badges techniques ont été retirés.

Le bilan présente d’abord la note et son enregistrement, puis les erreurs à revoir. Les bonnes réponses et les notions travaillées se déplient à la demande. Une estimation de parcours n’est affichée que si ses compteurs ont réellement évolué ; elle ne représente pas des points TOEIC.

## Progression et confidentialité

L’avatar dans l’en-tête ouvre **Ma progression**, **Mes mots**, **Modifier mon profil** et **Mes données**. Le nom, la couleur et une photo facultative restent locaux et suivent l’export/import JSON. Naviguer vers la progression pendant un exercice met la séance en pause pour la reprendre ensuite.

Le panneau **Garder ma progression** propose de garder la séance, les réponses et les mots dans le stockage local du navigateur, avec un identifiant aléatoire local. Il n'utilise aucun cookie ni compte et n'envoie pas les réponses au serveur. En mode temporaire, les nouvelles réponses sont perdues au rechargement ou à la fermeture de la page ; les anciennes sauvegardes restent intactes.

La mémorisation dépend du domaine, de l'appareil et du profil du navigateur. Utiliser l’export JSON dans **Profil → Mes données** ou **Progression → Sauvegardes et transferts** pour une copie de sécurité ou pour transférer les données depuis localhost vers la démonstration publique. La restauration remplace les données locales ; elle ne les fusionne pas.

Cette édition publique ne contient pas les résultats personnels intégrés à l'édition locale ni les sauvegardes privées. L'hébergement du portfolio reste soumis à sa propre infrastructure et à ses journaux d'accès.

## Fichiers

Conserver `TOEIC_Lab.html` et les douze fichiers JS/CSS du dossier ensemble. `session-visiteur.js` doit être chargé avant tout script d'application. `mobile.css` est chargé à la fin pour compléter les styles intégrés.

## Vérifications

Les vérifications utilisent des profils de navigateur jetables : affichage et interactions tactiles dans six formats, expressions et sens, export, consentement, conservation après fermeture, refus et conflits entre onglets. Chromium/Brave sont vérifiés ; Safari réel n'a pas été validé.

## Variété des questions de Part 5

Le TOEIC Part 5 ciblé donne priorité aux énoncés inédits compatibles avec le parcours, avant les quotas de notions. Les questions déjà affichées sont suivies même sans réponse ; les séances en pause et leurs files restent réservées. Les anciens identifiants sont reconnus. Après épuisement du stock compatible, la rotation reprend les questions vues les plus anciennes. Les variantes très proches des modèles générés passent après les formulations nouvelles.

La banque ciblée comprend 120 nouvelles questions originales. Les métadonnées d’exposition suivent le consentement local et l’export/import JSON, sans modifier les anciennes réponses ni la notation.

## TOEIC blanc, Partie 5

L’accueil distingue **TOEIC Part 5 ciblé** et **TOEIC blanc**. La bibliothèque blanche couvre uniquement la **Partie 5**, avec dix tests fixes de trente questions originales chacun, numérotées 101 à 130. Elle ne simule pas les sept parties du TOEIC Listening and Reading et ne produit pas de conversion sur 990.

Chaque test permet de passer une question, revenir dessus et modifier ses choix. Les aides et traductions restent désactivées pendant le blanc. Les réponses restent provisoires jusqu’à la confirmation finale ; les questions laissées vides comptent alors fausses. La pause, la reprise et l’export/import conservent l’ordre et les choix. Les énoncés blancs restent séparés du stock ciblé. Refaire volontairement un test conserve son énoncé et son ordre.

La répartition des 300 questions originales suit le classement principal de 300 questions relevées dans dix sujets distincts fournis :

| Type principal | Questions | Part |
| --- | ---: | ---: |
| Vocabulaire et collocations | 102 | 34 % |
| Formes de mots | 65 | 21,7 % |
| Verbes, temps, voix et accords | 43 | 14,3 % |
| Prépositions | 30 | 10 % |
| Conjonctions et liaisons | 29 | 9,7 % |
| Déterminants, articles et pronoms | 23 | 7,7 % |
| Relatifs et autres constructions | 8 | 2,7 % |

Cette répartition est observée dans cet échantillon, pas imposée par ETS. Les questions sont originales, relues, et non étalonnées comme un test officiel. Les PDF de référence et les données personnelles restent hors du dépôt public. Le [format officiel décrit par ETS Global](https://www.etsglobal.org/fx/en/help-center/test-content/format-questions-toeic-listening-reading) couvre l’ensemble du test ; cette application entraîne ici la Partie 5.

## Interface et navigation

L’accueil donne directement accès au **TOEIC ciblé** et au **TOEIC blanc**, limités à la Partie 5, puis aux cinq matières de révision. Les tests blancs se filtrent par état : à faire, en pause ou terminés. Le compteur et la grille vont de 1 à 30 ; les références 101 à 130 restent conservées dans les questions.

Dans **Mes mots**, la révision et la recherche passent avant les lexiques facultatifs et les transferts CSV, regroupés dans une section repliable. Dans **Ma progression**, les filtres séparent le ciblé, les blancs et les autres exercices. Les indicateurs portent sur les séances terminées du filtre actif et le graphique affiche leurs pourcentages de bonnes réponses, sans score TOEIC converti.

Naviguer vers l’accueil ou les mots pendant une séance utilise la pause existante. Les fiches conservent l’écran de départ ; un blanc est mis en pause avant leur ouverture. Le clavier garde sa place après les actions et les dialogues : Échap ferme l’éditeur sans enregistrer, les onglets répondent aux flèches et les champs ont des libellés accessibles. Les trois fichiers `interface.css`, `interface-accessible.js` et `interface.js` se chargent après les modules d’exercices ; ils ne changent ni le format des données ni les moteurs d’apprentissage.
