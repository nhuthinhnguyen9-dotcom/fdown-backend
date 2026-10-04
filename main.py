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

    # Cấu hình an toàn để ép yt-dlp lấy các định dạng chắc chắn có cả audio lẫn video
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / best",
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
            info = yt_dlp.YoutubeDL(
                {"quiet": True, "no_warnings": True}
            ).extract_info(target_url, download=False)

            if "entries" in info and len(info["entries"]) > 0:
                info = info["entries"][0]

            formats_list = []
            default_url = info.get("url")
            thumbnail_url = info.get("thumbnail")

            # Duyệt qua các định dạng, ưu tiên các định dạng có sẵn audio hoặc link trực tiếp chuẩn
            found_formats = False
            if info.get("formats"):
                for fmt in info["formats"]:
                    fmt_url = fmt.get("url")
                    vcodec = fmt.get("vcodec", "none")
                    acodec = fmt.get("acodec", "none")

                    if not fmt_url:
                        continue

                    # Chỉ lấy những định dạng có cả hình VÀ tiếng (tránh hoàn toàn việc bị mất tiếng)
                    if vcodec != "none" and acodec != "none":
                        height = fmt.get("height") or 0
                        if height >= 720:
                            label = "HD Video (Có tiếng)"
                        else:
                            label = "SD Video (Có tiếng)"

                        # Tránh trùng lặp
                        if not any(f["quality"] == label for f in formats_list):
                            formats_list.append(
                                {
                                    "quality": label,
                                    "desc": (
                                        "Tệp Video MP4 chất lượng chuẩn"
                                    ),
                                    "ext": "mp4",
                                    "url": fmt_url,
                                }
                            )
                            found_formats = True

            # Nếu không tìm thấy dạng gộp sẵn, dùng link mặc định an toàn của yt-dlp
            if not formats_list:
                # Lấy bản best tổng hợp
                formats_list.append(
                    {
                        "quality": "HD Video (Chính)",
                        "desc": "Tệp Video MP4 tiêu chuẩn",
                        "ext": "mp4",
                        "url": default_url or target_url,
                    }
                )

            # Thêm tùy chọn MP3
            audio_target = formats_list[0]["url"] if formats_list else default_url
            if audio_target:
                formats_list.append(
                    {
                        "quality": "MP3",
                        "desc": "Tệp Âm thanh MP3",
                        "ext": "mp3",
                        "url": audio_target,
                    }
                )

            # Thêm tùy chọn Ảnh bìa
            if thumbnail_url:
                formats_list.append(
                    {
                        "quality": "IMAGE",
                        "desc": "Ảnh bìa video",
                        "ext": "jpg",
                        "url": thumbnail_url,
                    }
                )

            return {
                "title": info.get("title") or "Facebook Video",
                "thumbnail": thumbnail_url,
                "duration": info.get("duration_string") or "N/A",
                "formats": formats_list,
            }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail="Không thể bóc tách video này. Vui lòng kiểm tra lại đường link!",
        )
