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


def get_resolution_label(height: int, format_id: str = "") -> str:
    """Xác định nhãn chất lượng dựa trên chiều cao khung hình (height)."""
    if height >= 2160:
        return "4K Video"
    elif height >= 1440:
        return "2K Video"
    elif height >= 1080:
        return "1080p Full HD"
    elif height >= 720:
        return "720p HD"
    elif height >= 480:
        return "480p SD"
    elif height >= 360:
        return "360p SD"
    else:
        if "hd" in format_id.lower():
            return "HD Video"
        return "SD Video"


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

            # 1. Duyệt qua các định dạng video khả thi từ Facebook
            if info.get("formats"):
                # Sắp xếp các format theo độ phân giải từ cao xuống thấp
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
                    format_id = str(fmt.get("format_id", ""))

                    # Chỉ lấy các bản ghi có chứa cả Video + Audio hoặc các định dạng chuẩn
                    quality_label = get_resolution_label(height, format_id)

                    # Lọc trùng chất lượng để danh sách không bị rác
                    if quality_label not in seen_qualities:
                        seen_qualities.add(quality_label)
                        formats_list.append(
                            {
                                "quality": quality_label,
                                "desc": f"Tệp Video MP4 ({quality_label})",
                                "ext": "mp4",
                                "url": fmt_url,
                            }
                        )

            # 2. Nếu không tìm thấy format trong danh sách, dùng link gốc mặc định
            default_url = info.get("url")
            if not formats_list and default_url:
                formats_list.append(
                    {
                        "quality": "HD / SD Video",
                        "desc": "Tệp Video MP4 gốc",
                        "ext": "mp4",
                        "url": default_url,
                    }
                )

            # 3. Tùy chọn MP3 (Lấy đường dẫn âm thanh)
            audio_url = (
                formats_list[0]["url"]
                if formats_list
                else (default_url or target_url)
            )
            if audio_url:
                formats_list.append(
                    {
                        "quality": "MP3",
                        "desc": "Tệp Âm thanh MP3",
                        "ext": "mp3",
                        "url": audio_url,
                    }
                )

            # 4. Tùy chọn Ảnh bìa (Thumbnail)
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
