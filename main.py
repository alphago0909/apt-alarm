import requests
import xml.etree.ElementTree as ET
import urllib3
import time
import os

# 보안 경고 끄기
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 깃허브 금고에서 키를 꺼내옵니다
TELEGRAM_TOKEN = os.environ.get('TG_TOKEN')
CHAT_ID = os.environ.get('TG_ID')
SERVICE_KEY = os.environ.get('SEOUL_KEY')

# 서울시 25개 구 코드
SEOUL_CODES = {
    "강남구": "11680", "서초구": "11650", "송파구": "11710", "강동구": "11740",
    "마포구": "11440", "용산구": "11170", "성동구": "11200", "광진구": "11215",
    "종로구": "11110", "중구": "11140", "동대문구": "11230", "서대문구": "11410",
    "영등포구": "11560", "동작구": "11590", "관악구": "11620", "강서구": "11500",
    "양천구": "11470", "구로구": "11530", "금천구": "11545", "은평구": "11380",
    "성북구": "11290", "강북구": "11305", "도봉구": "11320", "노원구": "11350",
    "중랑구": "11260"
}

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.get(url, params=params)
    except Exception:
        pass

def safe_get_text(item, tag, default=""):
    found = item.find(tag)
    if found is not None and found.text is not None:
        return found.text.strip()
    return default

def load_saved_deals():
    if not os.path.exists("saved_deals.txt"):
        return []
    with open("saved_deals.txt", "r", encoding="utf-8") as f:
        return f.read().splitlines()

def save_deal(unique_id):
    with open("saved_deals.txt", "a", encoding="utf-8") as f:
        f.write(unique_id + "\n")

def check_new_deals():
    # 현재 날짜 기준 (YYYYMM)
    deal_ymd = time.strftime("%Y%m") 
    
    urls = {
        "매매": "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade",
        "전월세": "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent",
        "분양권": "https://apis.data.go.kr/1613000/RTMSDataSvcSilvTrade/getRTMSDataSvcSilvTrade"
    }
    
    saved_deals = load_saved_deals()
    
    for gu_name, lawd_cd in SEOUL_CODES.items():
        time.sleep(1) # 차단 방지
        
        for type_name, url in urls.items():
            params = {"serviceKey": SERVICE_KEY, "LAWD_CD": lawd_cd, "DEAL_YMD": deal_ymd}
            
            try:
                response = requests.get(url, params=params, verify=False, timeout=10)
                if response.status_code != 200: continue
                    
                root = ET.fromstring(response.content)
                items = root.findall("body/items/item")
                
                for item in items:
                    apt = safe_get_text(item, "aptNm", "아파트")
                    floor = safe_get_text(item, "floor", "0")
                    
                    # 날짜 처리
                    day = safe_get_text(item, "dealDay", "0")
                    rent_day = safe_get_text(item, "dealDay", day)
                    real_day = rent_day if type_name == "전월세" else day

                    # ★★★ 면적 추가 (전용면적) ★★★
                    # 전월세/분양권 등 API마다 태그가 다를 수 있어 두 가지 다 시도
                    area = safe_get_text(item, "excluUseAr", "") 
                    if not area:
                         # 혹시 다른 태그일 경우 대비
                         area = safe_get_text(item, "contractArea", "0")

                    # 평수 계산 (소수점 1자리까지)
                    try:
                        area_float = float(area)
                        pyung = round(area_float / 3.3058, 1) # 3.3으로 나누기
                        area_str = f"{area_float}㎡ ({pyung}평)"
                    except:
                        area_str = f"{area}㎡"

                    # 가격 정보
                    if type_name == "전월세":
                        deposit = safe_get_text(item, "deposit", "0")
                        monthly = safe_get_text(item, "monthlyRent", "0")
                        price_str = f"전세 {deposit}" if monthly == "0" else f"월세 {deposit}/{monthly}"
                    else:
                        price = safe_get_text(item, "dealAmount", "0")
                        price_str = f"{type_name} {price}"

                    # 고유 ID에 면적도 포함 (같은 층, 같은 가격이라도 평수가 다르면 다른 거래니까요)
                    unique_id = f"{gu_name}|{type_name}|{apt}|{area}|{floor}층|{price_str}|{real_day}일"
                    
                    if unique_id not in saved_deals:
                        icon = "🏠" if type_name == "매매" else ("🔑" if type_name == "전월세" else "🎫")
                        
                        # ★★★ 알람 메시지에 면적 추가 ★★★
                        msg = (
                            f"🔔 [서울 {gu_name} - 신규 {type_name}]\n"
                            f"{icon} {apt} ({floor}층)\n"
                            f"📏 {area_str}\n"  # 여기에 면적 표시
                            f"💰 {price_str}만원\n"
                            f"📅 계약: {real_day}일"
                        )
                        
                        send_telegram_msg(msg)
                        save_deal(unique_id)
                        saved_deals.append(unique_id)
                        
            except Exception:
                continue

if __name__ == "__main__":
    check_new_deals()
