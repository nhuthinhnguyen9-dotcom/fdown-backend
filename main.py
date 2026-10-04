from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

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

    # Cấu hình giả lập Trình duyệt thật để tránh bị Facebook chặn
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Mode': 'navigate',
        },
        'force_generic_extractor': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            video_url = info.get('url')
            if not video_url and 'formats' in info and len(info['formats']) > 0:
                video_url = info['formats'][-1].get('url')

            if not video_url:
                raise HTTPException(status_code=400, detail="Video này ở chế độ riêng tư hoặc yêu cầu đăng nhập Facebook!")

            return {
                "status": "success",
                "title": info.get('title', 'Facebook Video'),
                "url": video_url
            }
    except Exception as e:
        error_msg = str(e)
        if "login" in error_msg.lower() or "redirect" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Video/Story này riêng tư hoặc yêu cầu đăng nhập tài khoản Facebook mới xem được!")
        raise HTTPException(status_code=500, detail=f"Lỗi bóc tách: {error_msg}")
