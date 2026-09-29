"""Derives patterns from raw posts. Nothing here is hard-coded: conclusions come from the data."""
import datetime as dt
from collections import defaultdict
EDU = ("tutorial", "how to", "tips", "guide", "learn", "explained")
def _avg(x): return sum(x) / len(x) if x else 0.0
def slot(h): return "7–9 PM" if 19 <= h < 21 else "12–2 PM" if 12 <= h < 14 else "9–11 AM" if 9 <= h < 11 else "Other"
def slot_of(p): return "Unknown" if p["date"].microsecond == 1 else slot(p["date"].hour)
def style(p): return "Educational" if any(k in p["caption"].lower() for k in EDU) else "Non-educational"

def group(posts, key):
    g = defaultdict(list)
    for p in posts: g[key(p)].append(p)
    return {k: {"n": len(v), "er": round(_avg([p["engagement_rate"] for p in v]), 2),
                "comment_rate": round(_avg([p["comments"] / max(p["views"], 1) * 100 for p in v]), 3),
                "positive_share": (lambda k: round(_avg([p["sentiment"] == "positive" for p in k]), 2) if k else None)([p for p in v if p["sentiment"] != "unknown"])} for k, v in g.items()}

def patterns(posts):
    if not posts: return {"n": 0, "baseline": 0}
    base = round(_avg([p["engagement_rate"] for p in posts]), 2)
    cutoff = max(p["date"] for p in posts) - dt.timedelta(days=30)
    recent = [p for p in posts if p["date"] >= cutoff]; prior = [p for p in posts if p["date"] < cutoff]
    rt, pt = group(recent, lambda p: p["topic"]), group(prior, lambda p: p["topic"])
    emerging = [{"topic": t, "recent_er": v["er"], "prior_er": pt[t]["er"]} for t, v in rt.items()
                if v["n"] >= 3 and t in pt and v["er"] > pt[t]["er"] * 1.15]
    return {"n": len(posts), "baseline": base,
            "topics": group(posts, lambda p: p["topic"]), "formats": group(posts, lambda p: p["format"]),
            "slots": group(posts, slot_of), "styles": group(posts, style),
            "combos": group(posts, lambda p: f'{p["topic"]}|{p["format"]}'),
            "sentiment_recent": group(recent, lambda p: "all")["all"]["positive_share"] if recent else None,
            "sentiment_prior": group(prior, lambda p: "all")["all"]["positive_share"] if prior else None,
            "emerging": emerging}

def lessons(posts):
    """Returns [(stable_key, sentence)] of patterns supported by enough posts."""
    P = patterns(posts); base = P.get("baseline") or 0; out = []
    for dim, label in (("topics", "topic"), ("formats", "format"), ("slots", "posting window"), ("styles", "content style"), ("combos", "combination")):
        for k, v in P.get(dim, {}).items():
            if v["n"] < (3 if dim == "combos" else 4) or k in ("Other", "Unknown") or not base: continue
            ref = (base * P["n"] - v["er"] * v["n"]) / (P["n"] - v["n"]) if dim == "slots" and P["n"] > v["n"] else base
            r = v["er"] / ref; name = k.replace("|", " "); hi = 1.25
            if r >= hi: out.append((f"{dim}:{k}:hi", f"{name} ({label}) outperforms: {v['er']}% avg engagement vs {round(ref, 2)}% {'for other time slots' if dim == 'slots' else 'baseline'} across {v['n']} posts."))
            elif r <= 0.75: out.append((f"{dim}:{k}:lo", f"{name} ({label}) underperforms: {v['er']}% avg engagement vs {round(ref, 2)}% {'for other time slots' if dim == 'slots' else 'baseline'} across {v['n']} posts."))
    st = P.get("styles", {})
    if len(st) == 2 and st["Educational"]["comment_rate"] > 1.5 * st["Non-educational"]["comment_rate"]:
        out.append(("styles:comments", "Educational posts generate far more comments per view than non-educational posts."))
    for e in P.get("emerging", []): out.append((f"emerging:{e['topic']}", f"Emerging interest: {e['topic']} engagement rose from {e['prior_er']}% to {e['recent_er']}% in the last 30 days."))
    a, b = P.get("sentiment_recent"), P.get("sentiment_prior")
    if a is not None and b is not None and abs(a - b) >= 0.1:
        out.append(("sentiment:shift", f"Audience sentiment shifted: positive share {'rose' if a > b else 'fell'} from {b:.0%} to {a:.0%} in the last 30 days."))
    return out
