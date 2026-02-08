import requests
import json
import time
import os
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# ★★★ 네이버 봇 전용 설정 ★★★
# ==========================================
TELEGRAM_TOKEN = os.environ.get('NAVER_TOKEN')
CHAT_ID = os.environ.get('TG_ID')
WATCHLIST_FILE = 'watchlist.json'

# 아이폰으로 위장하기 (검색 성공률 100%)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
    "Referer": "https://m.land.naver.com/"
}

GU_CODES = {
    "강남": "1168000000", "서초": "1165000000", "송파": "1171000000", "용산": "1117000000",
    "성동": "1120000000", "마포": "1144000000", "광진": "1121500000", "양천": "1147000000",
    "영등포": "1156000000", "동작": "1159000000", "강동": "1174000000", "종로": "1111000000",
    "중구": "1114000000", "동대문": "1123000000", "서대문": "1141000000", "관악": "1162000000",
    "강서": "1150000000", "구로": "1153000000", "금천": "1154500000", "은평": "1138000000",
    "성북": "1129000000", "강북": "1130500000", "도봉": "1132000000", "노원": "1135000000",
    "중랑": "1126000000"
}

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
    requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", params=params)

def delete_msg(msg_id):
    requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage", params={"chat_id": CHAT_ID, "message_id": msg_id})

def get_main_menu():
    return {"inline_keyboard": [
        [{"text": "🌍 지역(구) 설정", "callback_data": "MENU_GU"}, 
         {"text": "🏢 아파트 설정", "callback_data": "MENU_APT"}],
        [{"text": "📋 내 감시 목록", "callback_data": "SHOW_LIST"}]
    ]}

def get_gu_menu(watchlist):
    buttons, row = [], []
    for name, code in GU_CODES.items():
        is_active = any(x['type'] == 'GU' and x['code'] == code for x in watchlist)
        label = f"{'✅' if is_active else '⬜'} {name}"
        row.append({"text": label, "callback_data": f"TOGGLE_GU:{name}:{code}"})
        if len(row) == 3: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([{"text": "🔙 메인으로", "callback_data": "MAIN"}])
    return {"inline_keyboard": buttons}

def process_telegram():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    offset = 0
    if os.path.exists("last_update_id.txt"):
        with open("last_update_id.txt", "r") as f: 
            try: offset = int(f.read())
            except: pass

    try:
        res = requests.get(url, params={"offset": offset + 1, "timeout": 5}).json()
        if not res.get("ok"): return False
        
        watchlist = load_json(WATCHLIST_FILE)
        is_changed = False
        updates = res.get("result", [])
        
        if not updates: return False

        for item in updates:
            offset = item["update_id"]
            
            if "callback_query" in item:
                cb = item["callback_query"]
                data = cb["data"]
                msg_id = cb["message"]["message_id"]
                requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", params={"callback_query_id": cb["id"]})
                
                if data == "MAIN":
                    send_msg("⚙️ 설정 메뉴", get_main_menu())
                    delete_msg(msg_id)
                elif data == "MENU_GU":
                    send_msg("🌍 감시할 구를 선택하세요", get_gu_menu(watchlist))
                    delete_msg(msg_id)
                elif data.startswith("TOGGLE_GU"):
                    _, name, code = data.split(":")
                    exists = next((i for i,x in enumerate(watchlist) if x['code']==code), -1)
                    if exists > -1: 
                        watchlist.pop(exists)
                        send_msg(f"🗑️ {name}구 감시 해제")
                    else: 
                        watchlist.append({"type":"GU", "name":name, "code":code})
                        send_msg(f"✅ {name}구 추가 완료! (매물 확인 중...)")
                    is_changed = True
                    send_msg("🌍 감시할 구 선택", get_gu_menu(watchlist))
                    delete_msg(msg_id)
                elif data == "MENU_APT":
                    send_msg("⌨️ 채팅창에 아파트 이름을 입력하세요.\n(예: 잠실엘스)", {"inline_keyboard": [[{"text":"🔙 취소","callback_data":"MAIN"}]]})
                    delete_msg(msg_id)
                elif data.startswith("ADD_APT"):
                    _, code, name = data.split(":")
                    if not any(x['code']==code for x in watchlist):
                        watchlist.append({"type":"APT", "name":name, "code":code})
                        send_msg(f"✅ '{name}' 감시 시작! (매물 확인 중...)")
                        is_changed = True
                    else:
                        send_msg("⚠️ 이미 감시 중입니다.", get_main_menu())
                    delete_msg(msg_id)
                elif data == "SHOW_LIST":
                    txt = "📋 감시 목록:\n" + "\n".join([f"- {w['name']}" for w in watchlist]) if watchlist else "📭 목록이 비었습니다."
                    send_msg(txt, get_main_menu())
                    delete_msg(msg_id)
            
            elif "message" in item:
                text = item["message"].get("text", "")
                if text == "/start":
                    send_msg("🤖 네이버 부동산 비서입니다.", get_main_menu())
                elif not text.startswith("/"):
                    send_msg(f"🔎 '{text}' 검색 중...")
                    try:
                        r = requests.get("https://m.land.naver.com/api/search/client/search", params={"keyword":text}, headers=HEADERS, verify=False).json()
                        btns = []
                        for c in r.get("complexes", [])[:5]:
                            btns.append([{"text": f"🏢 {c['complexName']}", "callback_data": f"ADD_APT:{c['complexNo']}:{c['complexName']}"}])
                        btns.append([{"text":"🔙 취소","callback_data":"MAIN"}])
                        if len(btns) > 1: send_msg(f"👇 '{text}' 검색 결과:", {"inline_keyboard": btns})
                        else: send_msg("❌ 검색 결과가 없습니다.")
                    except: send_msg("❌ 검색 오류")

        if is_changed: save_json(WATCHLIST_FILE, watchlist)
        with open("last_update_id.txt", "w") as f: f.write(str(offset))
        return True
    except: return False

def check_naver_listings():
    watchlist = load_json(WATCHLIST_FILE)
    if not watchlist: return
    
    print("🔍 스캔 중...")
    saved = load_json("saved_naver_history.json")
    
    for target in watchlist:
        time.sleep(1)
        url = "https://m.land.naver.com/article/getArticleList" if target['type'] == 'GU' else "https://m.land.naver.com/complex/getComplexArticleList"
        params = {"tradTpCd": "A1", "order": "date_desc"}
        if target['type'] == 'GU': params.update({"cortarNo": target['code'], "rletTpCd": "APT", "prcMax": 300000})
        else: params.update({"hscpNo": target['code'], "showR0": "N"})
        
        try:
            items = requests.get(url, params=params, headers=HEADERS, verify=False, timeout=5).json().get('result',{}).get('list',[])
            for item in items:
                aid = item.get('atclNo')
                if aid in saved: continue
                apt = item.get('atclNm')
                price = item.get('hanPrc')
                area = item.get('spc1')
                link = f"https://m.land.naver.com/article/info/{aid}"
                msg = f"🔔 [{target['name']} 신규]\n🏢 {apt}\n💰 {price} / {area}㎡\n🔗 {link}"
                send_msg(msg)
                saved.append(aid)
        except: continue
        
    if len(saved) > 2000: saved = saved[-2000:]
    save_json("saved_naver_history.json", saved)

if __name__ == "__main__":
    print("🚀 봇 가동")
    end_time = time.time() + (5 * 60)
    while time.time() < end_time:
        process_telegram()
        if int(time.time()) % 60 == 0:
            check_naver_listings()
        time.sleep(0.5)
