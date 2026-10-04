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
    """Làm sạch các tham số rác đính kèm từ App Facebook."""
    if not url:
        return url

    url = url.strip()
    parsed = urllib.parse.urlparse(url)

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
            seen_qualities = set()
            default_url = info.get("url")
            audio_url = None

            # 1. Quét các định dạng video (có hỗ trợ 1080p, 2K, 4K nếu có)
            if info.get("formats"):
                sorted_formats = sorted(
                    info["formats"],
                    key=lambda x: x.get("height") or 0,
                    reverse=True,
                )

                for fmt in sorted_formats:
                    fmt_url = fmt.get("url")
                    if not fmt_url:
                        continue

                    height = fmt.get("height") or 0
                    format_id = str(fmt.get("format_id", "")).lower()
                    vcodec = fmt.get("vcodec", "none")
                    acodec = fmt.get("acodec", "none")

                    # Tìm riêng một link chuyên dụng cho audio (có tiếng gốc sạch sẽ)
                    if vcodec == "none" and acodec != "none" and not audio_url:
                        audio_url = fmt_url

                    # Lọc các luồng video
                    if vcodec == "none":
                        continue

                    label = None
                    if height >= 2160 or "4k" in format_id:
                        label = "4K Video"
                    elif height >= 1440 or "2k" in format_id:
                        label = "2K Video"
                    elif height >= 1080 or "1080" in format_id:
                        label = "1080p Full HD"
                    elif height >= 720 or "hd" in format_id:
                        label = "HD Video"
                    elif height > 0 or "sd" in format_id:
                        label = "SD Video"

                    if label and label not in seen_qualities:
                        seen_qualities.add(label)
                        formats_list.append(
                            {
                                "quality": label,
                                "desc": f"Tệp Video MP4 ({label})",
                                "ext": "mp4",
                                "url": fmt_url,
                            }
                        )

            # Nếu không quét được danh sách, dùng link mặc định
            if not formats_list and default_url:
                formats_list.append(
                    {
                        "quality": "HD / SD Video",
                        "desc": "Tệp Video MP4 gốc",
                        "ext": "mp4",
                        "url": default_url,
                    }
                )

            # Nếu không tìm thấy luồng audio riêng biệt, fallback tạm về link video đầu tiên để lấy tiếng
            if not audio_url:
                audio_url = formats_list[0]["url"] if formats_list else default_url

            # 2. Thêm tùy chọn MP3 (Audio thực sự lấy từ luồng âm thanh sạch)
            if audio_url:
                formats_list.append(
                    {
                        "quality": "MP3",
                        "desc": "Tệp Âm thanh chuẩn",
                        "ext": "m4a",  # Dùng m4a/aac gốc của Facebook để trình duyệt nhận diện chính xác là file audio
                        "url": audio_url,
                    }
                )

            # 3. Thêm tùy chọn Ảnh bìa / Thumbnail
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
                "title": info.get("title") or "Facebook Video",
                "thumbnail": thumbnail_url,
                "duration": info.get("duration_string") or "N/A",
                "formats": formats_list,
            }

    except Exception as e:
        err_msg = str(e)
        if "login.php" in err_msg or "stories" in target_url:
            raise HTTPException(
                status_code=400,
                detail="Facebook Story hoặc Video riêng tư yêu cầu đăng nhập. Hệ thống hiện chỉ hỗ trợ Video Công Khai (Public) và Reels!",
            )

        raise HTTPException(
            status_code=400,
            detail="Không thể bóc tách video này. Vui lòng kiểm tra lại đường link!",
        )
