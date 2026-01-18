from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from ytmusicapi import YTMusic
from pytubefix import YouTube
import os

app = FastAPI()
yt = YTMusic()

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

@app.get("/api/trending")
async def trending():
    try:
        songs = yt.get_charts(country="IN")['songs']['items']
        return [{"id": s['videoId'], "title": s['title'], "artist": s['artists'][0]['name'], "thumbnail": s['thumbnails'][-1]['url']} for s in songs[:15]]
    except Exception:
        return []

@app.get("/api/search")
async def search(q: str):
    try:
        results = yt.search(q, filter="songs")
        return [{"id": r['videoId'], "title": r['title'], "artist": r['artists'][0]['name'], "thumbnail": r['thumbnails'][-1]['url']} for r in results]
    except Exception:
        return []

@app.get("/api/stream")
async def get_stream(id: str):
    try:
        url = f"https://www.youtube.com/watch?v={id}"
        
        # KEY FIX: Using OAuth and 'ANDROID' client to bypass Render IP blocks
        yt_video = YouTube(
            url, 
            use_oauth=True, 
            allow_oauth_cache=True,
            client='ANDROID' 
        )
        
        # Filter for m4a for best mobile background compatibility
        audio_stream = yt_video.streams.filter(only_audio=True, file_extension='m4a').first()
        
        if audio_stream:
            # We return the direct URL which remains valid for a few hours
            return {"url": audio_stream.url}
            
        raise HTTPException(status_code=404, detail="Audio stream not found")
    except Exception as e:
        print(f"Streaming Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
def home():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "index.html not found"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
