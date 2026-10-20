import os
import time
import requests
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

TOKEN = "8912502756:AAHe_0qe2dokTtRXh1EYpgVexOTuCHdZk6Q"
CHAT_ID = "769164600"
KEY = "d940a36cc7b3b1f03bd41b8880721772"

URL = "https://v3.football.api-sports.io/fixtures?live=all"
HEADERS = {
    "x-rapidapi-host": "v3.football.api-sports.io",
    "x-rapidapi-key": KEY
}

LIGLER = {
    203, 204, 552, 39, 40, 41, 45, 48, 140, 141, 143,
    135, 136, 137, 78, 79, 81, 61, 62, 66, 2, 3,
    848, 88, 94, 144, 179, 253, 71, 128
}

bildirilen_iy = set()
bildirilen_ms = set()

# Türkiye saati (UTC+3)
TR_TZ = timezone(timedelta(hours=3))

class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot Aktif!")

def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyServer)
    server.serve_forever()

def telegram_gonder(mesaj):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": mesaj, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print("Telegram hatasi:", e)

def canli_tara():
    try:
        res = requests.get(URL, headers=HEADERS, timeout=15).json()
        if not res or "response" not in res:
            return

        for match in res["response"]:
            f_id = match["fixture"]["id"]
            minute = match["fixture"]["status"]["elapsed"]
            lig_id = match["league"]["id"]

            if lig_id not in LIGLER or not minute:
                continue

            goals_h = match["goals"]["home"] or 0
            goals_a = match["goals"]["away"] or 0
            ev = match["teams"]["home"]["name"]
            dep = match["teams"]["away"]["name"]
            lig_adi = match["league"]["name"]

            # 1. YARI STRATEJİSİ: 15-23 dk, skor 0-0
            if 15 <= minute <= 23 and goals_h == 0 and goals_a == 0:
                if f_id not in bildirilen_iy:
                    st_res = requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={f_id}", headers=HEADERS, timeout=15).json()
                    sut, isabet, korner = 0, 0, 0
                    if "response" in st_res and len(st_res["response"]) >= 2:
                        for team in st_res["response"]:
                            for s in team["statistics"]:
                                val = s["value"] or 0
                                if s["type"] == "Total Shots": sut += int(val)
                                elif s["type"] == "Shots on Goal": isabet += int(val)
                                elif s["type"] == "Corner Kicks": korner += int(val)

                        if sut >= 4 and isabet >= 2 and korner >= 2:
                            msg = (
                                f"🔥 <b>İY 0.5 ÜST SİNYALİ!</b>\n\n"
                                f"🏆 <b>Lig:</b> {lig_adi}\n"
                                f"⚽ <b>Maç:</b> {ev} vs {dep}\n"
                                f"⏱ <b>Dakika:</b> {minute}' | <b>Skor:</b> 0-0\n\n"
                                f"📊 <b>İstatistikler:</b>\n"
                                f"• Toplam Şut: {sut}\n"
                                f"• İsabetli Şut: {isabet}\n"
                                f"• Korner: {korner}\n\n"
                                f"💡 <b>Tavsiye:</b> İY 0.5 Üst (1.35+ Oran Bekleyin)"
                            )
                            telegram_gonder(msg)
                            bildirilen_iy.add(f_id)

            # 2. YARI STRATEJİSİ: 65-75 dk, fark en fazla 1
            elif 65 <= minute <= 75 and abs(goals_h - goals_a) <= 1:
                if f_id not in bildirilen_ms:
                    st_res = requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={f_id}", headers=HEADERS, timeout=15).json()
                    sut, isabet, korner = 0, 0, 0
                    if "response" in st_res and len(st_res["response"]) >= 2:
                        for team in st_res["response"]:
                            for s in team["statistics"]:
                                val = s["value"] or 0
                                if s["type"] == "Total Shots": sut += int(val)
                                elif s["type"] == "Shots on Goal": isabet += int(val)
                                elif s["type"] == "Corner Kicks": korner += int(val)

                        if sut >= 12 and isabet >= 5 and korner >= 6:
                            msg = (
                                f"⚡️ <b>2. YARI GOL SİNYALİ!</b>\n\n"
                                f"🏆 <b>Lig:</b> {lig_adi}\n"
                                f"⚽ <b>Maç:</b> {ev} {goals_h} - {goals_a} {dep}\n"
                                f"⏱ <b>Dakika:</b> {minute}'\n\n"
                                f"📊 <b>Baskı İstatistikleri:</b>\n"
                                f"• Toplam Şut: {sut}\n"
                                f"• İsabetli Şut: {isabet}\n"
                                f"• Korner: {korner}\n\n"
                                f"💡 <b>Tavsiye:</b> Sıradaki Gol / Maç Sonu 1 Gol Daha"
                            )
                            telegram_gonder(msg)
                            bildirilen_ms.add(f_id)

    except Exception as e:
        print("Tarama hatasi:", e)

def ana_dongu():
    telegram_gonder("🚀 <b>Akıllı Tasarruf Modu Devrede!</b>\nBot maç saatlerine göre otomatik çalışacak, günlük kota aşılmayacak.")
    while True:
        simdi = datetime.now(TR_TZ)
        hafta_sonu = simdi.weekday() >= 5
        saat = simdi.hour
        dakika = simdi.minute

        # Tarama saatleri kontrolü
        calissin_mi = False
        bekleme_suresi = 300  # Varsayılan uyku: 5 dakika

        if hafta_sonu:
            # Hafta sonu: 14:00 - 23:45 arası aktif
            if 14 <= saat <= 23:
                calissin_mi = True
                bekleme_suresi = 360  # 6 dakikada bir istek
        else:
            # Hafta içi: 19:00 - 23:45 arası aktif
            if 19 <= saat <= 23:
                calissin_mi = True
                bekleme_suresi = 210  # 3.5 dakikada bir istek

        if calissin_mi:
            canli_tara()
            time.sleep(bekleme_suresi)
        else:
            # Maç olmayan saatlerde sunucuyu açık tut ama API'ye istek atma
            time.sleep(600)  # 10 dakika bekle ve saati tekrar kontrol et

if __name__ == "__main__":
    t = threading.Thread(target=keep_alive, daemon=True)
    t.start()
    ana_dongu()
