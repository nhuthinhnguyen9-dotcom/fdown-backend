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

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Referer': 'https://publer.io/'
    }

    # CỔNG 1: Dùng API Publer Downloader
    try:
        publer_res = requests.post(
            "https://publer.io/api/v1/tools/media-downloader",
            json={"url": url},
            headers=headers,
            timeout=10
        )
        if publer_res.status_code == 200:
            data = publer_res.json()
            if "data" in data and len(data["data"]) > 0:
                media_info = data["data"][0]
                video_url = media_info.get("url") or media_info.get("path")
                if video_url:
                    return {
                        "status": "success",
                        "title": "Facebook Video (HD)",
                        "url": video_url
                    }
    except Exception:
        pass

    # CỔNG 2: Dùng API TikWM / SSYoutube Engine Bypass
    try:
        ss_res = requests.post(
            "https://ssyoutube.com/api/convert",
            json={"url": url},
            headers=headers,
            timeout=10
        )
        if ss_res.status_code == 200:
            data = ss_res.json()
            if "url" in data and len(data["url"]) > 0:
                return {
                    "status": "success",
                    "title": data.get("meta", {}).get("title", "Facebook Video"),
                    "url": data["url"][0]["url"]
                }
    except Exception:
        pass

    # CỔNG 3: Dùng API SaveFrom Direct Engine
    try:
        sf_res = requests.post(
            "https://worker.sf-helper.com/project/sf-helper/api.php",
            data={"url": url},
            headers=headers,
            timeout=10
        )
        sf_data = sf_res.json()
        if isinstance(sf_data, list) and len(sf_data) > 0:
            url_list = sf_data[0].get("url", [])
            if len(url_list) > 0 and "url" in url_list[0]:
                return {
                    "status": "success",
                    "title": sf_data[0].get("meta", {}).get("title", "Facebook Video"),
                    "url": url_list[0]["url"]
                }
    except Exception:
        pass

    raise HTTPException(
        status_code=400, 
        detail="Máy chủ Facebook tạm thời thắt chặt kết nối. Vui lòng kiểm tra lại xem video có ở chế độ Công Khai (Public) không!"
    )
