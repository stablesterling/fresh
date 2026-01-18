from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from ytmusicapi import YTMusic
import yt_dlp
import uuid
import os

app = FastAPI()
yt = YTMusic()

# Mock Database (In-memory)
db = {"users": {}, "sessions": {}, "likes": {}}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- AUTHENTICATION ---
@app.post("/api/auth/register")
async def register(data: dict):
    u, p = data.get("username"), data.get("password")
    if not u or u in db["users"]: return {"success": False, "error": "Identity already exists"}
    db["users"][u] = p
    db["likes"][u] = []
    return {"success": True}

@app.post("/api/auth/login")
async def login(data: dict, response: Response):
    u, p = data.get("username"), data.get("password")
    if db["users"].get(u) == p:
        sid = str(uuid.uuid4())
        db["sessions"][sid] = u
        response.set_cookie(key="sid", value=sid, httponly=True, samesite="lax")
        return {"success": True}
    return {"success": False, "error": "Invalid Encryption"}

@app.get("/api/auth/status")
async def status(request: Request):
    sid = request.cookies.get("sid")
    user = db["sessions"].get(sid)
    return {"logged_in": bool(user), "user": user}

@app.get("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie("sid")
    return {"success": True}

# --- MUSIC LOGIC ---
@app.get("/api/search")
async def search(q: str):
    results = yt.search(q, filter="songs")
    return [{"id": r['videoId'], "title": r['title'], "artist": r['artists'][0]['name'], "thumbnail": r['thumbnails'][-1]['url']} for r in results]

@app.post("/api/play")
async def play(data: dict):
    video_id = data.get("url")
    # Using yt-dlp to get the direct audio stream URL
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'cookiefile': None # Prevents cookie errors on Render
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            stream_url = info['url']
            return {"stream_url": stream_url, "is_hls": ".m3u8" in stream_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/like")
async def toggle_like(request: Request, song: dict):
    sid = request.cookies.get("sid")
    user = db["sessions"].get(sid)
    if not user: raise HTTPException(status_code=401)
    
    user_likes = db["likes"][user]
    existing = next((s for s in user_likes if s['id'] == song['id']), None)
    
    if existing:
        user_likes.remove(existing)
        return {"status": "unliked"}
    else:
        user_likes.append(song)
        return {"status": "liked"}

@app.get("/api/library")
async def get_library(request: Request):
    sid = request.cookies.get("sid")
    user = db["sessions"].get(sid)
    return db["likes"].get(user, [])

# Serve Frontend
@app.get("/", response_class=HTMLResponse)
def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(content="", status_code=204)
