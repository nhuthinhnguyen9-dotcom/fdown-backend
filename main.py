from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

app = FastAPI()

# Cấu hình CORS cho phép Vercel / Frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "ok", "message": "fbdowload API is running!"}

@app.get("/api/download")
def download_facebook(url: str = Query(..., description="Facebook Video URL")):
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            title = info.get('title', 'Facebook Video')
            thumbnail = info.get('thumbnail', '')
            duration = info.get('duration_string', '')
            
            formats_list = []
            
            # 1. Lấy link Video SD (mặc định)
            if 'url' in info:
                formats_list.append({
                    "quality": "SD 360P",
                    "desc": "Chất lượng tiêu chuẩn (SD)",
                    "ext": "MP4",
                    "url": info['url']
                })
            
            # 2. Lấy link Video HD (nếu có)
            for f in info.get('formats', []):
                if f.get('height') and f.get('height') >= 720:
                    formats_list.append({
                        "quality": f"HD {f.get('height')}P",
                        "desc": "Chất lượng cao (HD)",
                        "ext": "MP4",
                        "url": f.get('url')
                    })
                    break

            # 3. Lọc riêng luồng Audio thuần túy (vcodec == 'none') để không bị dính video
            audio_url = None
            for f in info.get('formats', []):
                # Chọn format chỉ có audio, không có hình ảnh
                if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                    audio_url = f.get('url')
                    break
            
            # Nếu không tìm thấy luồng audio riêng, dùng link mặc định
            if not audio_url and 'url' in info:
                audio_url = info['url']

            formats_list.append({
                "quality": "AUDIO MP3",
                "desc": "Âm thanh MP3 thuần túy",
                "ext": "MP3",
                "url": audio_url
            })

            return {
                "title": title,
                "thumbnail": thumbnail,
                "duration": duration,
                "formats": formats_list
            }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi bóc tách video: {str(e)}")
