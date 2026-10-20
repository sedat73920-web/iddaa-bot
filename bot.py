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

bildirilen_maclar = set()
TR_TZ = timezone(timedelta(hours=3))

class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot Aktif!")

    def log_message(self, format, *args):
        return

def keep_alive():
    try:
        port = int(os.environ.get("PORT", 8080))
        server = HTTPServer(("0.0.0.0", port), DummyServer)
        server.serve_forever()
    except Exception as e:
        print("Web server hatasi:", e)

def telegram_gonder(mesaj):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": mesaj, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print("Telegram gonderim hatasi:", e)

def canli_tara():
    try:
        res = requests.get(URL, headers=HEADERS, timeout=15).json()
        if not res or "response" not in res:
            return

        for match in res["response"]:
            try:
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

                # 60 - 75 DAKİKA ARALIĞI (2-0 dahil fark en fazla 2)
                if 60 <= minute <= 75 and abs(goals_h - goals_a) <= 2:
                    if f_id not in bildirilen_maclar:
                        st_res = requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={f_id}", headers=HEADERS, timeout=15).json()
                        sut, isabet, korner = 0, 0, 0
                        if "response" in st_res and len(st_res["response"]) >= 2:
                            for team in st_res["response"]:
                                for s in team["statistics"]:
                                    val = s["value"] or 0
                                    if s["type"] == "Total Shots": sut += int(val)
                                    elif s["type"] == "Shots on Goal": isabet += int(val)
                                    elif s["type"] == "Corner Kicks": korner += int(val)

                            # Olgunlaşmış baskı kriterleri
                            if sut >= 11 and isabet >= 4 and korner >= 5:
                                msg = (
                                    f"⚡️ <b>2. YARI GOL SİNYALİ (60-75 dk)!</b>\n\n"
                                    f"🏆 <b>Lig:</b> {lig_adi}\n"
                                    f"⚽ <b>Maç:</b> {ev} {goals_h} - {goals_a} {dep}\n"
                                    f"⏱ <b>Dakika:</b> {minute}'\n\n"
                                    f"📊 <b>Baskı İstatistikleri:</b>\n"
                                    f"• Toplam Şut: <b>{sut}</b>\n"
                                    f"• İsabetli Şut: <b>{isabet}</b>\n"
                                    f"• Korner: <b>{korner}</b>\n\n"
                                    f"💡 <b>Tavsiye:</b> Sıradaki Gol / Maç Sonu 1 Gol Daha"
                                )
                                telegram_gonder(msg)
                                bildirilen_maclar.add(f_id)
            except Exception as match_err:
                print("Mac isleme hatasi:", match_err)

    except Exception as e:
        print("Genel tarama hatasi:", e)

def ana_dongu():
    telegram_gonder("🎯 <b>60-75 Dk Modu (2 Fark Dahil) Aktif!</b>\n• 2-0, 0-2 skorları radara eklendi.\n• Fark 2'den büyükse (3-0 vb.) elenir.\n• Şut >= 11, Korner >= 5 şartı korunuyor.")
    while True:
        try:
            simdi = datetime.now(TR_TZ)
            hafta_sonu = simdi.weekday() >= 5
            saat = simdi.hour

            calissin_mi = False
            bekleme_suresi = 300

            if hafta_sonu:
                if 14 <= saat <= 23:
                    calissin_mi = True
                    bekleme_suresi = 360
            else:
                if 19 <= saat <= 23:
                    calissin_mi = True
                    bekleme_suresi = 240

            if calissin_mi:
                canli_tara()
                time.sleep(bekleme_suresi)
            else:
                time.sleep(600)
        except Exception as loop_err:
            print("Ana dongu hatasi:", loop_err)
            time.sleep(60)

if __name__ == "__main__":
    t = threading.Thread(target=keep_alive, daemon=True)
    t.start()
    ana_dongu()
