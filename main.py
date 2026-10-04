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

    # Cấu hình ưu tiên lấy video nét nhất
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'bestvideo+bestaudio/best',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
            
            # Duyệt qua các định dạng khả dụng
            formats = info.get('formats', [])
            
            # Lấy link chất lượng cao nhất có thể
            best_url = info.get('url')
            
            # Tìm link HD chuẩn (720p / 1080p)
            hd_url = None
            sd_url = None
            
            for f in formats:
                f_url = f.get('url')
                if not f_url:
                    continue
                height = f.get('height') or 0
                format_id = f.get('format_id', '')
                
                # Ưu tiên lấy định dạng có tiếng + hình kết hợp sẵn
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    if height >= 720 or 'hd' in format_id.lower():
                        hd_url = f_url
                    elif height > 0 or 'sd' in format_id.lower():
                        sd_url = f_url

            # Gán fallback nếu không tách riêng được
            if not hd_url:
                hd_url = best_url
            if not sd_url:
                sd_url = best_url or hd_url

            # 1. Dòng HD (720P/1080P)
            formats_list.append({
                "quality": "720P (HD)",
                "desc": "Chất lượng cao (Nét)",
                "ext": "MP4",
                "type": "direct",
                "url": hd_url
            })

            # 2. Dòng SD (360P/480P)
            formats_list.append({
                "quality": "360P (SD)",
                "desc": "Chất lượng thường",
                "ext": "MP4",
                "type": "direct",
                "url": sd_url
            })

            # 3. Định dạng âm thanh (MP3)
            formats_list.append({
                "quality": "MP3",
                "desc": "Âm thanh video",
                "ext": "MP3",
                "type": "render",
                "url": hd_url
            })

            # 4. Ảnh đại diện Thumbnail (JPG)
            if thumbnail:
                formats_list.append({
                    "quality": "IMAGE",
                    "desc": "Hình ảnh thumbnail",
                    "ext": "JPG",
                    "type": "direct",
                    "url": thumbnail
                })

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
