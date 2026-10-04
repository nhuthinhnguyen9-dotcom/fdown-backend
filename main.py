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

    # Lọc sạch tham số rác từ Facebook URL
    clean_url = url.split('?')[0].split('&')[0]

    # Giả lập Trình duyệt Safari di động để bypass tường lửa
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        },
        'check_formats': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=False)
            
            video_url = info.get('url')
            if not video_url and 'formats' in info and len(info['formats']) > 0:
                video_url = info['formats'][-1].get('url')

            if not video_url:
                raise HTTPException(status_code=400, detail="Video riêng tư hoặc yêu cầu đăng nhập Facebook.")

            return {
                "status": "success",
                "title": info.get('title', 'Facebook Video'),
                "url": video_url
            }
    except Exception as e:
        err = str(e)
        if "Unsupported URL" in err:
            raise HTTPException(status_code=400, detail="Đường dẫn không hợp lệ hoặc Video/Reels ở chế độ Riêng tư.")
        raise HTTPException(status_code=500, detail=f"Lỗi bóc tách: {err}")
