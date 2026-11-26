import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_certs as b  # noqa: E402

T = date(2026, 12, 1)


def test_status():
    s = lambda a, z: {"reg_start": a, "reg_end": z}
    assert b.status(s("2026-12-10", "2026-12-20"), T) == "upcoming"
    assert b.status(s("2026-11-20", "2026-12-20"), T) == "open"
    assert b.status(s("2026-11-20", "2026-12-05"), T) == "closing_soon"
    assert b.status(s("2026-11-01", "2026-11-30"), T) == "closed"
    assert b.status(s("2026-11-01", "2026-12-01"), T) == "closing_soon"


def test_ics_range_and_escape():
    certs = [{"cert_id": "x", "title": "A,B"}]
    sc = [{"schedule_id": "x1", "cert_id": "x", "batch_name": "n", "exam_date": "2026-12-05/2026-12-06", "source_url": "https://e"}]
    from datetime import datetime, timezone
    ics = b.build_ics(certs, sc, datetime(2026, 12, 1, tzinfo=timezone.utc))
    assert "DTSTART;VALUE=DATE:20261205" in ics and "DTEND;VALUE=DATE:20261207" in ics
    assert "A\\,B" in ics


def test_data_consistent():
    import json
    root = Path(b.ROOT)
    certs = json.loads((root / "data/certifications.json").read_text(encoding="utf-8"))["certifications"]
    ids = [c["cert_id"] for c in certs]
    assert len(ids) == len(set(ids))
    for c in certs:
        assert c["schedule_type"] in {"fixed_batch", "on_demand", "campaign"}
        assert c["cost_type"] in {"free", "freemium", "paid", "voucher_available"}
        assert c["official_url"].startswith("https://")
