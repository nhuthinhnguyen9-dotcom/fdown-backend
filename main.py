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
        # Sử dụng API bóc tách Facebook chuyên dụng
        api_url = f"https://api.v2.snapsave.app/api/download?url={url}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://snapsave.app/'
        }
        
        # Gọi sang API giải mã Facebook
        response = requests.get(f"https://fdown.net/download.php", params={'url': url}, headers=headers, timeout=10)
        
        # Nếu muốn dùng giải pháp thuần Python bóc tách link gốc HD/SD
        import re
        html = response.text
        
        # Rút trích link HD hoặc SD từ FB
        hd_match = re.search(r'hd_src:"([^"]+)"', html)
        sd_match = re.search(r'sd_src:"([^"]+)"', html)
        
        video_url = None
        if hd_match:
            video_url = hd_match.group(1)
        elif sd_match:
            video_url = sd_match.group(1)
            
        if not video_url:
            raise HTTPException(status_code=400, detail="Không thể bóc tách link video này. Vui lòng đảm bảo đây là Video/Reels công khai!")

        return {
            "status": "success",
            "title": "Facebook Video",
            "url": video_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ: {str(e)}")
