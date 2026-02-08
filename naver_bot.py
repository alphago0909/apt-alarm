import requests
import json
import os
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ★★★ 디버깅용 설정 ★★★
TELEGRAM_TOKEN = os.environ.get('NAVER_TOKEN')
CHAT_ID = os.environ.get('TG_ID')

def print_log(msg):
    print(f"👉 [로그] {msg}")

if __name__ == "__main__":
    print_log("봇 진단 시작...")
    
    # 1. 토큰 확인
    if not TELEGRAM_TOKEN:
        print_log("❌ [치명적 오류] 'NAVER_TOKEN'이 비어있습니다! Secrets 설정을 확인하세요.")
        exit()
    else:
        print_log(f"✅ 토큰 확인됨 (앞 5자리: {TELEGRAM_TOKEN[:5]}...)")

    if not CHAT_ID:
        print_log("❌ [치명적 오류] 'TG_ID'가 비어있습니다!")
        exit()
    else:
        print_log(f"✅ 내 아이디 확인됨: {CHAT_ID}")

    # 2. 텔레그램 연결 테스트 (강제 메시지 전송)
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": "🔔 [테스트] 봇 연결 성공! 이제 명령어를 입력하세요."}
    
    try:
        print_log("텔레그램으로 테스트 메시지 발사 시도...")
        res = requests.get(url, params=params)
        
        if res.status_code == 200:
            print_log("🎉 [성공] 메시지가 전송되었습니다! 텔레그램을 확인하세요.")
        elif res.status_code == 401:
            print_log("⛔ [오류] 토큰이 틀렸습니다! (Unauthorized)")
            print_log("-> 해결책: 텔레그램 @BotFather 에서 토큰을 다시 확인하고 GitHub Secrets의 'NAVER_TOKEN'을 수정하세요.")
        else:
            print_log(f"⚠️ [오류] 전송 실패. 응답 코드: {res.status_code}")
            print_log(f"내용: {res.text}")
            
    except Exception as e:
        print_log(f"❌ [에러] 연결 중 에러 발생: {e}")
