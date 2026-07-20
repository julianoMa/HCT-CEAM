from flask_wtf import FlaskForm
from flask_wtf.file import MultipleFileField
from wtforms import BooleanField, DateField, SelectField, StringField, TextAreaField, TimeField
from wtforms.validators import DataRequired, Length, Optional

from app.models.ceam import Rapport

AFFECTATION_CHOICES = [(a, a) for a in Rapport.AFFECTATIONS]


class RapportForm(FlaskForm):
    # 1. Plaignant
    plaignant_last_name = StringField("Nom", validators=[DataRequired(), Length(max=80)])
    plaignant_first_name = StringField("Prénom", validators=[DataRequired(), Length(max=80)])
    plaignant_rank = StringField("Grade", validators=[DataRequired(), Length(max=50)])
    plaignant_affectation = SelectField("Affectation", choices=AFFECTATION_CHOICES)

    # 2. Mis en cause
    concerne_last_name = StringField("Nom", validators=[DataRequired(), Length(max=80)])
    concerne_first_name = StringField("Prénom", validators=[DataRequired(), Length(max=80)])
    concerne_rank = StringField("Grade", validators=[DataRequired(), Length(max=50)])
    concerne_affectation = SelectField("Affectation", choices=AFFECTATION_CHOICES)

    # 3. Circonstances de l'incident
    event_date = DateField("Date de l'incident", validators=[DataRequired()])
    event_hour = TimeField("Heure approximative", validators=[DataRequired()])
    location = StringField("Lieu précis", validators=[DataRequired(), Length(max=150)])

    # 4. Exposé des faits
    description = TextAreaField(
        "Description chronologique et factuelle, sans jugement de valeur",
        validators=[DataRequired()],
    )

    # 5. Témoins de l'incident
    witness = TextAreaField("Témoin(s)", validators=[Optional()])

    # Preuves (ouvertes via un modal : liens + fichiers)
    proof = TextAreaField("Lien(s) preuve (vidéo, photo...)", validators=[Optional()])
    proof_files = MultipleFileField("Fichiers de preuve (PDF, images)")

    # Certification sur l'honneur
    certification = BooleanField(
        "Le plaignant certifie sur l'honneur l'exactitude des faits rapportés dans le "
        "présent formulaire. Il est informé que toute déclaration mensongère ou "
        "manifestement abusive peut faire l'objet d'un examen distinct par la Commission.",
        validators=[DataRequired(message="Tu dois certifier l'exactitude des faits pour envoyer le rapport.")],
    )


class NoteForm(FlaskForm):
    """Note interne privée du dossier, réservée à la commission —
    indépendante de tout changement de statut (voir les formulaires
    procéduraux ci-dessous pour ça)."""
    note = TextAreaField("Note interne", validators=[Optional()])


class SuspensionForm(FlaskForm):
    """Suspension du traitement : le motif est obligatoire."""
    motif = TextAreaField(
        "Motif de la suspension",
        validators=[DataRequired(message="Un motif est obligatoire pour suspendre le traitement.")],
    )


class ClotureForm(FlaskForm):
    """Classement + clôture finale du dossier."""
    classement = SelectField(
        "Classement",
        choices=[("", "Choisir un classement…")] + [(c, c) for c in Rapport.CLASSEMENTS],
        validators=[DataRequired(message="Un classement doit être sélectionné avant de clôturer.")],
    )


class ReponseForm(FlaskForm):
    """Envoi d'une nouvelle réponse officielle, ajoutée à l'historique du
    dossier et visible par le plaignant. La validation fine des pièces
    jointes (type, taille) se fait côté serveur dans app/storage.py plutôt
    que via un validateur WTForms, pour rester fiable quel que soit le
    nombre de fichiers sélectionnés."""
    type = StringField("Type de réponse", validators=[DataRequired(), Length(max=100)])
    content = TextAreaField("Contenu de la réponse", validators=[DataRequired()])
    attachments = MultipleFileField("Pièces jointes (PDF, images)")


class MessageForm(FlaskForm):
    """Message libre dans un fil de discussion du dossier — ouvert au
    déclarant, aux tiers, et aux membres CEAM (contrairement à ReponseForm,
    réservée à la commission pour les réponses officielles catégorisées).
    Le fil visé (thread) est transmis par un champ caché propre à chaque
    conversation dans le template, pas par un choix libre ici — voir la
    validation de sa valeur, faite côté route, dans app/ceam/routes.py."""
    content = TextAreaField("Message", validators=[DataRequired()])
    attachments = MultipleFileField("Pièces jointes (PDF, images)")
    thread = StringField("Fil de discussion", validators=[DataRequired()])


class ReglementForm(FlaskForm):
    """Édition du règlement CEAM (texte structuré en sections/articles),
    réservée aux administrateurs."""
    content = TextAreaField("Contenu du règlement", validators=[Optional()])