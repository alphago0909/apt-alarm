import requests
import os
import sys

# 깃허브에 저장된 키 가져오기
TOKEN = os.environ.get('NAVER_TOKEN')
CHAT_ID = os.environ.get('TG_ID')

print("--- [진단 시작] ---")

# 1. 키가 제대로 있나 확인
if not TOKEN:
    print("❌ 에러: NAVER_TOKEN이 없습니다! Secrets 설정을 확인하세요.")
    sys.exit(1)
else:
    # 보안상 앞 5글자만 출력
    print(f"✅ 토큰 확인됨: {TOKEN[:5]}...")

if not CHAT_ID:
    print("❌ 에러: TG_ID가 없습니다!")
    sys.exit(1)
else:
    print(f"✅ 아이디 확인됨: {CHAT_ID}")

# 2. 텔레그램에 강제로 메시지 보내기
print("📡 텔레그램 발송 시도 중...")
url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
params = {"chat_id": CHAT_ID, "text": "🚨 [생존신고] 주인님! 저 연결됐어요! 토큰 맞아요!"}

try:
    res = requests.get(url, params=params)
    print(f"결과 코드: {res.status_code}")
    print(f"결과 내용: {res.text}")
    
    if res.status_code == 200:
        print("🎉 성공! 텔레그램을 확인하세요.")
    elif res.status_code == 401:
        print("⛔ 실패! 토큰(비밀번호)이 틀렸습니다. 봇파더에게 다시 받으세요.")
    else:
        print("⚠️ 실패! 채팅방이 없거나 아이디가 틀렸습니다.")

except Exception as e:
    print(f"❌ 치명적 오류: {e}")

print("--- [진단 종료] ---")
