import os, json
from dotenv import load_dotenv
from openai import OpenAI
import memory, analytics, learning
from db import Session, Post, Recommendation, Brand, post_dict
load_dotenv()
llm = OpenAI(base_url=os.getenv("LLM_BASE_URL"), api_key=os.getenv("LLM_API_KEY") or "missing")
MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

def _posts():
    with Session() as s: return [post_dict(p) for p in s.query(Post).all()]

def search_memory(query): return memory.search(query)
def remember_experience(text): memory.remember(text, context="agent_note"); return "stored"
def get_historical_patterns(): return analytics.patterns(_posts())
def get_audience_insights():
    return {"hindsight_reflection": memory.reflect("What do we know about this audience: interests, formats, timing, sentiment, and how they changed?"),
            "emerging": analytics.patterns(_posts()).get("emerging", [])}
def analyze_post_performance(views, likes, comments, shares, topic="", format=""):
    P = analytics.patterns(_posts()); er = round((likes + comments + shares) / max(views, 1) * 100, 2)
    return {"engagement_rate": er, "baseline": P.get("baseline"), "topic_avg": P.get("topics", {}).get(topic, {}).get("er"), "format_avg": P.get("formats", {}).get(format, {}).get("er")}
def generate_content_recommendation(topic, topic_category, format, best_time, reasons):
    with Session() as s:
        r = Recommendation(payload={"topic": topic, "topic_category": topic_category, "format": format, "best_time": best_time, "reasons": reasons})
        s.add(r); s.commit(); rid = r.id
    return {"id": rid, "topic": topic, "format": format, "best_time": best_time, "reasons": reasons}
def record_post_outcome(recommendation_id, views, likes, comments, shares):
    return learning.record_outcome(recommendation_id, views, likes, comments, shares)

FN = {f.__name__: f for f in (search_memory, remember_experience, get_historical_patterns, get_audience_insights,
      analyze_post_performance, generate_content_recommendation, record_post_outcome)}
def _t(name, desc, props, req=()): return {"type": "function", "function": {"name": name, "description": desc, "parameters": {"type": "object", "properties": props, "required": list(req)}}}
S, I = {"type": "string"}, {"type": "integer"}
TOOLS = [
 _t("search_memory", "Semantic search of Hindsight long-term memory (past posts, lessons, outcomes). Call first for any question about this brand.", {"query": S}, ["query"]),
 _t("get_audience_insights", "Hindsight's synthesized understanding of the audience + emerging interests.", {}),
 _t("get_historical_patterns", "Computed stats by topic/format/time slot/style plus baseline engagement.", {}),
 _t("remember_experience", "Store a new observation in Hindsight.", {"text": S}, ["text"]),
 _t("analyze_post_performance", "Compare metrics to baseline.", {"views": I, "likes": I, "comments": I, "shares": I, "topic": S, "format": S}, ["views", "likes", "comments", "shares"]),
 _t("generate_content_recommendation", "Save the final recommendation shown on the card. reasons must each cite retrieved evidence.", {"topic": S, "topic_category": S, "format": S, "best_time": S, "reasons": {"type": "array", "items": S}}, ["topic", "topic_category", "format", "best_time", "reasons"]),
 _t("record_post_outcome", "Record actual results for a saved recommendation; triggers learning.", {"recommendation_id": I, "views": I, "likes": I, "comments": I, "shares": I}, ["recommendation_id", "views", "likes", "comments", "shares"]),
]
SYSTEM = ("You are SocialMind, a strategist that learns ONE brand's audience via Hindsight long-term memory. "
 "Each turn you receive the brand profile and memories already retrieved from Hindsight; call search_memory for more detail and get_historical_patterns for stats. "
 "Ground every claim in memories or computed stats; never invent numbers. If memory is empty or thin, say so and label advice as generic. "
 "If the user states a preference, constraint or piece of feedback, call remember_experience to store it. "
 "For 'what should I post' questions, finish by calling generate_content_recommendation, then explain briefly. Be concise.")

def _context(message: str) -> tuple[str, int]:
    mem = memory.search(message)
    with Session() as s:
        b = s.query(Brand).first(); brand = b.data if b else None
    return (f"Brand profile: {json.dumps(brand) if brand else 'not provided'}\nHindsight memories retrieved ({len(mem)}):\n"
            + ("\n".join("- " + m[:400] for m in mem) or "- (none yet: memory is empty)")), len(mem)

def chat(message: str, history: list[dict] | None = None) -> dict:
    ctx, used = _context(message)
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "system", "content": ctx}, *(history or []), {"role": "user", "content": message}]
    tools_called, rec = [], None
    for _ in range(7):
        m = llm.chat.completions.create(model=MODEL, messages=msgs, tools=TOOLS, temperature=0.3).choices[0].message
        msgs.append(m)
        if not m.tool_calls: return {"answer": m.content, "recommendation": rec, "memories_used": used, "tools": tools_called}
        for tc in m.tool_calls:
            try: out = FN[tc.function.name](**json.loads(tc.function.arguments or "{}"))
            except Exception as e: out = {"error": str(e)}
            tools_called.append(tc.function.name)
            if tc.function.name == "search_memory" and isinstance(out, list): used += len(out)
            if tc.function.name == "generate_content_recommendation" and "id" in out: rec = {**out, "memories_used": used}
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(out, default=str)[:6000]})
    return {"answer": "I couldn't finish reasoning; try again.", "recommendation": rec, "memories_used": used, "tools": tools_called}
