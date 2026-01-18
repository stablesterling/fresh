from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from ytmusicapi import YTMusic

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

yt = YTMusic()

# FIX: Stop the favicon.ico 404 error
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(content="", status_code=204)

# Serve the frontend
@app.get("/", response_class=HTMLResponse)
def read_root():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>index.html not found!</h1>"

# Search logic
@app.get("/search")
def search(q: str):
    results = yt.search(q, filter="songs")
    songs = []
    for r in results:
        songs.append({
            "title": r.get("title"),
            "artist": r.get("artists")[0].get("name") if r.get("artists") else "Unknown",
            "videoId": r.get("videoId"),
            "thumbnail": r.get("thumbnails")[-1].get("url") if r.get("thumbnails") else ""
        })
    return songs
