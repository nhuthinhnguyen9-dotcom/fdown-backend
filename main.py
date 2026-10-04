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

    try:
        # Sử dụng API Rapid/Cobalt/SnapSave bypass Facebook
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Thử gọi API lấy link gốc Facebook
        api_res = requests.post(
            "https://co.wuk.sh/api/json",
            json={"url": url},
            headers=headers,
            timeout=12
        )
        
        data = api_res.json()
        
        if api_res.status_code == 200 and "url" in data:
            return {
                "status": "success",
                "title": "Facebook Video",
                "url": data["url"]
            }
            
        # Phương án dự phòng 2 nếu API 1 bị quá tải
        fb_api = requests.get(f"https://api.v2.snapsave.app/api/download?url={url}", headers=headers, timeout=10)
        if fb_api.status_code == 200:
            fb_data = fb_api.json()
            if "data" in fb_data and len(fb_data["data"]) > 0:
                video_link = fb_data["data"][0].get("url") or fb_data["data"][0].get("file")
                if video_link:
                    return {
                        "status": "success",
                        "title": "Facebook Video HD",
                        "url": video_link
                    }

        raise HTTPException(status_code=400, detail="Facebook đã chặn kết nối hoặc video này bị giới hạn quyền riêng tư/quốc gia.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")
