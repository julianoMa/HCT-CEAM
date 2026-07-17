from datetime import datetime, timedelta

from app.models.ceam import Rapport


def _make_rapport(**overrides):
    defaults = dict(
        id=1,
        plaignant_last_name="Dupont", plaignant_first_name="Jean",
        plaignant_affectation="TMC", plaignant_rank="Interne",
        concerne_last_name="Martin", concerne_first_name="Paul",
        concerne_affectation="NMH", concerne_rank="Chef de service",
        event_date="2026-01-15", event_hour="14:30",
        witness="", description="Description test", proof="",
        send_date=datetime(2026, 1, 1, 10, 0).isoformat(timespec="minutes"),
        owner_id=42, status=Rapport.STATUS_NOUVEAU, note="",
        reponses=[], archived=False, status_history=[],
    )
    defaults.update(overrides)
    return Rapport(**defaults)


def test_reference_uses_year_and_padded_id():
    r = _make_rapport(id=7, send_date="2026-03-01T10:00")
    assert r.reference == "CEAM-2026-0007"


def test_status_label_known_and_unknown():
    r = _make_rapport(status=Rapport.STATUS_CLOTURE)
    assert r.status_label == "Clôturé"
    r2 = _make_rapport(status=999)
    assert r2.status_label == "Inconnu"


def test_event_date_fr_formats_correctly():
    r = _make_rapport(event_date="2026-01-15")
    assert r.event_date_fr == "15/01/2026"


def test_event_date_fr_falls_back_on_bad_input():
    r = _make_rapport(event_date="pas une date")
    assert r.event_date_fr == "pas une date"


def test_delai_traitement_none_if_never_cloture():
    r = _make_rapport(status_history=[
        {"status": Rapport.STATUS_NOUVEAU, "author_name": "x", "author_rank": "y",
         "changed_at": "2026-01-01T10:00"},
    ])
    assert r.delai_traitement_jours is None


def test_delai_traitement_computed_from_status_history():
    r = _make_rapport(
        send_date="2026-01-01T10:00",
        status_history=[
            {"status": Rapport.STATUS_NOUVEAU, "author_name": "x", "author_rank": "y",
             "changed_at": "2026-01-01T10:00"},
            {"status": Rapport.STATUS_CLOTURE, "author_name": "x", "author_rank": "y",
             "changed_at": "2026-01-06T10:00"},
        ],
    )
    assert r.delai_traitement_jours == 5.0


def test_jours_depuis_depot_is_positive_for_past_date():
    past = (datetime.utcnow() - timedelta(days=3)).isoformat(timespec="minutes")
    r = _make_rapport(send_date=past)
    assert r.jours_depuis_depot >= 2.9


def test_filter_by_search_matches_reference():
    r1 = _make_rapport(id=1, send_date="2026-01-01T10:00")
    r2 = _make_rapport(id=2, send_date="2026-01-01T10:00", plaignant_last_name="Durand")
    result = Rapport.filter_by_search([r1, r2], "0001")
    assert result == [r1]


def test_filter_by_search_matches_name_case_insensitive():
    r1 = _make_rapport(plaignant_last_name="Dupont")
    r2 = _make_rapport(plaignant_last_name="Durand")
    result = Rapport.filter_by_search([r1, r2], "dupont")
    assert result == [r1]


def test_filter_by_search_empty_query_returns_all():
    r1 = _make_rapport()
    r2 = _make_rapport()
    assert Rapport.filter_by_search([r1, r2], "") == [r1, r2]


def test_reponses_affichage_maps_fields():
    r = _make_rapport(reponses=[{
        "type": "Accusé de réception", "content": "Texte", "author_name": "Commission",
        "author_rank": "Auto", "sent_at": "2026-01-01T10:00",
    }])
    affichage = r.reponses_affichage
    assert len(affichage) == 1
    assert affichage[0]["type_label"] == "Accusé de réception"
    assert affichage[0]["sent_at_fr"] == "01/01/2026 à 10:00"


def test_status_history_affichage_maps_fields():
    r = _make_rapport(status_history=[{
        "status": Rapport.STATUS_EN_EXAMEN, "author_name": "Alice",
        "author_rank": "Membre CEAM", "changed_at": "2026-01-02T09:00",
    }])
    affichage = r.status_history_affichage
    assert affichage[0]["status_label"] == "En cours d'examen"
    assert affichage[0]["author_name"] == "Alice"