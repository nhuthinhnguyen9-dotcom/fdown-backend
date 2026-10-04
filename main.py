import urllib.parse
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


def clean_fb_url(url: str) -> str:
    """Làm sạch các tham số rác đính kèm từ App Facebook và hỗ trợ chuẩn Story."""
    if not url:
        return url

    url = url.strip()
    parsed = urllib.parse.urlparse(url)

    # Đối với Story, giữ nguyên cấu trúc đường dẫn đầy đủ để Facebook không từ chối truy cập
    if "/stories/" in parsed.path:
        return url

    clean_url = f"{parsed.scheme}://www.facebook.com{parsed.path}"
    return clean_url


@app.get("/api/download")
def download_video(url: str):
    if not url:
        raise HTTPException(
            status_code=400, detail="Vui lòng cung cấp URL video!"
        )

    target_url = clean_fb_url(url)

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "best",
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)

            if "entries" in info and len(info["entries"]) > 0:
                info = info["entries"][0]

            formats_list = []
            hd_url = None
            sd_url = None
            audio_url = None

            # Bóc tách link HD, SD chuẩn và tìm riêng luồng audio sạch cho MP3
            if info.get("formats"):
                for fmt in info["formats"]:
                    format_id = str(fmt.get("format_id", "")).lower()
                    fmt_url = fmt.get("url")
                    vcodec = fmt.get("vcodec", "none")
                    acodec = fmt.get("acodec", "none")

                    if not fmt_url:
                        continue

                    # Tự động tìm luồng chỉ có tiếng (audio-only) để làm file MP3 chuẩn
                    if vcodec == "none" and acodec != "none" and not audio_url:
                        audio_url = fmt_url

                    if "hd" in format_id:
                        hd_url = fmt_url
                    elif "sd" in format_id:
                        sd_url = fmt_url

            # Lấy URL mặc định nếu không phân biệt được HD/SD
            default_url = info.get("url")

            # 1. Thêm chất lượng HD
            if hd_url:
                formats_list.append(
                    {
                        "quality": "HD Video",
                        "desc": "Tệp Video HD chất lượng cao",
                        "ext": "mp4",
                        "url": hd_url,
                    }
                )

            # 2. Thêm chất lượng SD
            if sd_url:
                formats_list.append(
                    {
                        "quality": "SD Video",
                        "desc": "Tệp Video SD chất lượng tiêu chuẩn",
                        "ext": "mp4",
                        "url": sd_url,
                    }
                )

            # Nếu không tìm thấy HD/SD riêng biệt, lấy link video chính
            if not formats_list and default_url:
                formats_list.append(
                    {
                        "quality": "HD / SD Video",
                        "desc": "Tệp Video MP4 gốc",
                        "ext": "mp4",
                        "url": default_url,
                    }
                )

            # Xác định nguồn phát cho MP3
            final_audio_url = audio_url or hd_url or sd_url or default_url

            # 3. Thêm tùy chọn MP3 (Audio thực sự dạng m4a)
            if final_audio_url:
                formats_list.append(
                    {
                        "quality": "MP3",
                        "desc": "Tệp Âm thanh MP3 chuẩn",
                        "ext": "m4a",
                        "url": final_audio_url,
                    }
                )

            # 4. Thêm tùy chọn Ảnh bìa / Thumbnail
            thumbnail_url = info.get("thumbnail")
            if thumbnail_url:
                formats_list.append(
                    {
                        "quality": "IMAGE",
                        "desc": "Ảnh bìa video (Hình ảnh)",
                        "ext": "jpg",
                        "url": thumbnail_url,
                    }
                )

            if not formats_list:
                raise Exception("Không tìm thấy tệp video trực tiếp.")

            return {
                "title": info.get("title") or "Facebook Story / Video",
                "thumbnail": thumbnail_url,
                "duration": info.get("duration_string") or "N/A",
                "formats": formats_list,
            }

    except Exception as e:
        err_msg = str(e)
        if "login.php" in err_msg:
            raise HTTPException(
                status_code=400,
                detail="Video riêng tư yêu cầu đăng nhập. Hệ thống chỉ hỗ trợ Video Công Khai (Public), Reels và Story!",
            )

        raise HTTPException(
            status_code=400,
            detail="Không thể bóc tách nội dung này. Vui lòng kiểm tra lại đường link!",
        )
