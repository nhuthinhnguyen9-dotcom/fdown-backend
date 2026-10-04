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

    clean_url = url.strip()

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
            'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        },
        'check_formats': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=False)
            
            title = info.get('title', 'Facebook Video')
            duration = info.get('duration_string') or info.get('duration') or 'N/A'
            thumbnail = info.get('thumbnail', '')
            
            formats_list = []
            
            # 1. Bóc tách Video HD & SD
            if 'formats' in info and len(info['formats']) > 0:
                for f in info['formats']:
                    f_url = f.get('url')
                    if not f_url:
                        continue
                    height = f.get('height') or 0
                    format_id = f.get('format_id', '')
                    
                    if height >= 720 or 'hd' in format_id.lower():
                        formats_list.append({
                            "quality": "720P (HD)",
                            "desc": "Chất lượng cao",
                            "ext": "MP4",
                            "type": "direct",
                            "url": f_url
                        })
                    elif height > 0 or 'sd' in format_id.lower():
                        formats_list.append({
                            "quality": "360P (SD)",
                            "desc": "Chất lượng thường",
                            "ext": "MP4",
                            "type": "direct",
                            "url": f_url
                        })
            
            # Link mặc định nếu không chia được HD/SD
            default_url = info.get('url')
            if not formats_list and default_url:
                formats_list.append({
                    "quality": "720P (HD)",
                    "desc": "Chất lượng cao",
                    "ext": "MP4",
                    "type": "direct",
                    "url": default_url
                })
                formats_list.append({
                    "quality": "360P (SD)",
                    "desc": "Chất lượng thường",
                    "ext": "MP4",
                    "type": "direct",
                    "url": default_url
                })

            # 2. Định dạng Âm thanh (Audio MP3)
            audio_url = default_url or (formats_list[0]['url'] if formats_list else '')
            if audio_url:
                formats_list.append({
                    "quality": "MP3",
                    "desc": "Âm thanh",
                    "ext": "MP3",
                    "type": "render",
                    "url": audio_url
                })

            # 3. Định dạng Bổ sung: Tải Hình Ảnh Thumbnail (Ảnh bìa Video)
            if thumbnail:
                formats_list.append({
                    "quality": "IMAGE",
                    "desc": "Hình ảnh thumbnail",
                    "ext": "JPG",
                    "type": "direct",
                    "url": thumbnail
                })

            if not formats_list:
                raise HTTPException(status_code=400, detail="Video riêng tư hoặc không tìm thấy liên kết tải.")

            return {
                "status": "success",
                "title": title,
                "duration": str(duration),
                "thumbnail": thumbnail,
                "formats": formats_list
            }
    except Exception as e:
        err = str(e)
        if "Unsupported URL" in err:
            raise HTTPException(status_code=400, detail="Đường dẫn không hợp lệ hoặc ở chế độ Riêng tư.")
        raise HTTPException(status_code=500, detail=f"Lỗi bóc tách: {err}")
