import logging
import urllib.parse

import yt_dlp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fbdl")

app = FastAPI()

# Nên thay "*" bằng domain web của bạn khi đưa lên chạy thật.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # "*" + credentials=True là cấu hình không an toàn
    allow_methods=["GET"],
    allow_headers=["*"],
)

FB_HOSTS = {
    "facebook.com",
    "www.facebook.com",
    "m.facebook.com",
    "web.facebook.com",
    "mbasic.facebook.com",
}
SHORT_HOSTS = {"fb.watch"}
# Chỉ giữ lại các tham số thật sự định danh video (vd: /watch/?v=123).
KEEP_QUERY = {"v", "story_fbid", "id", "set"}


def clean_fb_url(url: str):
    """Làm sạch link Facebook. Trả về None nếu không phải link Facebook."""
    url = (url or "").strip()
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()

    if parsed.scheme not in ("http", "https"):
        return None

    # Link rút gọn fb.watch phải giữ nguyên, nếu đổi sang facebook.com sẽ hỏng.
    if host in SHORT_HOSTS:
        return url

    if host not in FB_HOSTS:
        return None

    # Story: giữ nguyên toàn bộ.
    if "/stories/" in parsed.path:
        return url

    kept = [(k, v) for k, v in urllib.parse.parse_qsl(parsed.query) if k in KEEP_QUERY]
    return urllib.parse.urlunparse(
        ("https", "www.facebook.com", parsed.path, "", urllib.parse.urlencode(kept), "")
    )


def is_progressive(fmt: dict) -> bool:
    """Định dạng có cả hình và tiếng trong cùng một file."""
    return fmt.get("vcodec") not in (None, "none") and fmt.get("acodec") not in (None, "none")


@app.get("/api/download")
def download_video(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp URL video!")

    target_url = clean_fb_url(url)
    if not target_url:
        raise HTTPException(status_code=400, detail="Đây không phải link Facebook hợp lệ.")

    # Không đặt "format": "best". Facebook thường tách riêng luồng hình và tiếng,
    # nên "best" (chỉ nhận file đã có cả hai) có thể báo "format not available".
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
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

            formats = [f for f in (info.get("formats") or []) if f.get("url")]
            progressive = [f for f in formats if is_progressive(f)]
            video_only = [
                f for f in formats
                if f.get("vcodec") not in (None, "none") and f.get("acodec") in (None, "none")
            ]
            audio_only = [
                f for f in formats
                if f.get("vcodec") in (None, "none") and f.get("acodec") not in (None, "none")
            ]

            def best_by_height(items):
                return max(items, key=lambda f: (f.get("height") or 0, f.get("tbr") or 0), default=None)

            out = []

            hd = next((f for f in progressive if str(f.get("format_id")).lower() == "hd"), None)
            sd = next((f for f in progressive if str(f.get("format_id")).lower() == "sd"), None)

            if hd:
                out.append({"quality": "HD Video", "desc": "Video HD (có tiếng)", "ext": "mp4", "url": hd["url"]})
            if sd:
                out.append({"quality": "SD Video", "desc": "Video SD (có tiếng)", "ext": "mp4", "url": sd["url"]})

            if not out:
                best = best_by_height(progressive)
                if best:
                    out.append({"quality": "Video", "desc": "Video MP4 (có tiếng)", "ext": "mp4", "url": best["url"]})

            # Reel thường chỉ có luồng tách rời: hình và tiếng là hai link khác nhau.
            if not out:
                vbest = best_by_height(video_only)
                if vbest:
                    out.append({
                        "quality": "Video không tiếng",
                        "desc": "Chỉ có hình. Cần ghép với âm thanh bằng ffmpeg",
                        "ext": "mp4",
                        "url": vbest["url"],
                    })

            abest = best_by_height(audio_only)
            if abest:
                out.append({"quality": "AUDIO", "desc": "Âm thanh (định dạng m4a)", "ext": "m4a", "url": abest["url"]})

            thumbnail = info.get("thumbnail")
            if thumbnail:
                out.append({"quality": "IMAGE", "desc": "Ảnh bìa video", "ext": "jpg", "url": thumbnail})

            if not out:
                raise RuntimeError("Không tìm thấy tệp video trực tiếp.")

            return {
                "title": info.get("title") or "Facebook Video",
                "thumbnail": thumbnail,
                "duration": info.get("duration_string") or "N/A",
                "formats": out,
            }

    except HTTPException:
        raise
    except Exception as e:
        err = str(e)
        # Ghi lỗi thật vào log để biết nguyên nhân. Đừng nuốt mất lỗi.
        logger.exception("Lỗi khi xử lý %s: %s", target_url, err)
        low = err.lower()
        if "login" in low or "log in" in low or "private" in low:
            raise HTTPException(
                status_code=400,
                detail="Video riêng tư hoặc Facebook yêu cầu đăng nhập. Chỉ hỗ trợ nội dung công khai.",
            )
        raise HTTPException(
            status_code=400,
            detail="Không thể bóc tách nội dung này. Vui lòng kiểm tra lại đường link!",
        )
