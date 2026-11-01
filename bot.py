import time
import requests
from datetime import datetime, time as dt_time

# --- AYARLAR VE YAPILANDIRMA ---
API_KEY = "9009059246:AAHcZwhdQqwl6qkI28LeM_1hQLxpwsc41wU"  # Telegram Bot Token / API Anahtarı
BASE_URL = "https://api.example.com/v1"  # API servis adresiniz
WHITE_LIST = ["Süper Lig", "Premier League", "La Liga", "Serie A", "Bundesliga"]  # Beyaz liste ligler

# İstek sayacı ve sıfırlama takibi için değişkenler
request_count = 0
last_reset_time = time.time()

def check_daily_limit():
    global request_count, last_reset_time
    current_time = time.time()
    
    # 24 saatte bir sayacı sıfırla (86400 saniye = 24 saat)
    if current_time - last_reset_time >= 86400:
        request_count = 0
        last_reset_time = current_time

    if request_count >= 100:
        print("Günlük 100 istek sınırına ulaşıldı. Kota yenilenene kadar bekleniyor...")
        return False
    return True

def api_request(endpoint, params=None):
    global request_count
    if not check_daily_limit():
        return None
        
    url = f"{BASE_URL}/{endpoint}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        request_count += 1
        print(f"API İsteği Yapıldı. Günlük Toplam İstek: {request_count}/100")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API Hatası: {response.status_code}")
            return None
    except Exception as e:
        print(f"Bağlantı Hatası: {e}")
        return None

def send_telegram_message(message):
    bot_token = "9009059246:AAHcZwhdQqwl6qkI28LeM_1hQLxpwsc41wU"
    chat_id = "TELEGRAM_CHAT_ID"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Gönderim Hatası: {e}")

def is_within_working_hours():
    """Çalışma saatlerini kontrol eder: 13:00 ile 00:30 arası"""
    now = datetime.now().time()
    start_time = dt_time(13, 0)
    end_time = dt_time(0, 30)
    
    if start_time <= now or now <= end_time:
        return True
    return False

def scan_matches():
    print(f"\n--- Tarama Başlatıldı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    
    data = api_request("live", params={"status": "all"})
    if not data or "matches" not in data:
        print("Canlı maç verisi alınamadı.")
        return

    matches = data["matches"]
    print(f"Toplam canlı maç sayısı: {len(matches)}")

    for match in matches:
        league = match.get("league_name")
        minute = match.get("minute", 0)
        score_diff = abs(match.get("home_score", 0) - match.get("away_score", 0))
        match_id = match.get("id")
        home_team = match.get("home_team")
        away_team = match.get("away_team")

        if league in WHITE_LIST and score_diff <= 1:
            is_first_half_target = (25 <= minute <= 35)
            is_second_half_target = (60 <= minute <= 78)

            if is_first_half_target or is_second_half_target:
                print(f"Şartları sağlayan maç bulundu: {home_team} vs {away_team} (Dakika: {minute})")
                
                stats = api_request(f"matches/{match_id}/stats")
                
                if stats:
                    message = (
                        f"🚨 *Maç Sinyali Tespit Edildi!* \n\n"
                        f"⚽ {home_team} vs {away_team}\n"
                        f"🏆 Lig: {league}\n"
                        f"⏱ Dakika: {minute}\n"
                        f"📊 Skor Farkı: {score_diff}"
                    )
                    send_telegram_message(message)
                    print(f"Bildirim gönderildi: {home_team} - {away_team}")

def main():
    print("Bot başlatıldı. Çalışma saat aralığı: 13:00 - 00:30 (20 dakikalık periyotlar)")
    while True:
        if is_within_working_hours():
            scan_matches()
        else:
            print(f"Çalışma saatleri dışındayız ({datetime.now().strftime('%H:%M')}). Bekleniyor...")
        
        time.sleep(1200)

if __name__ == "__main__":
    main()
