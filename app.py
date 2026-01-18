import os
import uvicorn
import bcrypt
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from ytmusicapi import YTMusic
from pytubefix import YouTube

# --- DATABASE CONFIG (SQLite) ---
DATABASE_URL = "sqlite:///./vofo.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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

# --- AUTH HELPERS ---
def hash_password(password: str):
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str):
    pwd_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)

app = FastAPI()
yt = YTMusic()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- AUTH ROUTES ---
@app.post("/api/auth/register")
async def register(data: dict, db: Session = Depends(get_db)):
    if not data.get('username') or not data.get('password'):
        raise HTTPException(400, "Fields required")
    
    if db.query(User).filter(User.username == data['username']).first():
        raise HTTPException(400, "User exists")
    
    hashed_pwd = hash_password(data['password'])
    user = User(username=data['username'], password=hashed_pwd)
    db.add(user)
    db.commit()
    return {"success": True}

@app.post("/api/auth/login")
async def login(data: dict, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data['username']).first()
    if not user or not verify_password(data['password'], user.password):
        raise HTTPException(401, "Invalid credentials")
    return {"success": True, "user_id": user.id, "username": user.username}

# --- MUSIC ROUTES ---
@app.get("/api/trending")
async def trending():
    try:
        songs = yt.get_charts(country="IN")['songs']['items']
        return [{"id": s['videoId'], "title": s['title'], "artist": s['artists'][0]['name'], "thumbnail": s['thumbnails'][-1]['url']} for s in songs[:15]]
    except: return []

@app.get("/api/search")
async def search(q: str):
    try:
        results = yt.search(q, filter="songs")
        return [{"id": r['videoId'], "title": r['title'], "artist": r['artists'][0]['name'], "thumbnail": r['thumbnails'][-1]['url']} for r in results]
    except: return []

@app.get("/api/stream")
async def stream(id: str):
    try:
        url = YouTube(f"https://youtube.com/watch?v={id}").streams.filter(only_audio=True).first().url
        return {"url": url}
    except: raise HTTPException(500, "Streaming failed")

@app.post("/api/like")
async def toggle_like(data: dict, db: Session = Depends(get_db)):
    exist = db.query(LikedSong).filter(LikedSong.user_id == data['user_id'], LikedSong.song_id == data['id']).first()
    if exist:
        db.delete(exist); db.commit(); return {"status": "unliked"}
    db.add(LikedSong(user_id=data['user_id'], song_id=data['id'], title=data['title'], artist=data['artist'], thumbnail=data['thumbnail']))
    db.commit(); return {"status": "liked"}

@app.get("/api/library/{user_id}")
async def library(user_id: int, db: Session = Depends(get_db)):
    likes = db.query(LikedSong).filter(LikedSong.user_id == user_id).all()
    return [{"id": l.song_id, "title": l.title, "artist": l.artist, "thumbnail": l.thumbnail} for l in likes]

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("index.html", "r", encoding="utf-8") as f: return f.read()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
