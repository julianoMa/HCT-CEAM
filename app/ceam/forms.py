from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, TextAreaField, TimeField
from wtforms.validators import DataRequired, Length, Optional

from app.models.ceam import Rapport

AFFECTATION_CHOICES = [(a, a) for a in Rapport.AFFECTATIONS]


class RapportForm(FlaskForm):
    # Plaignant
    plaignant_last_name = StringField("Nom du plaignant", validators=[DataRequired(), Length(max=80)])
    plaignant_first_name = StringField("Prénom du plaignant", validators=[DataRequired(), Length(max=80)])
    plaignant_affectation = SelectField("Affectation du plaignant", choices=AFFECTATION_CHOICES)
    plaignant_rank = StringField("Grade du plaignant", validators=[DataRequired(), Length(max=50)])

    # Concerné
    concerne_last_name = StringField("Nom du concerné", validators=[DataRequired(), Length(max=80)])
    concerne_first_name = StringField("Prénom du concerné", validators=[DataRequired(), Length(max=80)])
    concerne_affectation = SelectField("Affectation du concerné", choices=AFFECTATION_CHOICES)
    concerne_rank = StringField("Grade du concerné", validators=[DataRequired(), Length(max=50)])

    # Événement
    event_date = DateField("Date de l'événement", validators=[DataRequired()])
    event_hour = TimeField("Heure de l'événement", validators=[DataRequired()])
    witness = TextAreaField("Témoin(s)", validators=[Optional()])
    description = TextAreaField("Description détaillée", validators=[DataRequired()])
    proof = TextAreaField("Lien(s) preuve (vidéo, photo...)", validators=[Optional()])


class InstructionForm(FlaskForm):
    """Suivi interne du dossier (statut + note), réservé à la commission.
    Ne contient plus de champ de réponse : voir ReponseForm."""
    status = SelectField("Statut", coerce=int)
    note = TextAreaField("Note interne", validators=[Optional()])


class ReponseForm(FlaskForm):
    """Envoi d'une nouvelle réponse officielle, ajoutée à l'historique du
    dossier et visible par le plaignant."""
    type = StringField("Type de réponse", validators=[DataRequired(), Length(max=100)])
    content = TextAreaField("Contenu de la réponse", validators=[DataRequired()])


class ReglementForm(FlaskForm):
    """Édition du règlement CEAM (texte structuré en sections/articles),
    réservée aux administrateurs."""
    content = TextAreaField("Contenu du règlement", validators=[Optional()])