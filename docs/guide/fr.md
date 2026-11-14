# Guide Datum Plot

## Bienvenue

Datum Plot est un logiciel pour Windows qui analyse des données scientifiques et produit des graphiques prêts à publier. Vous saisissez, collez ou importez vos données dans un tableau, vous choisissez une analyse, et Datum Plot affiche les résultats accompagnés d’une conclusion en langage simple, trace le graphique et met en page la figure pour une revue, un poster ou une diapositive. Tout reste lié : modifiez une valeur du tableau, et chaque résultat et chaque graphique qui l’utilisent se mettent à jour.

Les calculs et les tracés sont réalisés par Python (numpy, SciPy et matplotlib), intégré à l’application. Rien d’autre n’est à installer, et vos données ne quittent jamais votre ordinateur.

Ce guide vous accompagne pas à pas dans Datum Plot, de l’installation jusqu’à la figure exportée. Inutile de le lire d’une traite : chaque chapitre se suffit à lui-même.

Comment lire ce guide :

- L’interface de Datum Plot est en anglais. Les noms en **gras** sont les onglets, boutons et champs tels qu’ils apparaissent dans Datum Plot, suivis de leur sens en français entre parenthèses, par exemple **Test Chooser** (Choix du test). Il suffit de chercher le nom anglais dans le logiciel.
- Une flèche › indique un chemin : **Analyze › Test Chooser** (Analyser › Choix du test) signifie l’onglet **Analyze**, puis le bouton **Test Chooser**.
- Les touches sont notées ainsi : [[Ctrl+S]].
- Les numéros orange sur les images correspondent aux listes numérotées placées en dessous.

> **Astuce.** Presque chaque outil de Datum Plot a un petit **?** à côté de son nom. Cliquez dessus pour ouvrir une courte fiche qui explique à quoi sert l’outil et comment l’utiliser.

## Installer, mettre à jour et démarrer

### Installation

1. Téléchargez `DatumPlot-x.y.z-setup.exe` depuis la page des versions (Releases) : github.com/Edgar-Mendonca/Datum-Plot/releases.
2. Lancez-le. Il s’installe pour votre propre compte Windows : les droits d’administrateur ne sont pas nécessaires.
3. La première fois, Windows peut afficher **Windows protected your PC** (Windows a protégé votre ordinateur), car le programme d’installation n’est pas encore signé. Cliquez sur **More info** (Informations complémentaires), puis sur **Run anyway** (Exécuter quand même).

Le premier démarrage prend un peu plus de temps, le temps que Datum Plot prépare son moteur Python. La barre d’état indique **Ready** (Prêt) une fois le moteur démarré.

### Mises à jour

Datum Plot recherche une nouvelle version à chaque démarrage. Lorsqu’une version est disponible, un bouton **Update x.y.z available** (Mise à jour x.y.z disponible) apparaît dans la barre de titre ; cliquez dessus, ou ouvrez **File › Updates** (Fichier › Mises à jour) et cliquez sur **Update now** (Mettre à jour maintenant). Le téléchargement est vérifié par sa somme de contrôle avant l’installation, puis Datum Plot redémarre tout seul. Vos projets ne sont pas modifiés.

![File › Updates : la version, la recherche de mises à jour et les liens vers GitHub.](img/updates.png)

### La page Home

![La page Home (File › Home).](img/home.png)

1. **Départs.** Datum Plot s’ouvre sur cette page. **Empty project** (Projet vide) : rien encore. **Blank XY table** (Tableau XY vide) : un tableau sans graphique, pour saisir et analyser des données seulement. **Blank XY table and graph** (Tableau XY et graphique vides) : le même avec son graphique. **Blank column table** (Tableau en colonnes vide) : des groupes côte à côte, sans graphique, pour les tests t et l’ANOVA. Un graphique peut être ajouté plus tard avec **Graph › New Graph** (Graphique › Nouveau graphique).
2. **Samples** (Exemples). Un dossier de petits projets complets, avec des données réalistes, une analyse et un graphique. Il s’ouvre dans la page Home, les exemples rangés sous des titres : courbes et régression, comparaison de groupes, survie et fiabilité, tests médicaux, signaux et analyse thermique, cartes et graphiques spéciaux. Ouvrez-en un pour voir à quoi ressemble un projet abouti, puis remplacez les données par les vôtres ; **← Home** ramène à l’accueil.
3. **La page File** (Fichier). **New** (Nouveau), **Open** (Ouvrir), **Import** (Importer), **Save** (Enregistrer), **Save As** (Enregistrer sous), **Export** (Exporter) et **Print** (Imprimer), et en dessous **Roadmap** (Feuille de route), **Options** (Options) et **Updates** (Mises à jour). La flèche en haut ramène au projet.

À côté se trouvent **Open** (Ouvrir), **Import data** (Importer des données), le **Guide** (ce guide, en anglais, en chinois ou en français) et la **Roadmap** (Feuille de route) ; plus bas, vos projets récents.

![Les exemples, sous leurs titres.](img/samples.png)

## La fenêtre en un coup d’œil

