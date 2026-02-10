import requests
import xml.etree.ElementTree as ET
import datetime
import os
import json

# ==========================================
# 환경변수 (Github Secrets에서 가져옴)
# ==========================================
SERVICE_KEY = os.environ.get('DATA_KEY')
TELEGRAM_TOKEN = os.environ.get('TG_TOKEN')
CHAT_ID = os.environ.get('TG_ID')

# 감시할 지역 코드 (예: 광진구 11215)
LAWD_CD = '11215' 
DEAL_YMD = datetime.datetime.now().strftime('%Y%m')

# ★ 여기가 핵심: 보낸 내역 저장하는 파일 이름
HISTORY_FILE = 'sent_list.json'

def load_history():
    if not os.path.exists(HISTORY_FILE): return []
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except: return []

def save_history(data):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_telegram(msg):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    try:
        requests.get(url, params={'chat_id': CHAT_ID, 'text': msg})
    except: pass

def get_apt_trade():
    url = 'http://openapi.molit.go.kr/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcAptTradeDev'
    params = {
        'serviceKey': requests.utils.unquote(SERVICE_KEY),
        'LAWD_CD': LAWD_CD,
        'DEAL_YMD': DEAL_YMD,
        'numOfRows': '100'
    }
    
    try:
        res = requests.get(url, params=params)
        root = ET.fromstring(res.content)
        items = root.findall('.//item')
        
        # 1. 기존 장부(이미 보낸 것들) 펼치기
        sent_list = load_history()
        new_sent_list = sent_list.copy()
        
        count = 0
        
        for item in items:
            try:
                apt_name = item.find('아파트').text
                price = item.find('거래금액').text.strip()
                day = item.find('일').text
                floor = item.find('층').text
                area = item.find('전용면적').text
                
                # ★ 거래마다 '고유 번호표'를 붙입니다. (아파트이름+가격+층+날짜)
                # 이게 같으면 100% 중복 거래입니다.
                unique_id = f"{apt_name}_{price}_{floor}_{day}"
                
                # 2. 장부에 있는 번호표면? -> 패스! (중복 방지)
                if unique_id in sent_list:
                    continue 
                
                # 3. 장부에 없으면? -> 알림 보내기!
                msg = f"🏠 **[실거래 알림]**\n"
                msg += f"단지: {apt_name}\n"
                msg += f"가격: {price}만원\n"
                msg += f"층수: {floor}층\n"
                msg += f"면적: {area}㎡"
                
                send_telegram(msg)
                print(f"전송 완료: {unique_id}")
                
                # 4. 방금 보낸 건 장부에 기록
                new_sent_list.append(unique_id)
                count += 1
                
            except: continue
        
        # 5. 장부 덮어쓰기 (최근 500개만 기억)
        if len(new_sent_list) > 500:
            new_sent_list = new_sent_list[-500:]
        save_history(new_sent_list)
        print(f"총 {count}개의 신규 거래 발견")
        
    except Exception as e:
        print(f"에러: {e}")

if __name__ == '__main__':
    get_apt_trade()
