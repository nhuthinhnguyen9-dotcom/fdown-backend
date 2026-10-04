from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "ok", "message": "FDown Server đang hoạt động!"}

@app.get("/api/download")
def download_video(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="Thiếu link video")

    # Danh sách các Máy chủ Cobalt API công khai để tự động chuyển tiếp nếu 1 server bận
    cobalt_servers = [
        "https://api.cobalt.tools",
        "https://cobalt-api.kwiatekm.com",
        "https://api.v2.snapsave.app"
    ]

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # Thử bóc tách qua Cobalt API
    for server in cobalt_servers[:2]:
        try:
            res = requests.post(
                server,
                json={"url": url},
                headers=headers,
                timeout=10
            )
            if res.status_code == 200:
                data = res.json()
                video_url = data.get("url") or data.get("picker", [{}])[0].get("url")
                if video_url:
                    return {
                        "status": "success",
                        "title": "Facebook Video HD",
                        "url": video_url
                    }
        except Exception:
            continue

    # Phương án dự phòng với TikWM/SnapSave cho Facebook
    try:
        res = requests.get(f"https://api.v2.snapsave.app/api/download?url={url}", headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if "data" in data and len(data["data"]) > 0:
                video_url = data["data"][0].get("url") or data["data"][0].get("file")
                if video_url:
                    return {
                        "status": "success",
                        "title": "Facebook Video",
                        "url": video_url
                    }
    except Exception:
        pass

    raise HTTPException(status_code=400, detail="Không thể bóc tách link video này. Vui lòng kiểm tra lại link hoặc chắc chắn video ở chế độ Công Khai!")