![La fenêtre de Datum Plot avec un graphique ouvert.](img/window.png)

1. **Onglets.** **File** (Fichier) ouvre la page Fichier. **Data** (Données), **Analyze** (Analyser), **Graph** (Graphique), **Layout** (Mise en page), **Tools** (Outils), **View** (Affichage) et **Help** (Aide) affichent chacun leur propre ruban.
2. **Ruban.** Les outils de l’onglet actif, rangés en groupes nommés. Quand la fenêtre est étroite (un écran de portable), les groupes se replient depuis la droite en un bouton portant leur nom, par exemple **Style ▾** : cliquez dessus pour ses commandes. Sur un écran peu haut, la page Fichier présente ses commandes en une colonne compacte.
3. **Barre latérale.** Permet de passer de la feuille **Info** (Informations) du projet aux **Data** (Données), **Results** (Résultats), **Graphs** (Graphiques) et **Layouts** (Mises en page).
4. **Navigator** (Navigateur). Tous les tableaux de données, résultats, graphiques et mises en page du projet, avec des miniatures des graphiques. Faites un clic droit sur un élément pour le renommer, le dupliquer ou le supprimer.
5. **L’élément ouvert.** Ici un graphique ; ce peut aussi être un tableau de données, une feuille de résultats ou une mise en page.

Le champ **Tell me what you want to do** (Dites-moi ce que vous voulez faire), en haut (ou [[Ctrl+K]]), trouve n’importe quelle commande par son nom : tapez « log axis » (axe logarithmique) ou « t-test » (test t) et appuyez sur [[Enter]].

### Comment un projet est lié

Un projet contient des tableaux de données, des analyses, des graphiques et des mises en page :

- Un **data table** (tableau de données) contient les nombres.
- Une **analysis** (analyse) lit un tableau de données et produit une **results sheet** (feuille de résultats).
- Un **graph** (graphique) trace un tableau de données et peut afficher les courbes et les étoiles de significativité de ses analyses.
- Une **layout** (mise en page) dispose des graphiques et du texte sur une page.

Quand vous modifiez une valeur, chaque résultat et chaque graphique qui en dépendent sont recalculés. Vous n’avez jamais besoin d’« actualiser ».

## Tableaux de données

### Types de tableau

Choisissez le type de tableau qui correspond à votre expérience : **Data › New Table** (Données › Nouveau tableau).

![Data › New Table : choisir un type de tableau.](img/new-table.png)

1. **Familles de tableaux.** Data tables (tableaux de données), et Worksheets and 3D (feuilles de calcul et 3D).
2. **Les types.** Cliquez sur un type pour lire à quoi il sert ; double-cliquez pour le créer.

| Type | Ce qu’il contient | Analyses typiques |
|---|---|---|
| **XY** | des valeurs X (temps, dose, déformation…) et des séries Y avec réplicats | régression, ajustement de courbe |
| **Column** (Colonnes) | chaque colonne est un groupe | tests t, ANOVA, Bland-Altman, ROC |
| **Grouped** (Groupé) | deux facteurs : les lignes et les séries de données | ANOVA à deux facteurs |
| **Contingency** (Contingence) | effectifs des issues par groupe | khi-deux, test exact de Fisher |
| **Survival** (Survie) | une ligne par sujet : le temps, et 1 (événement) ou 0 (censuré) | Kaplan-Meier, test du log-rank |
| **Parts of whole** (Parties d’un tout) | les parts d’un total | fractions, secteurs et anneaux |
| **Many variables** (Variables multiples) | une ligne par échantillon, de nombreuses propriétés | régression multiple, ACP, classification |
| **Nested** (Imbriqué) | des groupes avec sous-groupes (lots, animaux) | test t et ANOVA imbriqués |
| **Worksheet** (Feuille de calcul) | des colonnes libres avec rôles, unités et formules | données brutes d’instrument |
| **Matrix** (Matrice) | des valeurs Z sur une grille X–Y | cartes de contours, surfaces 3D, ajustements de surface |

### Saisir les données

![Un tableau de données (onglet Data).](img/table.png)

1. **Data › Insert** (Données › Insérer). **New Table** (Nouveau tableau), **Import** (Importer), **Several Files** (Plusieurs fichiers), **Digitize Graph** (Numériser un graphique), **Add Data Set** (Ajouter une série), **Remove Data Set** (Supprimer une série) et les lignes.
2. **En-têtes.** Le titre et les unités de X, et le titre de chaque série de données. Double-cliquez sur un en-tête pour le modifier, ainsi que les réplicats ou le mode de saisie des valeurs. Les titres longs passent à la ligne, sur trois lignes au plus. Faites glisser le bord droit d’un en-tête pour élargir sa colonne ; double-cliquez sur ce bord pour l’ajuster au titre et aux valeurs.
3. **Cellules.** Tapez une valeur et appuyez sur [[Enter]]. Le copier-coller fonctionne avec les tableurs ([[Ctrl+C]], [[Ctrl+V]]) ; [[Ctrl+D]] recopie vers le bas.

