"""Interaction -> Memory -> Learning. Everything written to Hindsight goes through here."""
import datetime as dt
import memory, analytics
from db import Session, Post, Learning, Recommendation, Brand, COLS, post_dict

def post_text(p: dict) -> str:
    d = p["date"]
    return (f"On {d:%b %d} the brand posted a {p['format']} about {p['topic']} on {p['platform']} at {d.hour}:00 "
            f"(caption: '{p['caption']}'). Result: {p['views']} views, {p['engagement_rate']}% engagement, "
            f"{p['comments']} comments, {p['shares']} shares; audience sentiment {p['sentiment']}.")

def sync_lessons() -> list[str]:
    """Derive lessons from all posts; retain any not yet learned (dedupe by stable key)."""
    with Session() as s:
        posts = [post_dict(p) for p in s.query(Post).all()]
        known = {l.key for l in s.query(Learning).all()}
        new = [(k, t) for k, t in analytics.lessons(posts) if k not in known]
        for k, t in new: s.add(Learning(key=k, text=t))
        s.commit()
    for _, t in new: memory.remember(f"Lesson learned about this brand's audience: {t}", context="lesson")
    return [t for _, t in new]

def ingest(rows: list[dict]) -> dict:
    with Session() as s:
        s.add_all([Post(**{c: r[c] for c in COLS}) for r in rows]); s.commit()
    memory.remember_many([{"content": post_text(r), "context": "historical_post", "timestamp": r["date"]} for r in rows])
    return {"imported": len(rows), "new_lessons": sync_lessons()}

def record_outcome(rec_id: int, views: int, likes: int, comments: int, shares: int) -> dict:
    with Session() as s:
        rec = s.get(Recommendation, rec_id)
        if not rec: raise ValueError("unknown recommendation")
        pl = rec.payload; posts = [post_dict(p) for p in s.query(Post).all()]
        er = round((likes + comments + shares) / max(views, 1) * 100, 2)
        base = analytics.patterns(posts).get("baseline", 0)
        verdict = "above" if er > base * 1.1 else "below" if er < base * 0.9 else "near"
        rec.outcome = {"views": views, "likes": likes, "comments": comments, "shares": shares, "engagement_rate": er, "vs_baseline": verdict}
        hour = int(str(pl["best_time"]).split(":")[0]) + (12 if "PM" in str(pl["best_time"]).upper() and int(str(pl["best_time"]).split(":")[0]) < 12 else 0)
        s.add(Post(date=dt.datetime.now().replace(hour=min(hour, 23), minute=0, second=0, microsecond=0), platform="Unknown", topic=pl["topic_category"], format=pl["format"],
                   caption=pl["topic"], views=views, likes=likes, comments=comments, shares=shares, engagement_rate=er, sentiment="unknown"))
        s.commit(); out = rec.outcome
    memory.remember(f"We followed our own recommendation '{pl['topic']}' ({pl['format']} at {pl['best_time']}). Outcome: {views} views, "
                    f"{er}% engagement ({verdict} the {base}% baseline), {comments} comments, {shares} shares. Reasons given were: {'; '.join(pl['reasons'])}.",
                    context="recommendation_outcome")
    return {**out, "baseline": base, "new_lessons": sync_lessons()}

def save_brand(b: dict) -> None:
    with Session() as s:
        row = s.query(Brand).first()
        if row: row.data = b
        else: s.add(Brand(data=b))
        s.commit()
    memory.remember("Brand profile. " + "; ".join(f"{k}: {v}" for k, v in b.items() if v), context="brand_profile")

def feedback(rec_id: int, action: str, note: str = "") -> None:
    with Session() as s:
        rec = s.get(Recommendation, rec_id)
        if not rec: raise ValueError("unknown recommendation")
        rec.payload = {**rec.payload, "feedback": {"action": action, "note": note}}; pl = rec.payload; s.commit()
    verb = "decided to post" if action == "accepted" else "rejected"
    memory.remember(f"The team {verb} SocialMind's recommendation '{pl['topic']}' ({pl['format']} at {pl['best_time']}). "
                    + (f"Their note: {note}" if note else ""), context="recommendation_feedback")
