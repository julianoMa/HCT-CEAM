"""
Export PDF d'un dossier CEAM : informations générales, historique des
statuts, et réponses officielles de la commission — un résumé imprimable
et propre, utile pour garder une trace formelle d'un dossier (clôturé et
archivé, ou à tout autre moment).

Utilise fpdf2 (pur Python, sans dépendance système), plus adapté qu'une
librairie type WeasyPrint sur un hébergement serverless comme Vercel.
"""

from datetime import datetime, timezone

from app.timezone_utils import APP_TIMEZONE

from fpdf import FPDF

ACCENT_RGB = (244, 182, 93)
DARK_TEXT_RGB = (26, 18, 3)
TEXT_RGB = (15, 23, 42)
MUTED_RGB = (100, 116, 139)


class _DossierPDF(FPDF):
    def __init__(self, reference):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.reference = reference
        self.set_auto_page_break(auto=True, margin=18)

    def header(self):
        self.set_fill_color(*ACCENT_RGB)
        self.rect(0, 0, 210, 22, style="F")
        self.set_xy(10, 6)
        self.set_text_color(*DARK_TEXT_RGB)
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 6, "Commission d'Éthique des Affaires Médicales", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 10)
        self.set_x(10)
        self.cell(0, 6, f"Dossier {self.reference}", new_x="LMARGIN", new_y="NEXT")
        self.ln(8)
        self.set_text_color(*TEXT_RGB)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*MUTED_RGB)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title):
        self.ln(2)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*TEXT_RGB)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*ACCENT_RGB)
        self.set_line_width(0.5)
        y = self.get_y()
        self.line(10, y, 200, y)
        self.ln(3)

    def label_value(self, label, value):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*MUTED_RGB)
        self.cell(45, 6, label, new_x="RIGHT", new_y="TOP")
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*TEXT_RGB)
        self.multi_cell(145, 6, value or "-", new_x="LMARGIN", new_y="NEXT")

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*TEXT_RGB)
        self.multi_cell(0, 6, text or "-", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)


def generate_dossier_pdf(rapport):
    """Construit le PDF d'un dossier et retourne son contenu en bytes."""
    pdf = _DossierPDF(rapport.reference)
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.section_title("Informations générales")
    pdf.label_value("Référence :", rapport.reference)
    pdf.label_value("Statut :", rapport.status_label)
    pdf.label_value("Déposé le :", rapport.send_date_fr)
    if rapport.archived:
        pdf.label_value("Archivé :", "Oui")

    pdf.section_title("Plaignant")
    pdf.label_value("Nom :", f"{rapport.plaignant_first_name} {rapport.plaignant_last_name}")
    pdf.label_value("Grade :", rapport.plaignant_rank)
    pdf.label_value("Affectation :", rapport.plaignant_affectation)

    pdf.section_title("Personne concernée")
    pdf.label_value("Nom :", f"{rapport.concerne_first_name} {rapport.concerne_last_name}")
    pdf.label_value("Grade :", rapport.concerne_rank)
    pdf.label_value("Affectation :", rapport.concerne_affectation)

    pdf.section_title("Événement")
    pdf.label_value("Date :", f"{rapport.event_date_fr} à {rapport.event_hour}")
    if rapport.witness:
        pdf.label_value("Témoin(s) :", rapport.witness)
    pdf.label_value("Description :", "")
    pdf.body_text(rapport.description)
    if rapport.proof:
        pdf.label_value("Preuve(s) :", rapport.proof)

    pdf.section_title("Historique des statuts")
    if rapport.status_history_affichage:
        for h in rapport.status_history_affichage:
            pdf.body_text(
                f"{h['changed_at_fr']} - {h['status_label']} "
                f"(par {h['author_name']}, {h['author_rank']})"
            )
    else:
        pdf.body_text("Aucun changement de statut enregistré.")

    pdf.section_title("Réponses officielles de la commission")
    if rapport.reponses_affichage:
        for r in rapport.reponses_affichage:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*TEXT_RGB)
            pdf.multi_cell(
                0, 6,
                f"{r['type_label']} - {r['sent_at_fr']} ({r['author_name']}, {r['author_rank']})",
                new_x="LMARGIN", new_y="NEXT",
            )
            pdf.body_text(r["content"])
            if r.get("attachments"):
                noms = ", ".join(a["name"] for a in r["attachments"])
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(*MUTED_RGB)
                pdf.multi_cell(0, 6, f"Pièces jointes : {noms}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
    else:
        pdf.body_text("Aucune réponse envoyée pour le moment.")

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*MUTED_RGB)
    pdf.multi_cell(
        0, 6,
        f"Document généré le "
        f"{datetime.now(timezone.utc).astimezone(APP_TIMEZONE).strftime('%d/%m/%Y à %H:%M')} "
        "depuis la plateforme CEAM.",
        new_x="LMARGIN", new_y="NEXT",
    )

    return bytes(pdf.output())