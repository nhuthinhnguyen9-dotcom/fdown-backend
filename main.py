from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import re
import urllib.parse

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

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Sec-Fetch-Mode': 'navigate',
    }

    # CÁCH 1: Bóc tách trực tiếp từ Facebook CDN qua regex (Nhanh & Ổn định nhất)
    try:
        clean_url = url.split('?')[0] if '?' in url else url
        res = requests.get(clean_url, headers=headers, timeout=10, allow_redirects=True)
        html = res.text

        # Tìm link HD hoặc SD trực tiếp trong HTML gốc của Facebook
        hd_match = re.search(r'browser_native_hd_url":"([^"]+)"', html) or re.search(r'hd_src:"([^"]+)"', html)
        sd_match = re.search(r'browser_native_sd_url":"([^"]+)"', html) or re.search(r'sd_src:"([^"]+)"', html)

        found_url = None
        if hd_match:
            found_url = hd_match.group(1)
        elif sd_match:
            found_url = sd_match.group(1)

        if found_url:
            # Giải mã các ký tự unicode escape (ví dụ \/ thành /)
            video_url = found_url.replace('\\/', '/').replace('\\u0026', '&')
            return {
                "status": "success",
                "title": "Facebook Video (Gốc)",
                "url": video_url
            }
    except Exception:
        pass

    # CÁCH 2: Dự phòng qua Server SaveFrom API
    try:
        sf_res = requests.post(
            "https://worker.sf-helper.com/project/sf-helper/api.php",
            data={"url": url},
            headers=headers,
            timeout=10
        )
        sf_data = sf_res.json()
        if isinstance(sf_data, list) and len(sf_data) > 0:
            url_list = sf_data[0].get("url", [])
            if len(url_list) > 0 and "url" in url_list[0]:
                return {
                    "status": "success",
                    "title": sf_data[0].get("meta", {}).get("title", "Facebook Video"),
                    "url": url_list[0]["url"]
                }
    except Exception:
        pass

    # CÁCH 3: Dự phòng qua SSYouTube/SaveFrom Get Link
    try:
        encode_url = urllib.parse.quote(url)
        api_res = requests.get(f"https://api.v2.snapsave.app/api/download?url={encode_url}", headers=headers, timeout=10)
        if api_res.status_code == 200:
            data = api_res.json()
            if "data" in data and len(data["data"]) > 0:
                v_url = data["data"][0].get("url") or data["data"][0].get("file")
                if v_url:
                    return {
                        "status": "success",
                        "title": "Facebook Video HD",
                        "url": v_url
                    }
    except Exception:
        pass

    raise HTTPException(
        status_code=400, 
        detail="Không thể bóc tách video này! Vui lòng thử dùng link trực tiếp (Ví dụ: https://www.facebook.com/watch/?v=... hoặc link Reels công khai)."
    )
