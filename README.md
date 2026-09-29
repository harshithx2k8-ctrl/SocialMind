# SocialMind: an agent that learns YOUR audience (Hindsight)
Real loop: your posts -> analysis -> Hindsight memory -> personalized answers -> feedback/results -> new memory.

## Run (Windows): backend\run.bat, edit backend\.env (LLM_API_KEY, LLM_MODEL=openai/gpt-oss-120b, HINDSIGHT_URL), open http://localhost:8000
Start Hindsight first (Docker, see Hindsight docs; port 8888).

## Use it
1. Brand & Data: save your brand profile, import past posts (CSV) and/or log posts one by one.
2. Chat: every turn retrieves Hindsight memories first; your messages, recommendations, feedback ("I'll post this"/"Not for us")
   and recorded results are retained as new memories.
3. Dashboard / Timeline show what has been learned. Lessons are derived from YOUR data only (analytics.py).
Note: insights on posting time need a time of day in your data. Delete socialmind.db to fully reset SQLite.
