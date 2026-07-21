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


# ── Markdown léger pour la messagerie (Échanges) ──
# Volontairement limité à quelques syntaxes simples et sûres, pas un vrai
# moteur Markdown complet : gras, italique, code en ligne, et listes à
# puces. Le texte est TOUJOURS échappé avant toute substitution — aucun
# HTML fourni par l'utilisateur n'est jamais interprété tel quel.
_CHAT_CODE_RE = re.compile(r'`([^`\n]+?)`')
_CHAT_BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
_CHAT_ITALIC_RE = re.compile(r'(?<!\*)\*([^*\n]+?)\*(?!\*)')
_CHAT_BULLET_LINE_RE = re.compile(r'^[-*] +(.+)$')


def _build_mention_regex(names):
    """Construit un pattern qui reconnaît "@Nom Complet" pour un ensemble
    de noms connus (membres CEAM), le plus long d'abord pour qu'un nom
    composé ("Jean Dupont") ne soit pas coupé par un nom plus court qui en
    serait un préfixe ("Jean")."""
    unique_names = sorted({n for n in (names or []) if n}, key=len, reverse=True)
    if not unique_names:
        return None
    pattern = "|".join(re.escape(n) for n in unique_names)
    return re.compile(r'@(' + pattern + r')\b')


def _apply_mentions(escaped_text, mention_regex):
    """Entoure les mentions reconnues d'un span dédié, sur du texte DÉJÀ
    échappé — les noms comparés ne contiennent jamais de caractères HTML
    spéciaux, donc comparer directement sur le texte échappé est sûr."""
    if not mention_regex:
        return escaped_text
    return mention_regex.sub(lambda m: f'<span class="chat-mention">@{m.group(1)}</span>', escaped_text)


def _apply_chat_markdown_inline(escaped_text, mention_regex=None):
    """Applique gras/italique/code/mentions sur un texte DÉJÀ échappé.
    L'ordre (code, puis gras, puis italique, puis mentions) évite qu'un
    `**gras**` soit partiellement confondu avec de l'italique."""
    escaped_text = _CHAT_CODE_RE.sub(lambda m: f"<code>{m.group(1)}</code>", escaped_text)
    escaped_text = _CHAT_BOLD_RE.sub(lambda m: f"<strong>{m.group(1)}</strong>", escaped_text)
    escaped_text = _CHAT_ITALIC_RE.sub(lambda m: f"<em>{m.group(1)}</em>", escaped_text)
    escaped_text = _apply_mentions(escaped_text, mention_regex)
    return escaped_text


def render_chat_markdown(raw_text, mention_names=None):
    """Comme render_rich_text (liens/images/YouTube auto-détectés), mais
    avec en plus un markdown léger : **gras**, *italique*, `code`, et les
    lignes commençant par "- " ou "* " transformées en liste à puces.
    Réservé à l'espace d'échanges — le reste du site (règlement,
    description, preuves) continue d'utiliser render_rich_text tel quel.

    mention_names : liste optionnelle de noms complets de membres CEAM —
    toute occurrence "@Nom Complet" dans le texte est alors surlignée
    (voir _build_mention_regex). Ignoré si non fourni (comportement
    inchangé)."""
    if not raw_text:
        return Markup("")

    mention_regex = _build_mention_regex(mention_names)
    lines = raw_text.split("\n")
    rendered_lines = []
    in_list = False

    for line in lines:
        bullet_match = _CHAT_BULLET_LINE_RE.match(line)
        if bullet_match:
            if not in_list:
                rendered_lines.append("<ul class='chat-markdown-list'>")
                in_list = True
            rendered_lines.append(f"<li>{_render_line_with_links(bullet_match.group(1), mention_regex)}</li>")
            continue
        if in_list:
            rendered_lines.append("</ul>")
            in_list = False
        rendered_lines.append(_render_line_with_links(line, mention_regex))

    if in_list:
        rendered_lines.append("</ul>")

    return Markup("\n".join(rendered_lines))


def _render_line_with_links(raw_line, mention_regex=None):
    """Rend une seule ligne : découpe autour des URL (comme
    render_rich_text), applique le markdown léger + mentions sur les
    segments de texte, et laisse les URL gérées par _render_url tel quel."""
    parts = []
    last_end = 0
    for m in URL_RE.finditer(raw_line):
        segment = str(escape(raw_line[last_end:m.start()]))
        parts.append(_apply_chat_markdown_inline(segment, mention_regex))

        raw_url = m.group(1)
        trimmed = raw_url.rstrip(_TRAILING_PUNCTUATION)
        trailing = raw_url[len(trimmed):]
        parts.append(_render_url(trimmed))
        if trailing:
            parts.append(str(escape(trailing)))

        last_end = m.end()

    tail = str(escape(raw_line[last_end:]))
    parts.append(_apply_chat_markdown_inline(tail, mention_regex))
    return "".join(parts)