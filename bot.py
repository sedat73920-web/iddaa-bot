import os
import sys
import time
import threading
import requests
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

print(">>> [TEST 1] bot.py baslatildi! <<<")

# ==========================================
# 1. KULLANICI & API YAPILANDIRMASI
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
# 2. TELEGRAM MESAJ SERVİSİ
# ==========================================
def telegram_mesaji_ilet(icerik):
    try:
        print(f"[TELEGRAM] Mesaj gonderilmeye calisiliyor...")
        hedef_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        istek_paketi = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": icerik,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        yanit = requests.post(hedef_url, json=istek_paketi, timeout=10)
        print(f"[TELEGRAM YANIT] Kod: {yanit.status_code} | Yanit: {yanit.text}")
    except Exception as e:
        print(f"[TELEGRAM KRITIK HATA]: {e}")

# ==========================================
# 3. İSTATİSTİK AYRIŞTIRICI
# ==========================================
def istatistik_verilerini_cozumle(gelen_veri):
    toplam_sut = 0
    isabetli_sut = 0
    korner = 0

    if not gelen_veri or "response" not in gelen_veri:
        return 0, 0, 0

    takim_listesi = gelen_veri.get("response", [])
    if not isinstance(takim_listesi, list):
        return 0, 0, 0

    for takim in takim_listesi:
        istatistikler = takim.get("statistics", [])
        if not isinstance(istatistikler, list):
            continue

        for kalem in istatistikler:
            tip = str(kalem.get("type", "")).strip().lower()
            deger = kalem.get("value")

            sayisal = 0
            if deger is not None:
                metin = str(deger).strip()
                if metin.isdigit():
                    sayisal = int(metin)

            if "total shots" in tip:
                toplam_sut += sayisal
            elif "shots on goal" in tip:
                isabetli_sut += sayisal
            elif "corner" in tip:
                korner += sayisal

    return toplam_sut, isabetli_sut, korner

# ==========================================
# 4. CANLI MAÇ TARAMA MOTORU
# ==========================================
def canli_bulteni_tara():
    global bildirilen_maclar_kumesi, aktif_sifirlama_gunu

    bugun = datetime.now(TURKIYE_SAATI).day
    if bugun != aktif_sifirlama_gunu:
        bildirilen_maclar_kumesi.clear()
        aktif_sifirlama_gunu = bugun
        print("[HAFIZA] Yeni gun, liste temizlendi.")

    try:
        canli_istek = requests.get(API_LIVE_URL, headers=API_HEADERS, timeout=15)
        kalan_kota = canli_istek.headers.get("x-ratelimit-requests-remaining", "Bilinmiyor")

        if canli_istek.status_code != 200:
            print(f"[API HATASI] Kod: {canli_istek.status_code}")
            return

        ana_veri = canli_istek.json()
        maclar = ana_veri.get("response", [])

        if not maclar:
            print(f"[TARAMA] Canli mac yok. Kalan Kota: {kalan_kota}")
            return

        for mac in maclar:
            try:
                fikstur = mac.get("fixture", {})
                mac_id = fikstur.get("id")
                durum = fikstur.get("status", {})
                dakika = durum.get("elapsed")

                lig = mac.get("league", {})
                lig_adi = lig.get("name", "Bilinmeyen Lig")
                ulke = lig.get("country", "")

                if not dakika:
                    continue

                skor = mac.get("goals", {})
                ev_gol = skor.get("home") if skor.get("home") is not None else 0
                dep_gol = skor.get("away") if skor.get("away") is not None else 0
                fark = abs(ev_gol - dep_gol)

                if 60 <= dakika <= 75 and fark <= 2:
                    if mac_id in bildirilen_maclar_kumesi:
                        continue

                    ev_takim = mac.get("teams", {}).get("home", {}).get("name", "Ev")
                    dep_takim = mac.get("teams", {}).get("away", {}).get("name", "Dep")

                    stat_istek = requests.get(f"{API_STATS_URL}?fixture={mac_id}", headers=API_HEADERS, timeout=12)

                    if stat_istek.status_code == 200:
                        sut, isabet, korner = istatistik_verilerini_cozumle(stat_istek.json())

                        puan = 0
                        if sut >= 10: puan += 1
                        if isabet >= 4: puan += 1
                        if korner >= 5: puan += 1

                        if puan >= 2:
                            isabetsiz_sut = max(0, sut - isabet)
                            tehlike_skoru = (isabet * 2.5) + (isabetsiz_sut * 0.8) + (korner * 1.2)
                            tehlike_skoru = round(tehlike_skoru, 1)

                            if tehlike_skoru >= 22.0:
                                sinyal_tipi = "🔥 <b>YÜKSEK DEĞERLİ BASKI (A+ Sinyal)</b>"
                                kasa_tavsiyesi = "Kasanın %3.5 - %4'ü"
                            else:
                                sinyal_tipi = "⚡ <b>ORTA TEMPOLU BASKI (Standart Sinyal)</b>"
                                kasa_tavsiyesi = "Kasanın %2'si"

                            sut_ok = "✅" if sut >= 10 else "❌"
                            isabet_ok = "✅" if isabet >= 4 else "❌"
                            korner_ok = "✅" if korner >= 5 else "❌"

                            mesaj = (
                                f"{sinyal_tipi}\n\n"
                                f"🏆 <b>Lig:</b> {ulke} - {lig_adi}\n"
                                f"⚽ <b>Maç:</b> <b>{ev_takim}</b> {ev_gol} - {dep_gol} <b>{dep_takim}</b>\n"
                                f"⏱ <b>Dakika:</b> {dakika}'\n\n"
                                f"📊 <b>Canlı Veriler:</b>\n"
                                f"• Toplam Şut: <b>{sut}</b> {sut_ok}\n"
                                f"• İsabetli Şut: <b>{isabet}</b> {isabet_ok}\n"
                                f"• Korner: <b>{korner}</b> {korner_ok}\n"
                                f"🎯 <b>Tehlike İndeksi:</b> <b>{tehlike_skoru} Puan</b>\n\n"
                                f"💰 <b>Kasa Tavsiyesi:</b> {kasa_tavsiyesi}\n"
                                f"💡 <b>Seçenek:</b> Canlıda '1 Gol Daha' oranını değerlendirin."
                            )

                            telegram_mesaji_ilet(mesaj)
                            bildirilen_maclar_kumesi.add(mac_id)
                            print(f"[BILDIRILDI] {ev_takim} vs {dep_takim}")

            except Exception as e:
                print(f"[TEKIL MAC HATA]: {e}")

        print(f"[OZET] Canli Toplam: {len(maclar)} | Kalan Kota: {kalan_kota}")

    except Exception as e:
        print(f"[GENEL TARAMA HATA]: {e}")

