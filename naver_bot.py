import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import json
import time
import os
import urllib3
import urllib.parse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TELEGRAM_TOKEN = os.environ.get('NAVER_TOKEN')
CHAT_ID = os.environ.get('TG_ID')
WATCHLIST_FILE = 'watchlist.json'

# ★★★ 강력한 위장술 (PC 크롬 브라우저인 척하기) ★★★
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://m.land.naver.com/"
}

# ★★★ 접속기(Session) 생성: 실패하면 3번까지 다시 시도함 ★★★
session = requests.Session()
retry = Retry(connect=3, backoff_factor=1) # 1초 쉬고 재시도
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)
session.headers.update(HEADERS)

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
    try: session.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", params=params, timeout=5)
    except: pass

def delete_msg(msg_id):
    try: session.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage", params={"chat_id": CHAT_ID, "message_id": msg_id}, timeout=5)
    except: pass

# ★ 네이버 접속 함수 (강화됨)
def naver_request(url, params=None):
    try:
        res = session.get(url, params=params, verify=False, timeout=10)
        return res
    except Exception as e:
        print(f"접속 실패: {e}")
        return None

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

def search_complex(keyword):
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://m.land.naver.com/api/search/client/search?keyword={encoded_keyword}"
    
    res = naver_request(url)
    if not res: return None, "❌ 네이버가 응답하지 않습니다 (Timeout)."
    if res.status_code != 200: return None, f"❌ 접속 차단됨 (코드: {res.status_code})"
            
    data = res.json()
    complexes = data.get("complexes", [])
    if not complexes: return None, "❌ 검색 결과가 없습니다."
    return complexes, "OK"

def test_connection(target_type, code, name):
    send_msg(f"🕵️‍♂️ '{name}' 매물 확인 중...")
    url = "https://m.land.naver.com/article/getArticleList" if target_type == 'GU' else "https://m.land.naver.com/complex/getComplexArticleList"
    params = {"tradTpCd": "A1", "order": "date_desc"}
    if target_type == 'GU': params.update({"cortarNo": code, "rletTpCd": "APT"})
    else: params.update({"hscpNo": code, "showR0": "N"})

    res = naver_request(url, params)
    if res and res.status_code == 200:
        items = res.json().get('result', {}).get('list', [])
        if items:
            item = items[0]
            msg = f"✅ **[연결 성공]** {name}\n최신: {item.get('hanPrc')} / {item.get('spc1')}㎡"
            send_msg(msg)
            saved = load_json("saved_naver_history.json")
            if item.get('atclNo') not in saved:
                saved.append(item.get('atclNo'))
                save_json("saved_naver_history.json", saved)
        else:
            send_msg(f"✅ 연결 성공 (현재 매물 없음)")
    else:
        send_msg("❌ 데이터 가져오기 실패 (네이버 차단)")

def process_telegram():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    offset = 0
    if os.path.exists("last_update_id.txt"):
        with open("last_update_id.txt", "r") as f: 
            try: offset = int(f.read())
            except: pass

    try:
        res = session.get(url, params={"offset": offset + 1, "timeout": 5}).json()
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
                session.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", params={"callback_query_id": cb["id"]})
                
                if data == "MAIN":
                    send_msg("⚙️ 설정 메뉴", get_main_menu())
                    delete_msg(msg_id)
                elif data == "MENU_GU":
                    send_msg("🌍 감시할 구 선택", get_gu_menu(watchlist))
                    delete_msg(msg_id)
                elif data.startswith("TOGGLE_GU"):
                    _, name, code = data.split(":")
                    exists = next((i for i,x in enumerate(watchlist) if x['code']==code), -1)
                    if exists > -1: 
                        watchlist.pop(exists)
                        send_msg(f"🗑️ {name}구 해제")
                    else: 
                        watchlist.append({"type":"GU", "name":name, "code":code})
                        test_connection("GU", code, name)
                    is_changed = True
                    send_msg("🌍 감시할 구 선택", get_gu_menu(watchlist))
                    delete_msg(msg_id)
                elif data == "MENU_APT":
                    send_msg("⌨️ 아파트 이름을 입력하세요 (예: 잠실엘스)", {"inline_keyboard": [[{"text":"🔙 취소","callback_data":"MAIN"}]]})
                    delete_msg(msg_id)
                elif data.startswith("ADD_APT"):
                    _, code, name = data.split(":")
                    if not any(x['code']==code for x in watchlist):
                        watchlist.append({"type":"APT", "name":name, "code":code})
                        test_connection("APT", code, name)
                        is_changed = True
                    else: send_msg("⚠️ 이미 있어요.")
                    delete_msg(msg_id)
                elif data == "SHOW_LIST":
                    txt = "📋 감시 목록:\n" + "\n".join([f"- {w['name']}" for w in watchlist]) if watchlist else "📭 없음"
                    send_msg(txt, get_main_menu())
                    delete_msg(msg_id)
            
            elif "message" in item:
                text = item["message"].get("text", "")
                if text == "/start":
                    send_msg("🤖 네이버 비서입니다.", get_main_menu())
                elif not text.startswith("/"):
                    send_msg(f"🔎 '{text}' 검색 시도...")
                    complexes, error_msg = search_complex(text)
                    if complexes:
                        btns = []
                        for c in complexes[:5]:
                            btns.append([{"text": f"🏢 {c['complexName']}", "callback_data": f"ADD_APT:{c['complexNo']}:{c['complexName']}"}])
                        btns.append([{"text":"🔙 취소","callback_data":"MAIN"}])
                        send_msg(f"👇 결과 선택:", {"inline_keyboard": btns})
                    else:
                        send_msg(error_msg)

        if is_changed: save_json(WATCHLIST_FILE, watchlist)
        with open("last_update_id.txt", "w") as f: f.write(str(offset))
        return True
    except: return False

def check_naver_listings():
    watchlist = load_json(WATCHLIST_FILE)
    if not watchlist: return
    saved = load_json("saved_naver_history.json")
    
    for target in watchlist:
        time.sleep(1)
        url = "https://m.land.naver.com/article/getArticleList" if target['type'] == 'GU' else "https://m.land.naver.com/complex/getComplexArticleList"
        params = {"tradTpCd": "A1", "order": "date_desc"}
        if target['type'] == 'GU': params.update({"cortarNo": target['code'], "rletTpCd": "APT", "prcMax": 300000})
        else: params.update({"hscpNo": target['code'], "showR0": "N"})
        
        res = naver_request(url, params)
        if not res: continue

        try:
            items = res.json().get('result', {}).get('list', [])
            for item in items:
                aid = item.get('atclNo')
                if aid in saved: continue
                apt = item.get('atclNm')
                price = item.get('hanPrc')
                area = item.get('spc1')
                link = f"https://m.land.naver.com/article/info/{aid}"
                send_msg(f"🔔 [{target['name']} 신규]\n🏢 {apt}\n💰 {price} / {area}㎡\n🔗 {link}")
                saved.append(aid)
        except: continue
    
    if len(saved) > 2000: saved = saved[-2000:]
    save_json("saved_naver_history.json", saved)

if __name__ == "__main__":
    print("🚀 봇 재가동")
    end_time = time.time() + (5 * 60)
    while time.time() < end_time:
        process_telegram()
        if int(time.time()) % 60 == 0:
            check_naver_listings()
        time.sleep(0.5)