Une série de données peut être saisie sous forme de réplicats (chaque valeur dans sa propre colonne) ou sous forme de **mean, SD and N** (moyenne, écart-type et N) ou de **mean, SEM and N** (moyenne, erreur-type de la moyenne et N) tirés d’un article ou d’un autre logiciel : choisissez-le dans l’en-tête de la série.

Pour exclure une valeur des graphiques et des analyses sans la supprimer, sélectionnez-la et appuyez sur [[Ctrl+E]] (**Exclude / Include**, Exclure / Inclure). Les valeurs exclues apparaissent en italique bleu, barrées.

### Formules et transformations

- **Data › Column Formula** (Données › Formule de colonne) remplit une colonne à partir des autres, par exemple `(B - A) / A * 100`. La colonne se met à jour quand les données changent. Les dates aussi : `date(2026, 11, 5)`, `today()`, `year(X)`, `month(X)`, `day(X)`, et `days(B, A)` ou `hours(B, A)` pour le temps entre deux dates.
- **Data › Transform** (Données › Transformer) crée un nouveau tableau de valeurs transformées : logarithmes, 1/X, °C en K, soustraction d’une ligne de base, normalisation.
- **Data › Check Data** (Données › Vérifier les données) recherche les fautes de frappe, les valeurs manquantes et les valeurs qu’un axe logarithmique ne peut pas afficher.

### Importer

**Data › Import** (Données › Importer), ou **File › Import** (Fichier › Importer), lit les fichiers CSV, TXT et TSV, les classeurs .xlsx et les projets .pzfx. Un aperçu montre comment les colonnes seront lues ; choisissez la ligne d’en-tête et les réplicats, puis cliquez sur **Import**. Quand la colonne X contient des dates, **The X column holds dates** (La colonne X contient des dates) est coché pour vous. **Data › Several Files** (Données › Plusieurs fichiers) importe de nombreuses séries de mesures d’un coup : une série de données par fichier dans un seul tableau lorsqu’ils partagent les mêmes valeurs X, sinon un tableau par fichier. Les plans de microplaques (96 et 384 puits) sont reconnus.

### Les points d’une image de graphique

**Data › Digitize Graph** (Données › Numériser un graphique) lit les points d’un graphique publié à partir de son image (PNG, JPG, GIF, BMP ou WebP) dans un nouveau tableau. Cliquez sur **X mark 1** (repère X 1), puis sur une graduation de l’axe X dont vous connaissez la valeur, et tapez cette valeur ; faites de même pour **X mark 2**, **Y mark 1** et **Y mark 2**, en choisissant des repères éloignés. Cochez **Log** pour un axe à échelle logarithmique. Cliquez ensuite sur **Points** puis sur chaque point de la courbe ; un clic droit enlève le dernier, et **＋ Data set** (série) commence une autre courbe dans sa propre couleur. **Make Table** (Créer le tableau) donne une colonne X et une colonne par série, avec un graphique. Une image numérisée un peu de travers se lit quand même correctement, car chaque clic est mesuré le long de la droite qui passe par les deux repères de son axe.

### Dates et heures

La colonne X d’un tableau XY peut contenir des dates. Cliquez avec le bouton droit sur son en-tête (ou choisissez **Format X Column** (Format de la colonne X) dans le menu contextuel d’une cellule), puis **Dates** ou **Dates and times** (Dates et heures), et leur affichage : `5 Nov 2026`, `05-Nov-26`, `2026-11-05`, `05/11/2026` ou `Nov 2026`.

- Coller des dates dans une colonne X de nombres propose de la traiter comme des dates.
- Tapez ou collez les dates sous la forme `2026-11-05`, `5-Nov-26`, `5 Nov 2026`, `Nov 5, 2026` ou `05/11/2026`, avec une heure si vous voulez (`2026-11-05 14:30`). **File › Options › Dates** (Fichier › Options › Dates) indique si `05/11/2026` commence par le jour ou par le mois.
- Les dates sont gardées comme des nombres, les jours depuis le 1er janvier 1970, si bien que graphiques et ajustements les utilisent directement : le graphique a un axe de dates (**Format Graph › X Axis › Tick labels** (Mettre en forme › Axe X › Étiquettes) : automatique, jour et mois, mois et année, ISO ou numéro de semaine ; **Major ticks every** (Graduations principales tous les) : jour, semaine, 2 semaines, mois, 3 mois ou année), et une droite ajustée donne sa pente **par jour**, l’intersection avec l’axe X sous forme de date et la valeur à la première date.
- **Format Graph › Notes › Line at a date** (Mettre en forme › Notes › Ligne à une date) trace une ligne pointillée sur tout le graphique à la date saisie, avec une étiquette.
- Les classeurs exportés (.xlsx, .ods) contiennent de vraies dates. Les fichiers venant de Datum Plan s’ouvrent avec leurs dates déjà réglées.

## Analyses et résultats

### Choisir une analyse

![L’onglet Analyze.](img/analyze-tab.png)

1. **Analyze… et Test Chooser.** **Analyze…** (Analyser…) liste toutes les analyses ; **Test Chooser** (Choix du test) vous pose trois questions sur vos données et propose le test adapté.

