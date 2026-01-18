from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from ytmusicapi import YTMusic
from pytubefix import YouTube

app = FastAPI()
yt = YTMusic()

# Allow frontend to communicate with backend
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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
        # Fetches the direct URL to the audio file on YouTube's servers
        yt_video = YouTube(f"https://www.youtube.com/watch?v={id}")
        audio_stream = yt_video.streams.filter(only_audio=True).first()
        if audio_stream:
            return {"url": audio_stream.url}
        raise HTTPException(status_code=404, detail="Audio stream not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
