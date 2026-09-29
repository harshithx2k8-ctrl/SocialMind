# SocialMind

**An AI social-media strategist that learns *your* audience.**

SocialMind doesn't give generic advice. You give it your brand profile and your past posts; it analyzes them, stores what it learns in [Hindsight](https://hindsight.vectorize.io) long-term memory, and uses that memory to answer every question. Each new post, result and piece of feedback makes the next recommendation more personal.

```
your posts ─► analysis ─► Hindsight memory ─► personalized answer ─► you post / give feedback ─► new memory
     ▲                                                                                              │
     └──────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Features

- **Brand profile:** name, niche, audience, tone and goals, remembered and applied to every answer.
- **Post analysis:** import a CSV or log posts by hand. Patterns are derived from your data only: top and weak topics, formats, posting windows, educational vs. non-educational content, sentiment shifts, emerging interests.
- **Memory-grounded chat:** before each answer, relevant memories are retrieved from Hindsight and given to the agent. If memory is thin, it says so.
- **Recommendation card:** topic, format, best time, how many memories it used, and the reasons behind it.
- **Feedback loop:** mark a recommendation "I'll post this" or "Not for us" (with a reason), then record the real results. Both are stored as new memories.
- **Audience DNA dashboard and Memory Timeline** show what the agent has learned and when.

## Stack

| Layer | Tech |
|---|---|
| Frontend | Single-page HTML/CSS/JS served by FastAPI (Obsidian & Lime glass design) |
| Backend | Python, FastAPI |
| Agent | Any OpenAI-compatible LLM with tool calling (default: Groq) |
| Memory | Hindsight by Vectorize |
| Database | SQLite by default, PostgreSQL optional |

## Quick start

**You need:** Python 3.10+, an LLM API key (a free [Groq](https://console.groq.com) key works), and a running Hindsight (step 2).

### 1. Get the code and configure

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate      Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env                 # Windows: copy ..\.env.example .env
```

Edit `backend/.env`:

```
LLM_API_KEY=your-llm-key
LLM_MODEL=openai/gpt-oss-120b
HINDSIGHT_URL=http://localhost:8888
```

On Windows you can skip the manual steps and just run `backend\run.bat`.

### 2. Start Hindsight (pick one)

