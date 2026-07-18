"""
Détection automatique de l'affectation (TMC/NMH) et du grade à partir des
rôles Discord de la personne, pour pré-remplir le formulaire de dépôt.
Les identifiants de rôles ci-dessous sont spécifiques au serveur Discord
HCT — à mettre à jour si les rôles sont recréés un jour (un rôle recréé
change d'ID, même avec le même nom).
"""

AFFECTATION_ROLE_IDS = {
    "807004846548713512": "TMC",
    "807004742198493264": "NMH",
}

# Du moins important au plus important (ordre donné) : si une personne a
# plusieurs de ces rôles à la fois, celui trouvé en dernier dans cette
# liste (donc le plus élevé dans la hiérarchie) est retenu.
#
# "Deputy Chief" n'a pas encore d'ID Discord connu au moment de l'écriture
# de ce fichier : sa ligne est commentée ci-dessous. Pour l'activer, il
# suffit de décommenter et de renseigner l'ID Discord réel du rôle
# (clic droit sur le rôle dans les paramètres du serveur > Copier l'ID,
# avec le mode développeur activé dans Discord).
GRADE_ROLE_IDS_BY_IMPORTANCE = [
    ("805480586814423050", "Interne"),
    ("805481706450714624", "EMT"),
    ("1140971706039685150", "Junior Résident"),
    ("805481769201172510", "Résident"),
    ("1141728911340867614", "Doctor"),
    ("805481781239349278", "Senior Doctor"),
    ("860189666908045323", "Professor"),
    ("809086773326118952", "Head of Department"),
    ("1140657047126425660", "Shift Supervisor"),
    ("805518674806046733", "Deputy Chief"),
    ("805481782119104522", "Chief"),
    ("805551419905015818", "DEO"),
    ("805508029151313921", "CEO"),
]


def detect_affectation(discord_role_ids):
    """Retourne 'TMC', 'NMH', ou None si la personne n'a aucun des deux
    rôles d'affectation connus.

    Si elle a les deux à la fois (cas normalement impossible), le premier
    trouvé dans l'ordre TMC puis NMH est retenu — aucune priorité n'a été
    précisée entre les deux."""
    role_ids = {str(r) for r in discord_role_ids}
    for role_id, affectation in AFFECTATION_ROLE_IDS.items():
        if role_id in role_ids:
            return affectation
    return None


def detect_grade(discord_role_ids):
    """Retourne le grade le plus élevé parmi les rôles Discord de la
    personne, ou None si elle n'a aucun des rôles de grade connus."""
    role_ids = {str(r) for r in discord_role_ids}
    grade_trouve = None
    for role_id, grade in GRADE_ROLE_IDS_BY_IMPORTANCE:
        if role_id in role_ids:
            grade_trouve = grade  # ne pas s'arrêter : le dernier trouvé (le plus important) gagne
    return grade_trouve