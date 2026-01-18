import os
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from ytmusicapi import YTMusic
from pytubefix import YouTube

# --- DATABASE CONFIG ---
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://vofodb_user:Y7MQfAWwEtsiHQLiGHFV7ikOI2ruTv3u@dpg-d5lm4ongi27c7390kq40-a/vofodb")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- MODELS ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)

class LikedSong(Base):
    __tablename__ = "liked_songs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    song_id = Column(String)
    title = Column(String)
    artist = Column(String)
    thumbnail = Column(String)

Base.metadata.create_all(bind=engine)

# --- APP INIT ---
app = FastAPI()
yt = YTMusic()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- AUTH ENDPOINTS ---
@app.post("/api/auth/register")
async def register(data: dict, db: Session = Depends(get_db)):
    print(f"DEBUG: Registering user {data.get('username')}")
    try:
        hashed = pwd_context.hash(data['password'])
        user = User(username=data['username'], password=hashed)
        db.add(user)
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise HTTPException(status_code=400, detail="User already exists")

@app.post("/api/auth/login")
async def login(data: dict, db: Session = Depends(get_db)):
    print(f"DEBUG: Login attempt for {data.get('username')}")
    user = db.query(User).filter(User.username == data['username']).first()
    if not user or not pwd_context.verify(data['password'], user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"success": True, "user_id": user.id, "username": user.username}

# --- MUSIC ENDPOINTS ---
@app.get("/api/trending")
async def trending():
    try:
        songs = yt.get_charts(country="IN")['songs']['items']
        return [{"id": s['videoId'], "title": s['title'], "artist": s['artists'][0]['name'], "thumbnail": s['thumbnails'][-1]['url']} for s in songs[:15]]
    except Exception as e:
        return []

@app.get("/api/search")
async def search(q: str):
    results = yt.search(q, filter="songs")
    return [{"id": r['videoId'], "title": r['title'], "artist": r['artists'][0]['name'], "thumbnail": r['thumbnails'][-1]['url']} for r in results]

@app.get("/api/stream")
async def stream(id: str):
    try:
        # Pytubefix handling
        url = YouTube(f"https://youtube.com/watch?v={id}").streams.filter(only_audio=True).first().url
        return {"url": url}
    except Exception as e:
        print(f"STREAM ERROR: {e}")
        raise HTTPException(status_code=500)

@app.post("/api/like")
async def toggle_like(data: dict, db: Session = Depends(get_db)):
    existing = db.query(LikedSong).filter(LikedSong.user_id == data['user_id'], LikedSong.song_id == data['id']).first()
    if existing:
        db.delete(existing)
        db.commit()
        return {"status": "unliked"}
    
    new_like = LikedSong(
        user_id=data['user_id'], 
        song_id=data['id'], 
        title=data['title'], 
        artist=data['artist'], 
        thumbnail=data['thumbnail']
    )
    db.add(new_like)
    db.commit()
    return {"status": "liked"}

@app.get("/api/library/{user_id}")
async def get_library(user_id: int, db: Session = Depends(get_db)):
    likes = db.query(LikedSong).filter(LikedSong.user_id == user_id).all()
    return [{"id": l.song_id, "title": l.title, "artist": l.artist, "thumbnail": l.thumbnail} for l in likes]

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
