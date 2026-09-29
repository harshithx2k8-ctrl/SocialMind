"""Thin wrapper over Hindsight (retain / recall / reflect).
hindsight-client's sync methods bind an aiohttp session to the calling thread's event loop. FastAPI runs each request on a
different worker thread, which breaks that ('Timeout context manager should be used inside a task'). So every Hindsight
call runs on ONE dedicated thread, and the client is created there."""
import os, time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from hindsight_client import Hindsight
load_dotenv()
BASE = os.getenv("HINDSIGHT_BANK_ID", "socialmind-brand")
_FILE = os.path.join(os.path.dirname(__file__), ".bank")
BANK = open(_FILE).read().strip() if os.path.exists(_FILE) else BASE
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="hindsight")
_client: Hindsight | None = None
_ready = False

def _run(fn):
    return _pool.submit(fn).result()

def _c() -> Hindsight:  # only ever called on the hindsight thread
    global _client, _ready
    if _client is None:
        _client = Hindsight(base_url=os.getenv("HINDSIGHT_URL", "http://localhost:8888"), api_key=os.getenv("HINDSIGHT_API_KEY") or None)
    if not _ready:
        try:
            _client.create_bank(bank_id=BANK, name="SocialMind brand memory",
                mission="Remember what content worked for this brand's audience, why, and how it changed over time.")
        except Exception:
            pass  # exists already; retain also creates banks on demand
        _ready = True
    return _client

def reset() -> None:
    """Fresh, empty memory bank = a brand-new brand."""
    global BANK, _ready
    BANK = f"{BASE}-{int(time.time())}"; _ready = False
    open(_FILE, "w").write(BANK)

def remember(text: str, context: str = "experience", when=None) -> None:
    _run(lambda: _c().retain(bank_id=BANK, content=text, context=context, timestamp=when))

def remember_many(items: list[dict]) -> None:
    for i in range(0, len(items), 25):
        chunk = items[i:i + 25]; _run(lambda: _c().retain_batch(bank_id=BANK, items=chunk))

def search(query: str, limit: int = 12) -> list[str]:
    return [r.text for r in _run(lambda: _c().recall(bank_id=BANK, query=query)).results][:limit]

def reflect(query: str) -> str:
    return _run(lambda: _c().reflect(bank_id=BANK, query=query)).text
