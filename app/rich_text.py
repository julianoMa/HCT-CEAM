import re

from markupsafe import Markup, escape

URL_RE = re.compile(r'(https?://[^\s<>"]+)', re.IGNORECASE)

IMAGE_EXT_RE = re.compile(r'\.(jpe?g|png|gif|webp|bmp|avif)(\?.*)?$', re.IGNORECASE)

# Hébergeurs connus qui servent parfois des images sans extension de fichier
# dans l'URL (ex: certaines miniatures Zupimages).
KNOWN_IMAGE_HOST_RE = re.compile(r'(i\.imgur\.com|zupimages\.net/up/)', re.IGNORECASE)

YOUTUBE_RE = re.compile(
    r'(?:youtube\.com/watch\?v=|youtube\.com/shorts/|youtu\.be/)([\w-]{11})',
    re.IGNORECASE,
)

# Ponctuation qu'on ne veut pas inclure si elle traîne juste après une URL
# collée dans une phrase (ex: "voir ce lien : https://...jpg." -> le point
# final ne doit pas faire partie de l'URL).
_TRAILING_PUNCTUATION = ".,;:!?)"


def render_rich_text(raw_text):
    """Retourne un Markup HTML sûr à partir d'un texte brut."""
    if not raw_text:
        return Markup("")

    parts = []
    last_end = 0

    for m in URL_RE.finditer(raw_text):
        # Texte avant l'URL : échappé normalement.
        parts.append(str(escape(raw_text[last_end:m.start()])))

        raw_url = m.group(1)
        trimmed = raw_url.rstrip(_TRAILING_PUNCTUATION)
        trailing = raw_url[len(trimmed):]

        parts.append(_render_url(trimmed))
        if trailing:
            parts.append(str(escape(trailing)))

        last_end = m.end()

    parts.append(str(escape(raw_text[last_end:])))
    return Markup("".join(parts))


def _render_url(url):
    safe_url = str(escape(url))

    yt_match = YOUTUBE_RE.search(url)
    if yt_match:
        video_id = str(escape(yt_match.group(1)))
        return (
            '<div class="embed-youtube">'
            f'<iframe src="https://www.youtube-nocookie.com/embed/{video_id}" '
            'title="Vidéo YouTube intégrée" frameborder="0" '
            'allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
            'gyroscope; picture-in-picture" allowfullscreen loading="lazy">'
            '</iframe></div>'
        )

    if IMAGE_EXT_RE.search(url) or KNOWN_IMAGE_HOST_RE.search(url):
        return (
            f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer" '
            'class="embed-image-link">'
            f'<img src="{safe_url}" alt="Image jointe" loading="lazy" '
            'referrerpolicy="no-referrer" class="embed-image"></a>'
        )

    return f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer">{safe_url}</a>'