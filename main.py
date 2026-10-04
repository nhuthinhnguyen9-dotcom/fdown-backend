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
    """Làm sạch URL Facebook từ App mà không làm hỏng link Story/Reels."""
    if not url:
        return url

    # Nếu là link chia sẻ rút gọn fb.watch hoặc facebook.com/share/
    # hãy giữ nguyên để yt-dlp tự follow
    parsed = urllib.parse.urlparse(url)

    # Nếu là Story, giữ nguyên đường dẫn
    if "/stories/" in parsed.path:
        return url.split("&")[0]  # Chỉ xóa tham số theo dõi ứng dụng ở cuối

    # Nếu là video/reels thông thường, xóa các tham số rác như mibextid, fbclid
    clean_path = parsed.path
    clean_url = f"{parsed.scheme}://www.facebook.com{clean_path}"

    return clean_url


@app.get("/api/download")
def download_video(url: str):
    if not url:
        raise HTTPException(
            status_code=400, detail="Vui lòng cung cấp URL video!"
        )

    # Xử lý làm sạch link
    target_url = clean_fb_url(url.strip())

    # Cấu hình yt-dlp tối ưu cho Facebook & Story
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

            # Trường hợp link là playlist/nhiều story, lấy item đầu tiên
            if "entries" in info and len(info["entries"]) > 0:
                info = info["entries"][0]

            formats_list = []

            # Nếu lấy được URL video trực tiếp
            video_url = info.get("url")
            if video_url:
                formats_list.append(
                    {
                        "quality": "HD / SD Video",
                        "desc": "Tệp Video MP4 gốc",
                        "ext": "mp4",
                        "url": video_url,
                    }
                )

            # Lấy các định dạng chất lượng khác nếu có
            if info.get("formats"):
                for fmt in info["formats"]:
                    if fmt.get("url") and fmt.get("vcodec") != "none":
                        quality_label = fmt.get(
                            "format_note"
                        ) or f"{fmt.get('height', 'SD')}p"
                        # Tránh trùng lặp URL
                        if not any(
                            f["url"] == fmt["url"] for f in formats_list
                        ):
                            formats_list.append(
                                {
                                    "quality": f"{quality_label}".upper(),
                                    "desc": f"Video MP4 ({quality_label})",
                                    "ext": "mp4",
                                    "url": fmt["url"],
                                }
                            )

            if not formats_list:
                raise Exception("Không tìm thấy tệp video trực tiếp.")

            return {
                "title": info.get("title") or "Facebook Video / Story",
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration_string") or "N/A",
                "formats": formats_list,
            }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Không thể bóc tách video. Lỗi: {str(e)}",
        )
