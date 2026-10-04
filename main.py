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

    # Chuẩn hóa link Facebook
    clean_url = url.strip()

    # ENGINE 1: Bóc tách qua Gateway API của SnapSave Proxy
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Accept': '*/*',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://snapsave.app',
            'Referer': 'https://snapsave.app/'
        }
        payload = f"url={urllib.parse.quote(clean_url)}"
        
        req = requests.post("https://snapsave.app/action.php?lang=en", data=payload, headers=headers, timeout=10)
        res_text = req.text

        # Tìm link MP4 dạng HD/SD trong đoạn Javascript mã hóa của SnapSave
        urls = re.findall(r'https?://[^\s"<>\']+\.mp4[^\s"<>\']*', res_text)
        if not urls:
            urls = re.findall(r'href=\\"(https?://[^\\]+)\\"', res_text)

        if urls:
            video_url = urls[0].replace('\\/', '/').replace('&amp;', '&')
            return {
                "status": "success",
                "title": "Facebook Video HD",
                "url": video_url
            }
    except Exception:
        pass

    # ENGINE 2: Chuyển đổi sang mbasic (Facebook Mobile) để bypass firewall Render
    try:
        # Đổi link sang mbasic
        mbasic_url = clean_url.replace("www.facebook.com", "mbasic.facebook.com").replace("web.facebook.com", "mbasic.facebook.com").replace("facebook.com", "mbasic.facebook.com")
        
        mobile_headers = {
            'User-Agent': 'NokiaN9-00/00_2011M34_PR_r1053 AppleWebkit/534.3 (KHTML, like Gecko) NokiaBrowser/8.5.0 Mobile Safari/534.3'
        }
        
        res = requests.get(mbasic_url, headers=mobile_headers, timeout=10, allow_redirects=True)
        html = res.text

        # Bóc tách đường dẫn mp4 trực tiếp
        video_match = re.search(r'href="(/video_redirect/[^"]+)"', html) or re.search(r'src="(https://[^\"]+\.mp4[^\"]*)"', html)
        if video_match:
            v_link = video_match.group(1)
            if v_link.startswith("/video_redirect/"):
                # Decode link redirect từ FB
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(v_link).query)
                if "src" in parsed:
                    v_link = parsed["src"][0]
                else:
                    v_link = "https://mbasic.facebook.com" + v_link

            return {
                "status": "success",
                "title": "Facebook Video Mobile",
                "url": v_link
            }
    except Exception:
        pass

    # ENGINE 3: Dự phòng qua GetFB Gateway
    try:
        getfb_res = requests.post(
            "https://getmyfb.com/process",
            data={"id": clean_url, "locale": "en"},
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'},
            timeout=10
        )
        matches = re.findall(r'href="(https://[^\"]+\.mp4[^\"]*)"', getfb_res.text)
        if matches:
            return {
                "status": "success",
                "title": "Facebook Video",
                "url": matches[0].replace("&amp;", "&")
            }
    except Exception:
        pass

    raise HTTPException(
        status_code=400, 
        detail="Facebook đã thắt chặt quyền riêng tư đối với video này. Hãy đảm bảo video ở chế độ CÔNG KHAI và không nằm trong Nhóm Kín!"
    )
