import os
import time
import requests
from datetime import datetime, time as dt_time
from threading import Thread
from flask import Flask

# --- RENDER PORT HATASI ÇÖZÜCÜ WEB SUNUCUSU ---
app = Flask('')

@app.route('/')
def home():
    return "Bot aktif ve çalışıyor!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- AYARLAR VE YAPILANDIRMA ---
API_KEY = "9009059246:AAHcZwhdQqwl6qkI28LeM_1hQLxpwsc41wU"
BASE_URL = "https://api.example.com/v1"
WHITE_LIST = ["Süper Lig", "Premier League", "La Liga", "Serie A", "Bundesliga"]

request_count = 0
last_reset_time = time.time()

def check_daily_limit():
    global request_count, last_reset_time
    current_time = time.time()
    if current_time - last_reset_time >= 86400:
        request_count = 0
        last_reset_time = current_time
    if request_count >= 100:
        print("Günlük 100 istek sınırına ulaşıldı.")
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
        if response.status_code == 200:
            return response.json()
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
        print(f"Telegram Hatası: {e}")

def is_within_working_hours():
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
        return
    for match in data["matches"]:
        league = match.get("league_name")
        minute = match.get("minute", 0)
        score_diff = abs(match.get("home_score", 0) - match.get("away_score", 0))
        match_id = match.get("id")
        home_team = match.get("home_team")
        away_team = match.get("away_team")

        if league in WHITE_LIST and score_diff <= 1:
            if (25 <= minute <= 35) or (60 <= minute <= 78):
                stats = api_request(f"matches/{match_id}/stats")
                if stats:
                    message = f"🚨 *Maç Sinyali!* \n⚽ {home_team} vs {away_team}\n🏆 {league}\n⏱ Dakika: {minute}"
                    send_telegram_message(message)

def bot_loop():
    print("Bot döngüsü başlatıldı (13:00 - 00:30, 20 dk periyot).")
    while True:
        if is_within_working_hours():
            scan_matches()
        time.sleep(1200)

if __name__ == "__main__":
    keep_alive()
    bot_loop()
