import os, csv, io
from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import HTTPException as _H
from pydantic import BaseModel, Field
import agent, analytics, learning, memory
from csvio import parse_row
from db import Session, Post, Learning, Brand, Base, engine, post_dict

app = FastAPI(title="SocialMind")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatIn(BaseModel):
    message: str = Field(min_length=1); history: list[dict] = []
class OutcomeIn(BaseModel):
    recommendation_id: int; views: int = Field(gt=0); likes: int = Field(ge=0); comments: int = Field(ge=0); shares: int = Field(ge=0)
class FeedbackIn(BaseModel):
    recommendation_id: int; action: str = Field(pattern="^(accepted|rejected)$"); note: str = ""
class BrandIn(BaseModel):
    name: str = ""; niche: str = ""; audience: str = ""; tone: str = ""; goals: str = ""
class PostIn(BaseModel):
    date: str; time: str = ""; platform: str = "Unknown"; topic: str; format: str; caption: str = ""
    views: int = Field(gt=0); likes: int = Field(ge=0); comments: int = Field(ge=0); shares: int = Field(ge=0); sentiment: str = "unknown"

@app.exception_handler(Exception)
async def _any(_, e: Exception):
    return JSONResponse({"detail": f"{type(e).__name__}: {str(e)[:400]}"}, status_code=500)

@app.get("/health")
def health():
    """Read-only recall against Hindsight so setup problems show up immediately."""
    try:
        memory.search("connectivity check", 1)
        return {"hindsight": True}
    except Exception as e:
        return {"hindsight": False, "error": f"{type(e).__name__}: {str(e)[:400]}"}

@app.post("/chat")
def chat(b: ChatIn, bg: BackgroundTasks):
    try: r = agent.chat(b.message, b.history)
    except Exception as e: raise HTTPException(502, f"Agent error: {e}")
    bg.add_task(memory.remember, f"The user told/asked SocialMind: \"{b.message}\"", "user_conversation")
    if r["recommendation"]:
        x = r["recommendation"]
        bg.add_task(memory.remember, f"SocialMind recommended '{x['topic']}' as a {x['format']} at {x['best_time']}. Reasons: {'; '.join(x['reasons'])}", "recommendation")
    return r

@app.post("/outcome")
def outcome(b: OutcomeIn):
    try: return learning.record_outcome(**b.model_dump())
    except ValueError as e: raise HTTPException(404, str(e))

@app.post("/feedback")
def feedback(b: FeedbackIn):
    try: learning.feedback(b.recommendation_id, b.action, b.note); return {"ok": True}
    except ValueError as e: raise HTTPException(404, str(e))

@app.get("/brand")
def get_brand():
    with Session() as s:
        b = s.query(Brand).first(); return b.data if b else {}

@app.put("/brand")
def put_brand(b: BrandIn):
    learning.save_brand(b.model_dump()); return {"ok": True}

@app.post("/posts")
def add_post(b: PostIn):
    try: return learning.ingest([parse_row({k: str(v) for k, v in b.model_dump().items()})])
    except ValueError as e: raise HTTPException(422, str(e))

@app.post("/import/csv")
async def import_csv(file: UploadFile):
    rows = []
    for i, r in enumerate(csv.DictReader(io.StringIO((await file.read()).decode("utf-8-sig"))), start=2):
        try: rows.append(parse_row(r))
        except ValueError as e: raise HTTPException(422, f"Row {i}: {e}")
    if not rows: raise HTTPException(422, "CSV has no rows")
    return learning.ingest(rows)

@app.post("/reset")
def reset():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine); memory.reset(); return {"ok": True}

@app.get("/audience-dna")
def dna():
    import datetime as dt
    with Session() as s:
        P = analytics.patterns([post_dict(p) for p in s.query(Post).all()])
        fresh = dt.datetime.utcnow() - dt.timedelta(minutes=10)
        return {**P, "recently_updated": s.query(Learning).filter(Learning.created > fresh).count() > 0}

@app.get("/timeline")
def timeline():
    with Session() as s:
        return [{"date": l.created, "text": l.text} for l in s.query(Learning).order_by(Learning.created.desc())]

@app.get("/stats")
def stats():
    with Session() as s:
        posts = [post_dict(p) for p in s.query(Post).all()]; n_l = s.query(Learning).count(); weekly = {}
        for p in posts: w = p["date"].strftime("%G-W%V"); weekly[w] = weekly.get(w, 0) + p["views"]
        return {"total_posts": len(posts), "avg_engagement": analytics.patterns(posts).get("baseline", 0),
                "memories": len(posts) + n_l, "weekly_views": dict(sorted(weekly.items()))}

@app.get("/", include_in_schema=False)
def home(): return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))
