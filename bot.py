import os
import time
import requests
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# --- KULLANICI AYARLARI ---
TOKEN = "8912502756:AAHe_0qe2dokTtRXh1EYpgVexOTuCHdZk6Q"
CHAT_ID = "769164600"
KEY = "d940a36cc7b3b1f03bd41b8880721772"

URL_LIVE = "https://v3.football.api-sports.io/fixtures?live=all"
URL_STATS = "https://v3.football.api-sports.io/fixtures/statistics"

HEADERS = {
    "x-rapidapi-host": "v3.football.api-sports.io",
    "x-rapidapi-key": KEY
}

# TÜRKİYE RESMİ İDDAA BÜLTENİ LİGLERİ & KUPALARI
IDDAA_LIGLERI = {
    848, 2, 3, 531, 5, 4, 1, 6, 13, 11, 16,
    203, 204, 552, 555,
    39, 40, 41, 42, 45, 48, 46,
    140, 141, 143,
    135, 136, 137,
    78, 79, 81,
    61, 62, 66,
    88, 90, 89, 94, 96, 95, 144, 147, 179, 180,
    218, 219, 207, 209, 119, 120, 103, 104, 113,
    114, 106, 108, 197, 199, 345, 347, 235, 237,
    253, 257, 71, 72, 73, 128, 130, 262, 239, 98, 102, 292, 294
}

TR_TZ = timezone(timedelta(hours=3))
bildirilen_maclar = set()
son_sifirlama_gunu = datetime.now(TR_TZ).day

# --- RENDER UYKU ÖNLEYİCİ WEBSERVER ---
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot 7/24 Kesintisiz Aktif!")

    def log_message(self, format, *args):
        return

def keep_alive():
    try:
        port = int(os.environ.get("PORT", 8080))
        server = HTTPServer(("0.0.0.0", port), DummyServer)
        print(f"[SİSTEM] Web sunucusu {port} portunda baslatildi.")
        server.serve_forever()
    except Exception as e:
        print("[HATA] Web sunucu hatasi:", e)

# --- TELEGRAM MESAJ GÖNDERİCİ ---
def telegram_gonder(mesaj):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": mesaj,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            print(f"[TELEGRAM HATA] Kod: {resp.status_code} - Yanit: {resp.text}")
    except Exception as e:
        print("[TELEGRAM BAĞLANTI HATASI]:", e)

# --- İSTATİSTİK PARSER ---
def istatistikleri_coz(raw_response):
    toplam_sut = 0
    isabetli_sut =
