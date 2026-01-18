from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ytmusicapi import YTMusic

app = FastAPI()

# This allows your HTML page to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

yt = YTMusic()

@app.get("/search")
def search(q: str):
    # Searches YouTube Music for songs only
    results = yt.search(q, filter="songs")
    # Return a clean list of songs with just the data we need
    songs = []
    for r in results:
        songs.append({
            "title": r.get("title"),
            "artist": r.get("artists")[0].get("name") if r.get("artists") else "Unknown",
            "videoId": r.get("videoId"),
            "thumbnail": r.get("thumbnails")[-1].get("url")
        })
    return songs