Les autres groupes de l’onglet **Analyze** (Analyser) lancent directement une analyse : **Statistics** (Statistiques), **Compare Groups** (Comparer des groupes), **Regression** (Régression), **Materials** (Matériaux) et d’autres.

![Analyze… : toutes les analyses, par groupe.](img/analyze.png)

1. **Groupes.** Statistiques, régression et ajustement, matériaux, comparaison de groupes, relations, survie, signaux et spectres.
2. **Analyses.** Cliquez sur une analyse pour lire ce qu’elle fait et quelles bibliothèques Python elle utilise ; **Next…** (Suivant…) demande quelles séries de données inclure et quelles options appliquer.

### La feuille de résultats

![Une feuille de résultats : ajustement d’une courbe logistique.](img/results.png)

1. **Tableaux de résultats.** Les valeurs, avec leurs erreurs-types et leurs intervalles de confiance à 95 %. **Copy** (Copier) copie un tableau pour un tableur ou un document.
2. **La réponse.** Ce que l’analyse a trouvé, en termes simples.
3. **Vérifications.** Si les hypothèses sont respectées (par exemple, si les résidus se dispersent au hasard), avec une coche ou un avertissement.

En dessous se trouvent le texte **Methods** (Méthodes), prêt à coller dans un article (**Copy methods text**, Copier le texte des méthodes), et la légende de la figure. **Change…** (Modifier…) rouvre les options ; **Python code** (Code Python) montre le code Python à l’origine du résultat, pour le reproduire ailleurs. Cochez **Show on graph** (Afficher sur le graphique) pour tracer un ajustement ou les étoiles de significativité sur le graphique. Côté graphique, **Format Graph › Graph › Analyses** (Mettre en forme › Graphique › Analyses) liste les analyses du tableau : cochez celles que ce graphique montre et choisissez à côté de chacune les crochets que ce graphique trace (toutes les paires, les paires significatives ou aucun) et des étoiles ou des valeurs P ; **As the analysis** (comme l’analyse) suit les options de l’analyse. Si vous lancez une analyse que le tableau a déjà, Datum Plot propose d’abord de l’ouvrir (ou de la cocher sur le graphique affiché) ou d’en faire une autre (**Make Another**).

> **Astuce.** Vous ne savez pas ce que signifie une valeur ? Cliquez sur le **?** à côté, ou ouvrez **Help › Glossary** (Aide › Glossaire).

### Ce que Datum Plot sait analyser

- **Statistiques :** statistiques descriptives, tests de normalité, valeurs aberrantes, distributions de fréquences, fractions d’un total, intervalles de confiance bootstrap de la moyenne, de la médiane ou de l’écart-type.
- **Comparaison de groupes :** tests t (non apparié, de Welch, apparié), tests non paramétriques, ANOVA à un et à deux facteurs avec comparaisons multiples, mesures répétées et modèles à effets mixtes, tests t multiples avec taux de fausses découvertes et graphiques en volcan, tests t et ANOVA imbriqués, tailles d’effet, puissance, ANOVA à trois facteurs, ANCOVA (groupes comparés en tenant compte d’une covariable). Les tests t, l’ANOVA à un facteur et la corrélation donnent aussi un **Bayes factor** (facteur de Bayes, BF₁₀) : combien de fois les données sont plus probables avec une différence que sans ; contrairement à une valeur P, il peut aussi montrer des preuves d’absence de différence.
- **Relations :** corrélation, comparaison de méthodes de Bland-Altman, courbes ROC, tableaux de contingence (khi-deux, Fisher, risque relatif, rapport des cotes), concordance de jugements appariés (kappa de Cohen, tests de McNemar et de Bowker).
- **Régression et ajustement :** régression linéaire, ajustement de courbe à partir d’une bibliothèque de modèles ou de votre propre équation, ajustements globaux et comparaison de modèles, interpolation, aire sous la courbe, lissage, régression multiple, logistique et de Poisson, analyse en composantes principales et classification, ajustements de surface, splines de lissage.
- **Survie :** courbes de Kaplan-Meier, test du log-rank et rapports de risques instantanés (hazard ratios).
- **Signaux et spectres :** détection de pics, ajustement de pics gaussiens, lorentziens et de Voigt, spectres de Fourier et filtres, et l’évolution des fréquences dans le temps : un **scalogramme en ondelettes** ou un **spectrogramme** (Signals › Operation), une carte de chaleur temps–fréquence, avec la fréquence la plus forte à chaque instant en tableau à tracer.
- **Qualité :** cartes de contrôle (valeurs individuelles, X̄–R, X̄–S, p) avec vérification des règles et Cp/Cpk ; **Analyze › New Design** (Analyser › Nouveau plan) crée un plan factoriel à deux niveaux (complet ou demi-fraction) à remplir, et Factorial Analysis (Analyse factorielle) donne les effets, un diagramme de Pareto et les effets principaux.
- **Matériaux :** essais de traction, résistance de Weibull, énergies d’activation d’Arrhenius, courbes de fatigue S–N, analyse thermique DSC et ATG.

