from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
import datetime
import os

app = FastAPI()

# 환경변수 (나중에 Vercel 설정창에서 입력할 값들입니다)
PORTONE_API_KEY = os.environ.get("PORTONE_API_KEY")
PORTONE_API_SECRET = os.environ.get("PORTONE_API_SECRET")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID")


def get_portone_token():
    url = "https://api.iamport.kr/users/getToken"
    payload = {"imp_key": PORTONE_API_KEY, "imp_secret": PORTONE_API_SECRET}
    res = requests.post(url, json=payload).json()
    return res['response']['access_token']


def is_adult(birth_str):
    birth_date = datetime.datetime.strptime(birth_str, "%Y-%m-%d")
    today = datetime.date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age >= 19


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": OWNER_CHAT_ID, "text": message})


class CertData(BaseModel):
    imp_uid: str


# api/index.py의 verify_user 함수를 아래처럼 'GET'도 가능하게 수정
@app.api_route("/api/verify", methods=["GET", "POST"]) # POST만 있던 걸 api_route로 변경
async def verify_user(request: Request):
    # 1. 모바일(GET) 또는 PC(POST) 데이터 가져오기
    if request.method == "GET":
        imp_uid = request.query_params.get("imp_uid")
    else:
        data = await request.json()
        imp_uid = data.get("imp_uid")

    if not imp_uid:
        return {"status": "fail", "message": "인증번호가 없습니다."}

    # (이후 로직은 기존과 동일)
    token = get_portone_token()
    cert_url = f"https://api.iamport.kr/certifications/{imp_uid}"
    headers = {"Authorization": token}
    cert_res = requests.get(cert_url, headers=headers).json()
    
    user_info = cert_res['response']
    name = user_info['name']
    birth = user_info['birthday']
    phone = user_info['phone']
    
    if is_adult(birth):
        msg = f"🔔 [성인인증 완료]\n👤 성함: {name}\n📅 생년월일: {birth}\n📱 연락처: {phone}"
        send_telegram(msg)
        # 사장님 휴대폰 화면에 보여줄 메시지 (HTML 형태로 리턴하면 더 예쁩니다)
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=f"<h1>인증 성공!</h1><p>{name}님, 입장이 가능합니다.</p>")
    else:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content="<h1>인증 실패</h1><p>미성년자는 출입이 불가능합니다.</p>")

# Vercel이 인식할 수 있도록 추가
@app.get("/api")
async def root():
    return {"message": "노래방 인증 서버가 정상 작동 중입니다."}

@app.get("/")
async def read_index():
    return FileResponse('index.html')
