"""Forgiving parser for user-supplied post rows (CSV or form). Time-of-day unknown is marked with microsecond=1."""
import datetime as dt
FMTS = ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%m/%d/%Y")

def _date(s: str) -> dt.datetime:
    for f in FMTS:
        try:
            d = dt.datetime.strptime(s, f)
            return d if ":" in f else d.replace(microsecond=1)
        except ValueError:
            pass
    raise ValueError(f"Unrecognized date '{s}' (use YYYY-MM-DD or YYYY-MM-DD HH:MM)")

def _title(s: str) -> str:  # keeps short acronyms like AI/VR uppercase
    return " ".join(w.upper() if len(w) <= 2 else w.capitalize() for w in s.split())

def _norm(s: str) -> str:
    s = _title(s)
    return s[:-3] + "y" if s.endswith("ies") else s[:-1] if s.endswith("s") and not s.endswith("ss") else s

def parse_row(raw: dict) -> dict:
    r = {str(k).strip().lower(): (str(v) if v is not None else "").strip() for k, v in raw.items() if k}
    for k in ("date", "topic", "format", "views"):
        if not r.get(k): raise ValueError(f"Missing required column/field '{k}'")
    n = lambda k: int(float(r.get(k) or 0))
    views, likes, comments, shares = n("views"), n("likes"), n("comments"), n("shares")
    if views <= 0: raise ValueError("views must be > 0")
    er = float(r["engagement_rate"]) if r.get("engagement_rate") else round((likes + comments + shares) / views * 100, 2)
    return dict(date=_date(f"{r['date']} {r['time']}" if r.get("time") else r["date"]), platform=r.get("platform") or "Unknown",
                topic=_title(r["topic"]), format=_norm(r["format"]), caption=r.get("caption", ""),
                views=views, likes=likes, comments=comments, shares=shares, engagement_rate=er,
                sentiment=(r.get("sentiment") or "unknown").lower())