![Une feuille de résultats d’ANOVA à un facteur avec comparaisons multiples.](img/anova-results.png)

## Graphiques

### L’onglet Graph

![L’onglet Graph.](img/graph-tab.png)

1. **Graph** (Graphique). **New Graph** (Nouveau graphique), **Graph Type** (Type de graphique : nuage de points, barres, boîte à moustaches, violon, avant–après, courbes et d’autres) et **Data Table** (Tableau de données, pour revenir aux données).
2. **Axes** (Axes). Axes logarithmiques, axes encadrés, **Format Axes** (Mettre en forme les axes) et **Axis Break** (Coupure d’axe).
3. **Style** (Style). Des **Styles** (Styles) prêts à l’emploi pour les revues et les présentations, **Copy Look** (Copier l’apparence) vers d’autres graphiques, et **Colour Schemes** (Jeux de couleurs, dont certains adaptés aux daltoniens).
4. **Share** (Partager). **Export** (Exporter), **Copy Picture** (Copier l’image, à coller directement dans un document ou des diapositives), **Copy Embedded** (Copier en objet incorporé : un graphique que le document peut rouvrir dans Datum Plot) et **Print** (Imprimer).

Les autres groupes règlent les **Error Bars** (Barres d’erreur : la moyenne avec SD, SEM, IC à 95 % ou étendue, ou la médiane avec l’écart interquartile, l’étendue ou un IC à 95 %), affichent **Each Replicate** (Chaque réplicat), relient les points, affichent la légende (sur un graphique en colonnes, elle nomme chaque groupe par sa couleur), fixent la **Size** (Taille) et ajoutent un ajustement de courbe, des étoiles de significativité ou des annotations. Avec un **Axis Break** (Coupure d’axe), **Format Graph › Y Axis** (Mettre en forme › Axe Y) règle aussi la part de l’axe de chaque côté de la coupure et les graduations au-delà.

### Mettre en forme un graphique

Double-cliquez sur n’importe quelle partie d’un graphique (un axe, une série de données, le titre) pour la mettre en forme, ou cliquez avec le bouton droit sur un axe › **Format Axes** (Mettre en forme les axes), ou utilisez **Graph › Format Axes** (Graphique › Mettre en forme les axes). Il n’y a qu’une fenêtre Format Graph : ces commandes l’amènent à la page demandée, et elle agit toujours sur le graphique affiché (ouvrez-en un autre et elle le suit ; ouvrez un tableau ou des résultats et elle se ferme). Le nom du graphique est affiché au-dessus ; dans le navigateur, l’aperçu de chaque graphique est sous son nom (clic droit › **Hide Previews** (Masquer les aperçus) pour gagner de la place). Faites glisser le bord droit du navigateur pour l’élargir. Ctrl+clic (ou Maj+clic) sélectionne plusieurs éléments : clic droit pour les supprimer ensemble, les ranger dans un dossier (**Move to Folder › New Folder…** (Ranger dans un dossier › Nouveau dossier)) ou colorer leur nom (**Colour** (Couleur)). Clic droit sur un tableau › **Show Only This Family** (Afficher seulement cette famille) pour ne voir que ce tableau avec ses résultats, graphiques et mises en page ; **Show All** (Tout afficher) ramène le reste. Le **＋** à côté de Graphs crée un graphique de n’importe quel tableau ou copie le graphique ouvert avec sa mise en forme ; clic droit sur un tableau › **Duplicate with Graphs and Results** (Dupliquer avec graphiques et résultats) ou **Duplicate Table Only** (Dupliquer le tableau seul) ; clic droit sur une mise en page › **Copy Picture** (Copier l’image) ou **Export** (Exporter). Dans **Format Graph › Data Sets** (Mettre en forme › Séries), **Order** (Ordre) déplace les séries le long d’un graphique en colonnes (le tableau garde son ordre), et **Fill** (Remplissage) et **Border** (Bordure) colorent barres, boîtes et violons.

![Format Graph, ancré à côté du graphique.](img/format.png)

1. **Pages.** **Data Sets** (Séries de données : symboles, couleurs, lignes, barres d’erreur, axe Y de droite), **X Axis** (Axe X), **Y Axis** (Axe Y), **Graph** (Graphique : taille et polices) et les notes.
2. **Réglages.** Les modifications s’appliquent immédiatement.
3. **Le graphique** reste visible pendant que vous travaillez.

### Couleurs

![Graph › Colour Schemes (Graphique › Jeux de couleurs), à côté du graphique.](img/colours.png)

1. **Jeux de couleurs.** Cliquez sur l’un d’eux : le graphique change aussitôt, car la fenêtre se place à côté du graphique. Les jeux marqués **colour-blind safe** (adapté aux daltoniens) restent faciles à distinguer pour les personnes atteintes de l’un des trois types courants de daltonisme ; le jeu par défaut, Okabe-Ito, en fait partie.
2. **Ce que voient les lecteurs daltoniens.** Les trois colonnes montrent chaque jeu tel que le voient les personnes atteintes de protanopie, de deutéranopie et de tritanopie.

