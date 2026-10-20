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
    # UEFA ve Uluslararası
    848, 2, 3, 531, 5, 4, 1, 6, 13, 11, 16,
    # Türkiye
    203, 204, 552, 555,
    # İngiltere
    39, 40, 41, 42, 45, 48, 46,
    # İspanya
    140, 141, 143,
    # İtalya
    135, 136, 137,
    # Almanya
    78, 79, 81,
    # Fransa
    61, 62, 66,
    # Popüler Avrupa ve Kupalar
    88, 90, 89, 94, 96, 95, 144, 147, 179, 180,
    218, 219, 207, 209, 119, 120, 103, 104, 113,
    114, 106, 108, 197, 199, 345, 347, 235, 237,
    # Amerika & Asya
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

# --- İSTATİSTİK PARSER (GÜVENLİ VE ESNEK) ---
def istatistikleri_coz(raw_response):
    toplam_sut = 0
    isabetli_sut = 0
    korner = 0

    try:
        if not raw_response or "response" not in raw_response:
            return 0, 0, 0

        teams_data = raw_response["response"]
        for team in teams_data:
            stats = team.get("statistics", [])
            for item in stats:
                tip = str(item.get("type", "")).strip().lower()
                val = item.get("value")
                val_int = int(val) if (val is not None and str(val).isdigit()) else 0

                if "total shots" in tip:
                    toplam_sut += val_int
                elif "shots on goal" in tip:
                    isabetli_sut += val_int
                elif "corner" in tip:
                    korner += val_int

    except Exception as e:
        print("[PARSER HATA]:", e)

    return toplam_sut, isabetli_sut, korner

# --- CANLI MAÇ TARAMA MOTORU ---
def canli_tara():
    global bildirilen_maclar, son_sifirlama_gunu

    # Gece yarısı hafıza temizliği
    bugun = datetime.now(TR_TZ).day
    if bugun != son_sifirlama_gunu:
        bildirilen_maclar.clear()
        son_sifirlama_gunu = bugun
        print("[BİLGİ] Yeni gün basladi, bildirilen mac listesi sifirlandi.")

    try:
        res = requests.get(URL_LIVE, headers=HEADERS, timeout=15)
        kalan_kota = res.headers.get("x-ratelimit-requests-remaining", "Bilinmiyor")
        
        if res.status_code != 200:
            print(f"[API HATA] HTTP {res.status_code} - Kalan Kota: {kalan_kota}")
            return

        data = res.json()
        matches = data.get("response", [])
        
        if not matches:
            print(f"[BİLGİ] Su anda canli mac yok. Kalan Kota: {kalan_kota}")
            return

        taranan_adet = 0
        uygun_adet = 0

        for m in matches:
            try:
                fixture = m.get("fixture", {})
                f_id = fixture.get("id")
                status = fixture.get("status", {})
                dakika = status.get("elapsed")

                league = m.get("league", {})
                lig_id = league.get("id")
                lig_adi = league.get("name", "Bilinmeyen Lig")
                ulke = league.get("country", "")

                # 1. Filtre: Geçerli lig ve dakika kontrolü
                if lig_id not in IDDAA_LIGLERI or not dakika:
                    continue

                goals = m.get("goals", {})
                g_home = goals.get("home") if goals.get("home") is not None else 0
                g_away = goals.get("away") if goals.get("away") is not None else 0
                fark = abs(g_home - g_away)

                taranan_adet += 1

                # 2. Filtre: SADECE 60 - 75. DAKİKALAR ARASI & EN FAZLA 2 FARK
                if 60 <= dakika <= 75 and fark <= 2:
                    uygun_adet += 1
                    
                    if f_id in bildirilen_maclar:
                        continue

                    ev = m.get("teams", {}).get("home", {}).get("name", "Ev")
                    dep = m.get("teams", {}).get("away", {}).get("name", "Dep")

                    # İstatistik Sorgusu (Sadece şartı sağlayan seçilmiş maçlara)
                    stat_res = requests.get(f"{URL_STATS}?fixture={f_id}", headers=HEADERS, timeout=12)
                    if stat_res.status_code == 200:
                        sut, isabet, korner = istatistikleri_coz(stat_res.json())

                        print(f"[İNCELEME] {ev} {g_home}-{g_away} {dep} ({dakika}') | Sut: {sut} | Isabet: {isabet} | Korner: {korner}")

                        # 3. Filtre: Baskı Eşiği (Sut >= 11, İsabet >= 4, Korner >= 5)
                        if sut >= 11 and isabet >= 4 and korner >= 5:
                            mesaj = (
                                f"🔥 <b>CANLI GOL SİNYALİ (60-75 dk)!</b>\n\n"
                                f"🏆 <b>Lig:</b> {ulke} - {lig_adi}\n"
                                f"⚽ <b>Maç:</b> <b>{ev}</b> {g_home} - {g_away} <b>{dep}</b>\n"
                                f"⏱ <b>Dakika:</b> {dakika}'\n\n"
                                f"📊 <b>Canlı Baskı Verileri:</b>\n"
                                f"• Toplam Şut: <b>{sut}</b>\n"
                                f"• İsabetli Şut: <b>{isabet}</b>\n"
                                f"• Korner: <b>{korner}</b>\n\n"
                                f"💡 <b>Tavsiye:</b> Nesine/Misli canlısında '1 Gol Daha' oranını değerlendirin."
                            )
                            telegram_gonder(mesaj)
                            bildirilen_maclar.add(f_id)
                            print(f"[BİLDİRİM GÖNDERİLDİ] {ev} vs {dep}")

            except Exception as match_ex:
                print(f"[TEKİL MAÇ HATASI ID:{f_id}]:", match_ex)

        print(f"[TARAMA RAPORU] Canli Toplam: {len(matches)} | Bültenimizdeki: {taranan_adet} | 60-75 Dk Arasi: {uygun_adet} | Kalan Kota: {kalan_kota}")

    except Exception as loop_ex:
        print("[GENEL TARAMA HATASI]:", loop_ex)

# --- ANA ZAMANLAYICI DÖNGÜSÜ ---
def ana_dongu():
    telegram_gonder("🚀 <b>İddaa Canlı Analiz Botu Başlatıldı!</b>\n\n• Kriter: 60-75. Dakika\n• Fark: En fazla 2 gol\n• Baskı: Şut >= 11, İsabet >= 4, Korner >= 5\n• Bülten: Türkiye yasal bahis ligleri & tüm kupalar.")
    
    while True:
        try:
            simdi = datetime.now(TR_TZ)
            saat = simdi.hour
            hafta_sonu = simdi.weekday() >= 5

            calissin = False
            bekleme = 300

            if hafta_sonu:
                # Hafta sonu: 14:00 - 23:45 (6 dakikada bir)
                if 14 <= saat <= 23:
                    calissin = True
                    bekleme = 360
            else:
                # Hafta içi: 19:00 - 23:45 (4 dakikada bir)
                if 19 <= saat <= 23:
                    calissin = True
                    bekleme = 240

            if calissin:
                canli_tara()
                time.sleep(bekleme)
            else:
                # Çalışma saatleri dışındaysa 10 dakika bekle
                time.sleep(600)

        except Exception as e:
            print("[DÖNGÜ KRİTİK HATA]:", e)
            time.sleep(30)

if __name__ == "__main__":
    t = threading.Thread(target=keep_alive, daemon=True)
    t.start()
    ana_dongu()
