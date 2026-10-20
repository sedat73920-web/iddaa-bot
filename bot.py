import os
import time
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# API VE TELEGRAM AYARLARI
TELEGRAM_BOT_TOKEN = "8912502756:AAHe_0qe2dokTtRXh1EYpgVexOTuCHdZk6Q"
TELEGRAM_CHAT_ID = "769164600"
FOOTBALL_API_KEY = "d940a36cc7b3b1f03bd41b8880721772"

HEADERS = {
    "x-rapidapi-host": "v3.football.api-sports.io",
    "x-rapidapi-key": FOOTBALL_API_KEY
}

GÖNDERİLEN_MAÇLAR = set()

# Render'ın kapanmaması için basit web sunucusu
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot 7/24 aktif calisiyor!")

def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyServer)
    server.serve_forever()

def telegram_bildir(mesaj):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mesaj,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Telegram hatası:", e)

def canli_maclari_tara():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    try:
        yanit = requests.get(url, headers=HEADERS, timeout=15)
        veri = yanit.json()
        if "response" not in veri:
            return
        
        maclar = veri["response"]
        for mac in maclar:
            fixture_id = mac["fixture"]["id"]
            dakika = mac["fixture"]["status"]["elapsed"]
            skor_ev = mac["goals"]["home"] or 0
            skor_dep = mac["goals"]["away"] or 0
            ev_takim = mac["teams"]["home"]["name"]
            dep_takim = mac["teams"]["away"]["name"]
            lig_adi = mac["league"]["name"]

            if not dakika:
                continue

            # 1. YARI STRATEJİSİ: 15-23 dk, skor 0-0
            if 15 <= dakika <= 23 and skor_ev == 0 and skor_dep == 0:
                kilit = f"{fixture_id}_iy"
                if kilit not in GÖNDERİLEN_MAÇLAR:
                    stat_url = f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fixture_id}"
                    st_yanit = requests.get(stat_url, headers=HEADERS, timeout=15).json()
                    
                    toplam_sut = 0
                    isabetli_sut = 0
                    korner = 0

                    if "response" in st_yanit and len(st_yanit["response"]) >= 2:
                        for team_stat in st_yanit["response"]:
                            for s in team_stat["statistics"]:
                                val = s["value"] or 0
                                if s["type"] == "Total Shots":
                                    toplam_sut += int(val)
                                elif s["type"] == "Shots on Goal":
                                    isabetli_sut += int(val)
                                elif s["type"] == "Corner Kicks":
                                    korner += int(val)

                        if toplam_sut >= 4 and isabetli_sut >= 2 and korner >= 2:
                            mesaj = (
                                f"🔥 <b>İY 0.5 ÜST SİNYALİ!</b>\n\n"
                                f"🏆 <b>Lig:</b> {lig_adi}\n"
                                f"⚽ <b>Maç:</b> {ev_takim} vs {dep_takim}\n"
                                f"⏱ <b>Dakika:</b> {dakika}' | <b>Skor:</b> 0-0\n\n"
                                f"📊 <b>İstatistikler:</b>\n"
                                f"• Toplam Şut: {toplam_sut}\n"
                                f"• İsabetli Şut: {isabetli_sut}\n"
                                f"• Korner: {korner}\n\n"
                                f"💡 <b>Tavsiye:</b> İY 0.5 Üst (1.35+ Oran Bekleyin)"
                            )
                            telegram_bildir(mesaj)
                            GÖNDERİLEN_MAÇLAR.add(kilit)

            # 2. YARI STRATEJİSİ: 65-75 dk, fark en fazla 1
            elif 65 <= dakika <= 75 and abs(skor_ev - skor_dep) <= 1:
                kilit = f"{fixture_id}_ms"
                if kilit not in GÖNDERİLEN_MAÇLAR:
                    stat_url = f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fixture_id}"
                    st_yanit = requests.get(stat_url, headers=HEADERS, timeout=15).json()
                    
                    toplam_sut = 0
                    isabetli_sut = 0
                    korner = 0

                    if "response" in st_yanit and len(st_yanit["response"]) >= 2:
                        for team_stat in st_yanit["response"]:
                            for s in team_stat["statistics"]:
                                val = s["value"] or 0
                                if s["type"] == "Total Shots":
                                    toplam_sut += int(val)
                                elif s["type"] == "Shots on Goal":
                                    isabetli_sut += int(val)
                                elif s["type"] == "Corner Kicks":
                                    korner += int(val)

                        if toplam_sut >= 12 and isabetli_sut >= 5 and korner >= 6:
                            mesaj = (
                                f"⚡️ <b>2. YARI GOL SİNYALİ!</b>\n\n"
                                f"🏆 <b>Lig:</b> {lig_adi}\n"
                                f"⚽ <b>Maç:</b> {ev_takim} {skor_ev} - {skor_dep} {dep_takim}\n"
                                f"⏱ <b>Dakika:</b> {dakika}'\n\n"
                                f"📊 <b>Baskı İstatistikleri:</b>\n"
                                f"• Toplam Şut: {toplam_sut}\n"
                                f"• İsabetli Şut: {isabetli_sut}\n"
                                f"• Korner: {korner}\n\n"
                                f"💡 <b>Tavsiye:</b> Sıradaki Gol / Maç Sonu 1 Gol Daha"
                            )
                            telegram_bildir(mesaj)
                            GÖNDERİLEN_MAÇLAR.add(kilit)

    except Exception as e:
        print("Tarama hatası:", e)

def ana_dongu():
    telegram_bildir("🚀 <b>Bot Bulut Sunucuda Başlatıldı!</b>\n7/24 İY 0.5 Üst ve 2. Yarı Gol stratejileri devrede.")
    print("Tarama başladı...")
    while True:
        canli_maclari_tara()
        time.sleep(60)

if __name__ == "__main__":
    t = threading.Thread(target=keep_alive, daemon=True)
    t.start()
    ana_dongu()

