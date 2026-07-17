from app.rich_text import render_rich_text


def test_escapes_html():
    result = str(render_rich_text("<script>alert(1)</script>"))
    assert "<script>" not in result
    assert "&lt;script&gt;" in result


def test_plain_link_becomes_clickable():
    result = str(render_rich_text("Voir https://example.com/page pour plus d'infos"))
    assert '<a href="https://example.com/page"' in result
    assert 'target="_blank"' in result


def test_direct_image_link_becomes_thumbnail():
    result = str(render_rich_text("https://i.imgur.com/abc123.png"))
    assert "<img" in result
    assert 'src="https://i.imgur.com/abc123.png"' in result
    assert "embed-image" in result


def test_zupimages_direct_link_becomes_thumbnail():
    result = str(render_rich_text("https://www.zupimages.net/up/24/01/photo.jpg"))
    assert "<img" in result


def test_youtube_watch_link_becomes_embed():
    result = str(render_rich_text("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
    assert "embed-youtube" in result
    assert "dQw4w9WgXcQ" in result
    assert "<iframe" in result


def test_youtu_be_short_link_becomes_embed():
    result = str(render_rich_text("https://youtu.be/dQw4w9WgXcQ"))
    assert "embed-youtube" in result


def test_non_image_non_youtube_link_is_just_clickable():
    result = str(render_rich_text("https://example.com/page"))
    assert "<img" not in result
    assert "embed-youtube" not in result
    assert "<a href=" in result


def test_no_url_returns_escaped_text_only():
    result = str(render_rich_text("Texte simple sans lien"))
    assert "Texte simple sans lien" in result
    assert "<a " not in result


def test_empty_text_returns_empty():
    assert str(render_rich_text("")) == ""
    assert str(render_rich_text(None)) == ""


def test_trailing_punctuation_excluded_from_url():
    result = str(render_rich_text("Voir ce lien: https://example.com/page."))
    assert 'href="https://example.com/page"' in result