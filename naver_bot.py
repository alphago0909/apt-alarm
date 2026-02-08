import requests
import json
import time
import os
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# ★★★ 네이버 봇 전용 설정 ★★★
# ==========================================
TELEGRAM_TOKEN = os.environ.get('NAVER_TOKEN') # 네이버 봇 토큰
CHAT_ID = os.environ.get('TG_ID')              # 내 아이디
WATCHLIST_FILE = 'watchlist.json'

# 구 코드 데이터 (버튼용)
GU_CODES = {
    "강남": "1168000000", "서초": "1165000000", "송파": "1171000000", "용산": "1117000000",
    "성동": "1120000000", "마포": "1144000000", "광진": "1121500000", "양천": "1147000000",
    "영등포": "1156000000", "동작": "1159000000", "강동": "1174000000", "종로": "1111000000",
    "중구": "1114000000", "동대문": "1123000000", "서대문": "1141000000", "관악": "1162000000",
    "강서": "1150000000", "구로": "1153000000", "금천": "1154500000", "은평": "1138000000",
    "성북": "1129000000", "강북": "1130500000", "도봉": "1132000000", "노원": "1135000000",
    "중랑": "1126000000"
}

# 1. 기본 도구들
def load_json(filename):
    if not os.path.exists(filename): return []
    with open(filename, 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except: return []

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_msg(text, reply_markup=None):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    params = {"chat_id": CHAT_ID, "text": text}
    if reply_markup: params["reply_markup"] = json.dumps(reply_markup)
    try: requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", params=params)
    except: pass

def delete_msg(msg_id):
    try: requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage", params={"chat_id": CHAT_ID, "message_id": msg_id})
    except: pass

# 2. 메뉴 버튼 만들기 (여기가 화면 만드는 곳)
def get_main_menu():
    return {"inline_keyboard": [
        [{"text": "🌍 지역(구) 설정", "callback_data": "MENU_GU"}, 
         {"text": "🏢 아파트 설정", "callback_data": "MENU_APT"}],
        [{"text": "📋 내 감시 목록 확인", "callback_data": "SHOW_LIST"}]
    ]}

def get_gu_menu(watchlist):
    buttons, row = [], []
    for name, code in GU_CODES.items():
        # 이미 감시 중이면 체크 표시(✅)
        is_active = any(x['type'] == 'GU' and x['code'] == code for x in watchlist)
        label = f"{'✅' if is_active else '⬜'} {name}"
        row.append({"text": label, "callback_data": f"TOGGLE_GU:{name}:{code}"})
        if len(row) == 3: # 3개씩 줄바꿈
            buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([{"text": "🔙 메인으로 돌아가기", "callback_data": "MAIN"}])
    return {"inline_keyboard": buttons}

# 3. 텔레그램 버튼 누른거 처리하기
def process_telegram():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    
    # 마지막으로 읽은 메시지 번호 가져오기
    offset = 0
    if os.path.exists("last_update_id.txt"):
        with open("last_update_id.txt", "r") as f: 
            try: offset = int(f.read())
            except: pass

    try:
        # 메시지 확인
        res = requests.get(url, params={"offset": offset + 1, "timeout": 5}).json()
        if not res.get("ok"): return False
        
        watchlist = load_json(WATCHLIST_FILE)
        is_changed = False
        updates = res.get("result", [])
        
        if not updates: return False

        for item in updates:
            offset = item["update_id"]
            
            # [상황 A] 버튼을 눌렀을 때
            if "callback_query" in item:
                cb = item["callback_query"]
                data = cb["data"]
                msg_id = cb["message"]["message_id"]
                # 로딩바 없애기
                requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", params={"callback_query_id": cb["id"]})
                
                if data == "MAIN":
                    send_msg("⚙️ 설정을 선택하세요.", get_main_menu())
                    delete_msg(msg_id) # 이전 메뉴 지우기 (깔끔하게)

                elif data == "MENU_GU":
                    send_msg("🌍 감시할 구를 선택하세요.\n(누를 때마다 추가/해제됩니다)", get_gu_menu(watchlist))
                    delete_msg(msg_id)

                elif data.startswith("TOGGLE_GU"):
                    _, name, code = data.split(":")
                    exists = next((i for i,x in enumerate(watchlist) if x['code']==code), -1)
                    
                    if exists > -1: 
                        watchlist.pop(exists) # 이미 있으면 삭제
                        txt = f"🗑️ {name}구 감시 해제"
                    else: 
                        watchlist.append({"type":"GU", "name":name, "code":code}) # 없으면 추가
                        txt = f"✅ {name}구 추가 완료"
                    
                    is_changed = True
                    send_msg(txt) # 알림 메시지 잠깐 보냄
                    send_msg("🌍 감시할 구를 선택하세요.", get_gu_menu(watchlist)) # 메뉴판 갱신
                    delete_msg(msg_id)

                elif data == "MENU_APT":
                    send_msg("⌨️ 채팅창에 **아파트 이름**을 입력해주세요.\n(예: 헬리오시티, 잠실엘스)", {"inline_keyboard": [[{"text":"🔙 취소","callback_data":"MAIN"}]]})
                    delete_msg(msg_id)

                elif data.startswith("ADD_APT"):
                    _, code, name = data.split(":")
                    if not any(x['code']==code for x in watchlist):
                        watchlist.append({"type":"APT", "name":name, "code":code})
                        send_msg(f"✅ '{name}' 감시 시작!", get_main_menu())
                        is_changed = True
                    else:
                        send_msg("⚠️ 이미 감시 중인 아파트입니다.", get_main_menu())
                    delete_msg(msg_id)

                elif data == "SHOW_LIST":
                    if not watchlist:
                        txt = "📭 현재 감시 중인 목록이 없습니다."
                    else:
                        txt = "📋 **[현재 감시 목록]**\n"
                        for w in watchlist:
                            icon = "🌍" if w['type'] == 'GU' else "🏢"
                            txt += f"{icon} {w['name']}\n"
                    send_msg(txt, get_main_menu())
                    delete_msg(msg_id)
            
            # [상황 B] 채팅(텍스트)을 쳤을 때
            elif "message" in item:
                text = item["message"].get("text", "")
                
                if text == "/start":
                    send_msg("👋 안녕하세요! 네이버 부동산 비서입니다.\n아래 버튼을 눌러 설정을 시작하세요.", get_main_menu())
                elif not text.startswith("/"):
                    # 아파트 검색 모드
                    send_msg(f"🔎 '{text}' 검색 중...")
                    try:
                        # 네이버에 검색해보기
                        r = requests.get("https://m.land.naver.com/api/search/client/search", params={"keyword":text}, headers={"User-Agent":"Mozilla/5.0"}, verify=False).json()
                        btns = []
                        # 검색 결과 최대 5개 보여주기
                        for c in r.get("complexes", [])[:5]:
                            btns.append([{"text": f"🏢 {c['complexName']}", "callback_data": f"ADD_APT:{c['complexNo']}:{c['complexName']}"}])
                        
                        btns.append([{"text":"🔙 취소","callback_data":"MAIN"}])
                        
                        if len(btns) > 1:
                            send_msg("👇 추가할 아파트를 선택하세요:", {"inline_keyboard": btns})
                        else:
                            send_msg("❌ 검색 결과가 없습니다. 정확한 이름을 입력해주세요.")
                    except: 
                        send_msg("❌ 검색 중 오류가 발생했습니다.")

        if is_changed: save_json(WATCHLIST_FILE, watchlist)
        with open("last_update_id.txt", "w") as f: f.write(str(offset))
        return True
    except: return False

# 4. 부동산 매물 털어오기
def check_naver_listings():
    watchlist = load_json(WATCHLIST_FILE)
    if not watchlist: return
    
    print("🔍 매물 스캔 중...")
    saved = load_json("saved_naver_history.json")
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for target in watchlist:
        time.sleep(1) # 차단 방지
        url = "https://m.land.naver.com/article/getArticleList" if target['type'] == 'GU' else "https://m.land.naver.com/complex/getComplexArticleList"
        params = {"tradTpCd": "A1", "order": "date_desc"}
        
        if target['type'] == 'GU': params.update({"cortarNo": target['code'], "rletTpCd": "APT", "prcMax": 300000}) # 구 전체는 30억 이하만
        else: params.update({"hscpNo": target['code'], "showR0": "N"})
        
        try:
            items = requests.get(url, params=params, headers=headers, verify=False, timeout=5).json().get('result',{}).get('list',[])
            count = 0
            for item in items:
                aid = item.get('atclNo')
                if aid in saved: continue
                
                apt = item.get('atclNm')
                price = item.get('hanPrc')
                area = item.get('spc1')
                link = f"https://m.land.naver.com/article/info/{aid}"
                
                msg = f"🔔 [네이버 매물 - {target['name']}]\n🏢 {apt}\n💰 {price} / {area}㎡\n🔗 {link}"
                send_msg(msg)
                saved.append(aid)
                count += 1
                if count >= 3: break # 폭탄 방지
        except: continue
        
    if len(saved) > 2000: saved = saved[-2000:]
    save_json("saved_naver_history.json", saved)

# 5. 메인 실행 (5분 동안 깨어있기)
if __name__ == "__main__":
    print("🚀 봇 가동! (5분간 대기)")
    end_time = time.time() + (5 * 60) # 5분 타이머
    
    while time.time() < end_time:
        # 1. 버튼 눌렀나 확인 (0.5초마다)
        process_telegram()
        
        # 2. 매물 확인 (1분마다)
        if int(time.time()) % 60 == 0:
            check_naver_listings()
            
        time.sleep(0.5)