**Hindsight Cloud (nothing to install):** sign up at [ui.hindsight.vectorize.io](https://ui.hindsight.vectorize.io/signup), then set `HINDSIGHT_URL` and `HINDSIGHT_API_KEY` in `.env` from your dashboard.

**Docker (local):** run in a separate terminal and leave it open (one line on Windows; use `$HOME` instead of `%USERPROFILE%` on Mac/Linux):

```
docker run --rm -it --pull always -p 8888:8888 -p 9999:9999 -e HINDSIGHT_API_LLM_PROVIDER=groq -e HINDSIGHT_API_LLM_API_KEY=your-groq-key -e HINDSIGHT_API_LLM_MODEL=openai/gpt-oss-20b -v %USERPROFILE%\.hindsight-docker:/home/hindsight/.pg0 ghcr.io/vectorize-io/hindsight:latest
```

Hindsight uses its own LLM to extract memories, so it needs a key and model of its own. The API is at `localhost:8888` and its UI at `localhost:9999`.

### 3. Run SocialMind

```bash
uvicorn main:app --reload
```

Open **http://localhost:8000**. The status tag in the header should read **Hindsight · online**. You can also check `http://localhost:8000/health`.

## Using it

1. **Brand & Data tab:** save your brand profile, then import a CSV and/or log posts.
2. **Agent Chat:** ask *"What should I post tomorrow?"*, *"What does my audience like?"*, *"Why are you recommending this?"*, and so on.
3. On a recommendation card, choose **I'll post this** or **Not for us**. After publishing, enter the real views, likes, comments and shares and click **Record result**.
4. Check the **Dashboard** and **Memory Timeline** to see what changed. Ask *"What have you learned about our audience?"*

### CSV format

| Column | Required | Notes |
|---|---|---|
| `date` | yes | `YYYY-MM-DD`, or `YYYY-MM-DD HH:MM` |
| `topic` | yes | e.g. `AI`, `Career` |
| `format` | yes | e.g. `Reel`, `Carousel`, `Image` |
| `views` | yes | must be > 0 |
| `time` | no | `HH:MM`; needed for posting-time insights |
| `platform`, `caption` | no | |
| `likes`, `comments`, `shares` | no | default 0 |
| `sentiment` | no | `positive`, `neutral`, `negative`; otherwise "unknown" |
| `engagement_rate` | no | computed as (likes + comments + shares) / views if missing |

## How it works

- **Ingest (`learning.py`):** every post, lesson, recommendation, feedback item and outcome is retained in Hindsight as a plain-language experience. Postgres/SQLite holds structured rows for stats and charts.
- **Analysis (`analytics.py`):** compares topics, formats, time slots and styles to your baseline engagement and derives lessons. It needs at least 4 posts per group (3 for topic + format combinations), so tiny datasets won't produce many.
- **Retrieval (`agent.py`):** each turn, Hindsight is searched with the user's message and the brand profile is attached. The LLM can call these tools: `search_memory`, `remember_experience`, `get_audience_insights`, `analyze_post_performance`, `get_historical_patterns`, `generate_content_recommendation`, `record_post_outcome`.
- **Memory client (`memory.py`):** all Hindsight calls run on one dedicated thread. The client is async internally, and calling it from FastAPI's changing worker threads fails.

## Project layout

```
socialmind/
├── .env.example
├── README.md
└── backend/
    ├── main.py          # FastAPI routes
    ├── agent.py         # LLM tool-calling loop + tools
    ├── learning.py      # ingest, outcomes, feedback -> Hindsight
    ├── memory.py        # Hindsight wrapper
    ├── analytics.py     # pattern and lesson derivation
    ├── csvio.py         # forgiving CSV/form row parser
    ├── db.py            # SQLAlchemy models
    ├── run.bat          # Windows one-click start
    └── static/index.html
```

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/chat` | Ask the agent |
| GET/PUT | `/brand` | Read / save brand profile |
| POST | `/posts` | Log one post |
| POST | `/import/csv` | Import posts from CSV |
| POST | `/feedback` | Accept / reject a recommendation |
| POST | `/outcome` | Record real results |
| GET | `/audience-dna`, `/timeline`, `/stats` | Dashboard data |
| GET | `/health` | Check Hindsight connectivity (read-only) |
| POST | `/reset` | Erase posts and start a fresh memory bank |

Interactive docs: http://localhost:8000/docs

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `LLM_BASE_URL` | OpenAI-compatible endpoint | Groq |
| `LLM_API_KEY` | LLM key | none |
| `LLM_MODEL` | Model (must support tool calling) | `openai/gpt-oss-120b` |
| `HINDSIGHT_URL` / `HINDSIGHT_API_KEY` | Hindsight endpoint / key (cloud only) | `http://localhost:8888` |
| `HINDSIGHT_BANK_ID` | Base name of the memory bank | `socialmind-brand` |
| `DATABASE_URL` | Postgres URL; also `pip install psycopg2-binary` | SQLite file |

## Troubleshooting

| Symptom | Fix |
|---|---|
| Status shows **Hindsight · offline** | Hindsight isn't running or `HINDSIGHT_URL` is wrong. Start it (step 2). |
| Save or chat fails with a model 404 | The model was retired. Set `LLM_MODEL=openai/gpt-oss-120b` (app) and `HINDSIGHT_API_LLM_MODEL` (Hindsight), then restart both. |
| "Timeout context manager should be used inside a task" | Old `memory.py`. Use the current version. |
| `No module named 'psycopg'` | Leave `DATABASE_URL` empty for SQLite, or `pip install psycopg2-binary`. |
| Chat sounds generic | Add more posts, or wait a moment for Hindsight to finish indexing. |
| Start over | Click **Reset brand**, or delete `backend/socialmind.db`. |

## Limitations

- Posting-time insights need a time of day in your data; without it, only topic and format insights are produced.
- Timeline dates show when a lesson was learned, not when the underlying posts happened.
- Single brand, no user accounts or authentication. Run locally or behind your own auth.
- No automated tests yet.
- Hindsight setup details and model names change; check its docs if something differs.