Vos propres couleurs se saisissent dans la dernière ligne (#hex, séparées par des virgules). Dans **Format Graph › Data Sets** (Mettre en forme le graphique › Séries de données), chaque couleur est un petit carré qui montre la couleur telle qu’elle est dessinée. Cliquez dessus pour les couleurs du jeu, une couleur à vous, l’intensité (**Strength**) d’un remplissage, ou **Automatic** (retour au jeu de couleurs) ; un carré marqué A est automatique. Sur les graphiques à barres, boîtes et violons, le remplissage et la bordure des barres viennent d’abord, puis la forme, la taille, le remplissage et la bordure des symboles, chacun réglé à part. Sur ces graphiques, les symboles ont aussi leur propre case **Filled** (rempli), la bordure des barres ainsi que le remplissage et la bordure des symboles ont une intensité (**Strength**), et le carré **Error bars** (barres d’erreur) règle la couleur des barres d’erreur (automatique : la couleur du jeu). Un trait marque le début de chaque groupe de réglages. Une bordure de symbole automatique suit le jeu de couleurs : changer le remplissage ne la change plus. **Reset all colours** (Réinitialiser les couleurs) remet toutes les couleurs au jeu choisi. Toute fenêtre se déplace en faisant glisser sa barre de titre.

### Travailler sur le graphique

- Survolez un point pour voir ses valeurs.
- Faites glisser une note pour la déplacer ; double-cliquez dessus pour la modifier.
- Faites un clic droit sur un point pour l’exclure.
- **Zoom to a Box** (Zoomer sur un cadre), **Pan** (Déplacer la vue) et **Statistics of a Region** (Statistiques d’une zone) se trouvent dans le menu contextuel du graphique ; [[Ctrl]] et la molette de la souris zooment la vue.

### Des graphiques pour chaque type de données

![Comparaison de groupes : chaque valeur, moyenne et écart-type, avec les étoiles de significativité de l’ANOVA.](img/anova.png)

![Un tableau matrice représenté en carte de contours avec un ajustement de surface.](img/contour.png)

![Une étude de survie : courbes de Kaplan-Meier avec les sujets censurés marqués.](img/survival.png)

Les graphiques XY peuvent aussi être des graphiques polaires (**Format Graph › Graph › Polar**, Mettre en forme le graphique › Graphique › Polaire) ou en cascade, chaque courbe décalée au-dessus de la précédente (**Graph › Graph Style › Waterfall**, Graphique › Style de graphique › Cascade). Les tableaux à plusieurs variables peuvent être des diagrammes ternaires (les trois premières variables en parts de 100 %) des graphiques à bulles (X, Y, taille et couleur des bulles), des nuages de points 3D (X, Y, Z et couleur) ou des champs de vecteurs (flèches en X, Y avec leurs deux composantes) ; les tableaux groupés peuvent être des diagrammes en radar (les lignes sont les rayons) ; les tableaux matrices peuvent être tracés en cartes de contours, cartes de chaleur, surfaces 3D ou maillages filaires.

## Mises en page et export

### Mises en page

Une mise en page dispose plusieurs graphiques et du texte sur une même page : une figure à plusieurs panneaux pour une revue, un poster ou une diapositive.

![Une figure à deux panneaux (onglet Layout).](img/layout.png)

1. **Layout** (Mise en page). **New Layout** (Nouvelle mise en page), **Panel Letters** (Lettres des panneaux : A, a, (a)), **Arrange** (Disposer : aligner et dimensionner les panneaux), **Journal Figure** (Figure de revue : sur une ou deux colonnes d’une revue) et **Add Graph** (Ajouter un graphique).
2. **La page.** Faites glisser un panneau pour le déplacer ; faites glisser un coin pour le redimensionner. Faites un clic droit sur un panneau pour d’autres choix.

Le groupe **Templates** (Modèles) crée un **Poster** (Poster) ou une **Slide** (Diapositive). Le groupe **Export** (Exporter) enregistre la page.

### Export

![File › Export : les formats.](img/export.png)

1. **File › Export** (Fichier › Exporter) exporte le graphique ouvert.
2. **Formats.** **PNG** pour les diapositives et le web ; **TIFF** (300–1200 dpi, en CMJN si demandé) pour les revues ; les formats vectoriels **SVG**, **PDF** et **EPS**, qui restent nets à toutes les tailles. **Copy picture** (Copier l’image) place le graphique dans le presse-papiers.

Autres façons de partager, dans **Tools** (Outils) :

- **Export All Graphs** (Exporter tous les graphiques) en une fois.
- **Workbook** (Classeur) : tous les tableaux et résultats, en feuilles d’un fichier .xlsx ou .ods.
- **Slides** (Diapositives) : chaque graphique sur sa propre diapositive, et une diapositive par résultat (.pptx ou .odp).
- **Document** : les informations du projet, chaque graphique avec sa légende, chaque résultat et le texte des méthodes (.docx ou .odt).

Choisissez le type de fichier dans la boîte d’enregistrement. Les fichiers .ods, .odt et .odp sont au format OpenDocument, la norme ouverte.

### Des graphiques modifiables depuis un document

**Graph › Copy Embedded** (Graphique › Copier en objet incorporé, ou clic droit sur un graphique) copie le graphique avec ses données. Collez-le dans un document, des diapositives ou un classeur sous Windows : il ressemble à l’image, et **un double-clic dessus l’ouvre dans Datum Plot**. Modifiez les données, les couleurs ou les axes, puis cliquez sur **Update** (Mettre à jour) dans la barre du haut (ou fermez la fenêtre et choisissez **Update and Close**, Mettre à jour et fermer) : le graphique du document change. Les données voyagent dans le document, si bien qu’un collègue équipé de Datum Plot peut aussi l’ouvrir.

- **Copy Picture** (Copier l’image) reste le choix simple : une image sans lien avec Datum Plot.
- Sur Mac ou dans un navigateur, le graphique incorporé s’affiche comme une image et ne peut pas être ouvert.
- Le document montre le premier graphique de la fenêtre.
- Dans un traitement de texte, collez avec **Paste Special › Datum Plot Graph Object** (Collage spécial ; un collage simple peut donner une image).
- Si un double-clic ne fait rien, **Help › Check Embedded Graphs** (Aide › Vérifier les graphiques incorporés) fait le test et dit ce qui ne va pas.

### Impression

**File › Print** (Fichier › Imprimer) imprime un graphique avec un en-tête et un pied de page, ou l’enregistre en PDF.

## La console Python et l’automatisation

### Console Python

La console Python exécute votre propre code Python sur les données du projet.

![Tools › Python Console.](img/console.png)

1. **Code.** Écrivez le code Python ici. Vos tableaux sont disponibles sous forme de DataFrames pandas : `tables` les liste, `table(0)` est le premier, `tables['Name']` en désigne un par son nom.
2. **Run** (Exécuter), ou [[Ctrl+Enter]].
3. **Sortie.** Ce que vous affichez avec print, la valeur de la dernière ligne et toute figure que vous tracez avec `plt`.
4. **How to use** (Mode d’emploi). Un court guide intégré à la console ; **Examples** (Exemples) insère du code fonctionnel comme point de départ.

Prêts à l’emploi : `np` (numpy), `pd` (pandas), `stats` (scipy.stats), `scipy` et `plt` (matplotlib). `new_table('Name', data)` ajoute un tableau au projet ; `result('Analysis name')` renvoie les valeurs d’une analyse. Les variables sont conservées d’une exécution à l’autre jusqu’à ce que vous cliquiez sur **Reset** (Réinitialiser).

> **Remarque.** La console exécute le code que vous écrivez, avec vos droits, comme n’importe quel script Python. Les projets ne contiennent jamais de code : ouvrir un projet reçu de quelqu’un d’autre n’exécute jamais rien.

### Automatisation

![L’onglet Tools.](img/tools-tab.png)

1. **Python.** **Python Console** (Console Python), **My Analyses** (Mes analyses : le code enregistré avec **Save As My Analysis**, Enregistrer comme mon analyse) et **Notebook** (Notebook : le projet sous forme de notebook Jupyter).

- **Analysis Template** (Modèle d’analyse) reproduit sur d’autres tableaux les analyses d’un tableau (avec leurs options) et l’apparence de son graphique.
- **Batch Process** (Traitement par lots) prend un tableau modèle et de nombreux fichiers : chaque fichier devient un tableau avec ces analyses et un graphique, et les réponses sont regroupées dans une même liste.

## Fichiers

- **Save** (Enregistrer, [[Ctrl+S]]) conserve tout le projet dans un seul fichier `.dplot` : tableaux, analyses, graphiques et mises en page. L’enregistrement est atomique : un plantage ou un disque plein ne laisse jamais un fichier à moitié écrit.
- **Open** (Ouvrir, [[Ctrl+O]]) ouvre un fichier `.dplot` ; vous pouvez aussi double-cliquer dessus dans Windows.
- Datum Plot enregistre une copie de récupération toutes les quelques minutes (**File › Options**, Fichier › Options). S’il se ferme de façon inattendue, il propose de récupérer votre travail au démarrage suivant.
- **Undo** (Annuler) et **Redo** (Rétablir), [[Ctrl+Z]] et [[Ctrl+Y]], permettent de revenir sur chaque modification.

## L’aide dans l’application

![L’onglet Help.](img/help-tab.png)

1. **Learn** (Apprendre). **Guide** (ce guide), **Getting Started** (Premiers pas), **Roadmap** (Feuille de route : ce que Datum Plot fera, et quand), **Glossary** (Glossaire), **What Is This Tool?** (Qu’est-ce que cet outil ?), **Statistics Guide** (Guide des statistiques), **Test Chooser** (Choix du test), **Shortcuts** (Raccourcis) et **Tell Me** (Dites-moi).
2. **Updates** (Mises à jour). **Check for Updates** (Rechercher des mises à jour).

![Help › Guide : choisir une langue.](img/guide-dialog.png)

1. **Langues.** English, 中文 or Français. Le guide est téléchargé depuis GitHub, vérifié par sa somme de contrôle, enregistré dans votre dossier Téléchargements, puis ouvert.

## Quel test choisir

| Votre question | Vos données | Analyse |
|---|---|---|
| Deux groupes diffèrent-ils ? | deux colonnes de valeurs | test t (Mann-Whitney si la distribution n’est pas normale) |
| Les mêmes éléments ont-ils changé ? | avant et après, appariés par ligne | test t apparié (Wilcoxon si la distribution n’est pas normale) |
| Trois groupes ou plus diffèrent-ils ? | des colonnes de valeurs | ANOVA à un facteur avec comparaisons multiples (Kruskal-Wallis si la distribution n’est pas normale) |
| Deux facteurs ont-ils un effet ? | tableau groupé | ANOVA à deux facteurs (à mesures répétées si les mêmes sujets sont mesurés plusieurs fois) |
| Les proportions sont-elles différentes ? | des effectifs | khi-deux ou test exact de Fisher |
| Quelle relation entre X et Y ? | XY | régression linéaire ou ajustement de courbe |
| Deux variables varient-elles ensemble ? | deux colonnes | corrélation |
| Lesquels de nombreux gènes ou protéines ont changé ? | tableau groupé, une ligne chacun, deux séries | tests t multiples et graphique en volcan |
| Deux méthodes concordent-elles ? | valeurs appariées | Bland-Altman |
| Deux évaluateurs concordent-ils ? | tableau de contingence de jugements appariés | Concordance (kappa de Cohen) |
| Les groupes diffèrent-ils une fois la covariable prise en compte ? | XY : covariable en X, une série par groupe | ANCOVA |
| Un test détecte-t-il bien une affection ? | valeurs des témoins et des cas | courbe ROC |
| Combien de temps avant un événement ? | temps avec événements et sujets censurés | Kaplan-Meier et test du log-rank |

> **Astuce.** **Analyze › Test Chooser** (Analyser › Choix du test) vous pose ces questions.

## Glossaire

| Terme | Signification |
|---|---|
| **Data set** (Série de données) | Une série de valeurs dans un tableau (une colonne, ou un groupe de colonnes de réplicats). |
| **Replicate** (Réplicat) | Une mesure répétée de la même chose. |
| **SD** (Écart-type) | Mesure de la dispersion des valeurs. |
| **SEM** (Erreur-type de la moyenne) | Précision avec laquelle la moyenne est connue (SD/√n). |
| **95% CI** (Intervalle de confiance à 95 %) | L’intervalle qui contient la vraie valeur avec une confiance de 95 %. |
| **P value** (Valeur P) | La probabilité d’observer une différence aussi grande s’il n’existait aucune différence réelle. |
| **Bayes factor (BF₁₀)** (Facteur de Bayes) | Combien de fois les données sont plus probables s’il y a une différence que s’il n’y en a pas ; au-dessus de 3, preuve modérée d’une différence ; en dessous de 1/3, preuve modérée d’absence de différence. |
| **R²** | La part de la variation expliquée par la droite ou la courbe ajustée. |
| **Censored** (Censuré) | Un sujet chez qui l’événement ne s’était pas encore produit lors du dernier suivi. |
| **Residual** (Résidu) | L’écart entre un point et la courbe ajustée. |

## Raccourcis et dépannage

### Raccourcis

| Touches | Action |
|---|---|
| [[Ctrl+S]] / [[Ctrl+Shift+S]] | Enregistrer / Enregistrer sous |
| [[Ctrl+O]] / [[Ctrl+N]] | Ouvrir / Nouveau |
| [[Ctrl+Z]] / [[Ctrl+Y]] | Annuler / Rétablir |
| [[Ctrl+C]] / [[Ctrl+V]] | Copier / coller (fonctionne avec les tableurs) |
| [[Ctrl+E]] | Exclure ou inclure des valeurs |
| [[Ctrl+D]] | Recopier vers le bas |
| [[Ctrl+C]] sur un graphique | Copier le graphique comme image |
| [[Ctrl+P]] | Imprimer |
| [[Ctrl+K]] | Dites-moi ce que vous voulez faire |
| [[F1]] | Tous les raccourcis |

### Dépannage

- **La barre d’état indique que le moteur graphique n’est pas disponible.** Cliquez sur **Tools › Restart Engine** (Outils › Redémarrer le moteur). Si le problème persiste, réinstallez Datum Plot depuis la page des versions (Releases) ; vos projets ne sont pas concernés.
- **Une analyse indique qu’elle ne peut pas être calculée.** Le message en donne la raison (trop peu de valeurs, valeurs identiques, X manquant). Corrigez les données ou choisissez d’autres séries de données avec **Change…** (Modifier…).
- **Un graphique n’affiche aucun point sur un axe logarithmique.** Les valeurs nulles ou négatives ne peuvent pas être tracées sur un axe logarithmique ; **Data › Check Data** (Données › Vérifier les données) les repère.
- **Autre problème.** L’étape concernée est refusée et votre projet reste tel quel ; les détails se trouvent dans `crash.log`, dans le dossier de données de l’application. Merci de le signaler via **Help › Report an Issue** (Aide › Signaler un problème).
