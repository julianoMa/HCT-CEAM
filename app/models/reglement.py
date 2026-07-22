"""
Règlement de la CEAM : un unique document Firestore, édité par un
administrateur sous forme de texte structuré (chapitres / sections /
articles), et affiché sous forme de cartes.

Convention d'écriture (texte brut, pas besoin d'éditeur riche) :
    # Titre de chapitre      -> démarre un nouveau chapitre
    ## Titre de section      -> démarre une nouvelle section dans le chapitre courant
    ### Titre d'article      -> démarre un nouvel article dans la section courante
    (tout le reste)          -> contenu de l'article courant

Exemple :
    # Chapitre 1 : Dispositions générales
    ## Section 1 : Objet et champ d'application
    ### Article 1 : Objet
    Le présent règlement a pour objet de...

    ### Article 2 : Champ d'application
    Il s'applique à...

    ## Section 2 : Définitions
    ### Article 3 : Terminologie
    ...

    # Chapitre 2 : Procédure
    ## Section 1 : Dépôt
    ### Article 4 : Délai de dépôt
    ...
"""

import re
from datetime import datetime

from app.extensions import get_db

COLLECTION = "config"
DOCUMENT_ID = "reglement"

_CHAPITRE_RE = re.compile(r"^#\s+(.*)")
_SECTION_RE = re.compile(r"^##\s+(.*)")
_ARTICLE_RE = re.compile(r"^###\s+(.*)")


class Reglement:
    def __init__(self, content="", updated_at=None, updated_by_name=None):
        self.content = content or ""
        self.updated_at = updated_at
        self.updated_by_name = updated_by_name

    @property
    def updated_at_fr(self):
        if not self.updated_at:
            return None
        try:
            return datetime.fromisoformat(self.updated_at).strftime("%d/%m/%Y à %H:%M")
        except (ValueError, TypeError):
            return self.updated_at

    @property
    def preambule(self):
        """Texte libre tapé avant le premier '#', '##' ou '###' — affiché
        avant le sommaire, jamais inclus dedans (il n'a pas de titre)."""
        lines = []
        for raw_line in self.content.splitlines():
            line = raw_line.rstrip()
            if _CHAPITRE_RE.match(line) or _SECTION_RE.match(line) or _ARTICLE_RE.match(line):
                break
            lines.append(raw_line)
        return "\n".join(lines).strip()

    @property
    def chapitres(self):
        """Parse le texte brut en chapitres contenant leurs sections, elles-
        mêmes contenant leurs articles :
        [{"title": str, "sections": [{"title": str, "articles": [{"title": str, "content": str}, ...]}, ...]}, ...].
        Le préambule (avant le premier titre) est exclu d'ici, voir la
        propriété `preambule` ci-dessus."""
        chapitres = []
        current_chapitre = None
        current_section = None
        current_article = None

        for raw_line in self.content.splitlines():
            line = raw_line.rstrip()

            chapitre_match = _CHAPITRE_RE.match(line)
            section_match = _SECTION_RE.match(line)
            article_match = _ARTICLE_RE.match(line)

            if chapitre_match:
                current_chapitre = {"title": chapitre_match.group(1).strip(), "sections": []}
                chapitres.append(current_chapitre)
                current_section = None
                current_article = None
                continue

            if section_match:
                if current_chapitre is None:
                    current_chapitre = {"title": "", "sections": []}
                    chapitres.append(current_chapitre)
                current_section = {"title": section_match.group(1).strip(), "articles": []}
                current_chapitre["sections"].append(current_section)
                current_article = None
                continue

            if article_match:
                if current_chapitre is None:
                    current_chapitre = {"title": "", "sections": []}
                    chapitres.append(current_chapitre)
                if current_section is None:
                    current_section = {"title": "", "articles": []}
                    current_chapitre["sections"].append(current_section)
                current_article = {"title": article_match.group(1).strip(), "content": ""}
                current_section["articles"].append(current_article)
                continue

            if current_article is not None:
                current_article["content"] += raw_line + "\n"
            # Texte tapé avant le premier article d'un chapitre/section :
            # ignoré à l'affichage, pour garder une convention simple
            # (chapitre/section = juste un titre qui regroupe, le contenu
            # vit toujours dans les articles).

        for chapitre in chapitres:
            for section in chapitre["sections"]:
                for article in section["articles"]:
                    article["content"] = article["content"].strip()

        return chapitres

    def to_dict(self):
        return {
            "content": self.content,
            "updated_at": self.updated_at,
            "updated_by_name": self.updated_by_name,
        }

    @classmethod
    def get(cls):
        db = get_db()
        doc = db.collection(COLLECTION).document(DOCUMENT_ID).get()
        if not doc.exists:
            return cls()
        data = doc.to_dict()
        return cls(
            content=data.get("content", ""),
            updated_at=data.get("updated_at"),
            updated_by_name=data.get("updated_by_name"),
        )

    def save(self, content, updated_by_name):
        db = get_db()
        self.content = content
        self.updated_at = datetime.utcnow().isoformat(timespec="minutes")
        self.updated_by_name = updated_by_name
        db.collection(COLLECTION).document(DOCUMENT_ID).set(self.to_dict())