import urllib.parse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import yt_dlp

app = FastAPI()

# Cấu hình CORS để giao diện Blogger gọi API không bị chặn
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 1. HÀM XỬ LÝ & RÚT GỌN URL (Chèn đoạn code này ở đây)
def clean_and_resolve_fb_url(url: str) -> str:
    try:
        # Cắt bỏ các tham số rác từ app mobile (mibextid, source, fbclid, ...)
        parsed = urllib.parse.urlparse(url)
        clean_url = urllib.parse.urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, "", "", "")
        )

        # Gửi request để tự động Follow Redirect (chuyển hướng link từ App về link chuẩn)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }

        response = requests.head(
            clean_url, allow_redirects=True, timeout=5, headers=headers
        )
        final_url = response.url

        # Làm sạch tham số một lần nữa sau khi đã redirect xong
        parsed_final = urllib.parse.urlparse(final_url)
        return urllib.parse.urlunparse(
            (
                parsed_final.scheme,
                parsed_final.netloc,
                parsed_final.path,
                "",
                "",
                "",
            )
        )
    except Exception:
        return url


# 2. ENDPOINT API TẢI VIDEO
@app.get("/api/download")
def download_video(url: str):
    if not url:
        raise HTTPException(
            status_code=400, detail="Vui lòng cung cấp URL video!"
        )

    # ---> TỰ ĐỘNG LÀM SẠCH VÀ LẤY LINK CHUẨN TỪ APP TẠI ĐÂY <---
    target_url = clean_and_resolve_fb_url(url)

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "best",
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)

            # Lấy thông tin video trả về cho Frontend Blogger
            formats_list = []

            # Thêm định dạng Video
            formats_list.append(
                {
                    "quality": "HD / SD Video",
                    "desc": "Tệp Video MP4 gốc",
                    "ext": "mp4",
                    "url": info.get("url"),
                }
            )

            return {
                "title": info.get("title", "Facebook Video"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration_string", "N/A"),
                "formats": formats_list,
            }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail="Không thể bóc tách video. Vui lòng kiểm tra lại xem video có ở chế độ Công khai (Public) hay không!",
        )