# ==========================================
# 5. ARKA PLAN DÖNGÜSÜ
# ==========================================
def analiz_dongusu():
    print(">>> [TEST 2] analiz_dongusu thread'i basladi! Telegram mesaji atiliyor... <<<")
    telegram_mesaji_ilet("🚀 <b>Hibrit Analiz Sistemi Devrede!</b>\n\nSistem Render uzerinde aktif, maclar taranmaya baslandi.")

    while True:
        try:
            anlik = datetime.now(TURKIYE_SAATI)
            saat = anlik.hour
            dakika = anlik.minute
            hafta_sonu = anlik.weekday() >= 5

            calissin = False
            bekleme = 300

            if hafta_sonu:
                if (14 <= saat < 23) or (saat == 23 and dakika <= 55):
                    calissin = True
                    bekleme = 360
            else:
                if (18 <= saat < 23 and (saat > 18 or dakika >= 30)) or (saat == 23 and dakika <= 55):
                    calissin = True
                    bekleme = 300

            if calissin:
                canli_bulteni_tara()
                time.sleep(bekleme)
            else:
                print(f"[BEKLEME] Mac saatleri disi ({saat:02d}:{dakika:02d}). 10 dk uyku...")
                time.sleep(600)

        except Exception as e:
            print(f"[DÖNGÜ HATA]: {e}")
            time.sleep(30)

# ==========================================
# 6. RENDER UYKU ÖNLEYİCİ WEBSERVER
# ==========================================
class RenderHealthServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot Calisiyor.")

    def log_message(self, format, *args):
        return

def web_sunucu_calistir():
    try:
        port = int(os.environ.get("PORT", 8080))
        print(f">>> [TEST 3] Web sunucusu {port} portunda baslatiliyor... <<<")
        sunucu = HTTPServer(("0.0.0.0", port), RenderHealthServer)
        print(f">>> [TEST 4] Web sunucusu basariyla dinliyor! <<<")
        sunucu.serve_forever()
    except Exception as e:
        print(f"[WEB SUNUCU HATA]: {e}")

# Threadleri baslat
t_web = threading.Thread(target=web_sunucu_calistir, daemon=True)
t_web.start()

# Ana programı canlı tut
analiz_dongusu()
