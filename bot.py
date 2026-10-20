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
bildirilen_korner = set()

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

            # 1. ERKEN KORNER STRATEJİSİ (15-32 dk, fark <= 1, Korner >= 5)
            if 15 <= minute <= 32 and abs(goals_h - goals_a) <= 1 and f_id not in bildirilen_korner:
                st_res = requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={f_id}", headers=HEADERS, timeout=15).json()
                sut, isabet, korner = 0, 0, 0
                if "response" in st_res and len
