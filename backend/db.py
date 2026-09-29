import os, datetime as dt
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Text
from sqlalchemy.orm import declarative_base, sessionmaker
load_dotenv()
_url = os.getenv("DATABASE_URL") or "sqlite:///socialmind.db"
if _url.startswith("postgresql://"): _url = _url.replace("postgresql://", "postgresql+psycopg2://", 1)
engine = create_engine(_url)
Session = sessionmaker(engine)
Base = declarative_base()

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime); platform = Column(String); topic = Column(String)
    format = Column(String); caption = Column(Text)
    views = Column(Integer); likes = Column(Integer); comments = Column(Integer); shares = Column(Integer)
    engagement_rate = Column(Float); sentiment = Column(String)

class Learning(Base):  # mirror of lessons retained in Hindsight, powers the timeline
    __tablename__ = "learnings"
    id = Column(Integer, primary_key=True)
    created = Column(DateTime, default=dt.datetime.utcnow)
    key = Column(String, index=True); text = Column(Text)

class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True)
    created = Column(DateTime, default=dt.datetime.utcnow)
    payload = Column(JSON); outcome = Column(JSON, nullable=True)

class Brand(Base):
    __tablename__ = "brand"
    id = Column(Integer, primary_key=True); data = Column(JSON)

Base.metadata.create_all(engine)
COLS = ["date","platform","topic","format","caption","views","likes","comments","shares","engagement_rate","sentiment"]
def post_dict(p: Post) -> dict: return {"id": p.id, **{c: getattr(p, c) for c in COLS}}
