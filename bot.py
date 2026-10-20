import os
import sys
import time
import threading
import requests
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==========================================
# 1. TEMEL KULLANICI VE API YAPILANDIRMASI
# ==========================================
TELEGRAM_BOT_TOKEN = "8912502756:AAHe_0qe2dokTtRXh1EYpgVexOTuCHdZk6Q"
TELEGRAM_CHAT_ID = "769164600"
FOOTBALL_API_KEY = "d940a36cc7b3b1f03bd41b8880721772"

API_LIVE_URL = "https://v3.football.api-sports.io/fixtures?live=all"
API_STATS_URL = "https://v3.football.api-sports.io/fixtures/statistics"

API_HEADERS = {
    "x-rapidapi-host": "v3.football.api-sports.io",
    "x-rapidapi-key": FOOTBALL_API_KEY
}

TURKIYE_SAATI = timezone(timedelta(hours=3))
bildirilen_maclar_kumesi = set()
aktif_sifirlama_gunu = datetime.now(TURKIYE_SAATI).day

# ==========================================
# 2. RENDER BULUT UYKU ÖNLEYİCİ WEBSERVER
# ==========================================
class RenderHealthServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Iddaa Canli Bot Aktif!")

    def log_message(self, format, *args):
        return

def arka_plan_web_sunucusu_baslat():
    try:
        atanan_port = int(os.environ.get("PORT", 8080))
        sunucu = HTTPServer(("0.0.0.0", atanan_port), RenderHealthServer)
        print(f"[BILGI] Web sunucusu {atanan_port} portunda baslatildi.")
        sunucu.serve_forever()
    except Exception as e:
        print(f"[UYARI] Web sunucu hatasi: {e}")

# ==========================================
# 3. TELEGRAM MESAJ GÖNDERİCİ
# ==========================================
def telegram_mesaji_ilet(icerik):
    try:
        hedef_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        istek_paketi = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": icerik,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        yanit = requests.post(hedef_url, json=istek_paketi, timeout=12)
        if yanit.status_code == 200:
            print("[TELEGRAM] Bildirim basariyla gonderildi.")
        else:
            print(f"[TELEGRAM HATA] Kod: {yanit.status_code} - Yanit: {yanit.text}")
    except Exception as e:
        print(f"[TELEGRAM AG HATASI]: {e}")

# ==========================================
# 4. İSTATİSTİK AYRIŞTIRICI FONKSİYON
# ==========================================
def istatistik_verilerini_cozumle(gelen_veri):
    toplam_sut_miktari = 0
    isabetli_sut_miktari = 0
    korner_miktari = 0

    if not gelen_veri or "response" not in gelen_veri:
        return 0, 0, 0

    takim_istatistik_listesi = gelen_veri.get("response", [])
    if not isinstance(takim_istatistik_listesi, list):
        return 0, 0, 0

    for takim in takim_istatistik_listesi:
        istatistik_kalemleri = takim.get("statistics", [])
        if not isinstance(istatistik_kalemleri, list):
            continue

        for kalem in istatistik_kalemleri:
            kalem_tipi = str(kalem.get("type", "")).strip().lower()
            kalem_degeri = kalem.get("value")

            sayisal_deger = 0
            if kalem_degeri is not None:
                metin_deger = str(kalem_degeri).strip()
                if metin_deger.isdigit():
                    sayisal_deger = int(metin_deger)

            if "total shots" in kalem_tipi:
                toplam_sut_miktari += sayisal_deger
            elif "shots on goal" in kalem_tipi:
                isabetli_sut_miktari += sayisal_deger
            elif "corner" in kalem_tipi:
                korner_miktari += sayisal_deger

    return toplam_sut_miktari, isabetli_sut_miktari, korner_miktari

# ==========================================
# 5. CANLI MAÇ TARAMA MOTORU
# ==========================================
def canli_bulteni_tara():
    global bildirilen_maclar_kumesi, aktif_sifirlama_gunu

    # Gece yarısı hafıza temizliği
    su_anki_gun = datetime.now(TURKIYE_SAATI).day
    if su_anki_gun != aktif_sifirlama_gunu:
        bildirilen_maclar_kumesi.clear()
        aktif_sifirlama_gunu = su_anki_gun
        print("[HAFIZA] Yeni gun, bildirim listesi sifirlandi.")

    try:
        canli_istek = requests.get(API_LIVE_URL, headers=API_HEADERS, timeout=15)
        kalan_api_kotasi = canli_istek.headers.get("x-ratelimit-requests-remaining", "Bilinmiyor")

        if canli_istek.status_code != 200:
            print(f"[API HATASI] Kod: {canli_istek.status_code} | Kalan Kota: {kalan_api_kotasi}")
            return

        ana_veri = canli_istek.json()
        canli_mac_listesi = ana_veri.get("response", [])

        if not canli_mac_listesi:
            print(f"[TARAMA] Canli mac yok. Kalan Kota: {kalan_api_kotasi}")
            return

        dakika_tutan_sayisi = 0

        for mac in canli_mac_listesi:
            try:
                fikstur_bilgisi = mac.get("fixture", {})
                mac_id = fikstur_bilgisi.get("id")
                durum_bilgisi = fikstur_bilgisi.get("status", {})
                dakika = durum_bilgisi.get("elapsed")

                lig_bilgisi = mac.get("league", {})
                lig_adi = lig_bilgisi.get("name", "Bilinmeyen Turnuva")
                ulke_adi = lig_bilgisi.get("country", "")

                if not dakika:
                    continue

                skor_bilgisi = mac.get("goals", {})
                ev_gol = skor_bilgisi.get("home") if skor_bilgisi.get("home") is not None else 0
                dep_gol = skor_bilgisi.get("away") if skor_bilgisi.get("away") is not None else 0
                skor_farki = abs(ev_gol - dep_gol)

                # DAKİKA 60 - 75 & FARK <= 2 (TÜM DÜNYA MAÇLARI)
                if 60 <= dakika <= 75 and skor_farki <= 2:
                    dakika_tutan_sayisi += 1

                    if mac_id in bildirilen_maclar_kumesi:
                        continue

                    ev_takim = mac.get("teams", {}).get("home", {}).get("name", "Ev Sahibi")
                    dep_takim = mac.get("teams", {}).get("away", {}).get("name", "Deplasman")

                    # Sadece şartı sağlayan maça istatistik isteği at (Kota koruması)
