import os
import sys
import time
import threading
import requests
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

os.environ["PYTHONUNBUFFERED"] = "1"

print(">>> [SISTEM] Cift Kademeli Gol Avcisi Baslatildi <<<", flush=True)

# ==========================================
# 1. YAPILANDIRMA VE KİMLİK BİLGİLERİ
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
bildirilen_maclar = set()
aktif_gun = datetime.now(TURKIYE_SAATI).day

# Filtrelenecek ligler ve ülkeler
KISIR_ULKELER = [
    "egypt", "morocco", "algeria", "tunisia", "iran", "greece", 
    "argentina", "finland", "iceland", "ireland", "estonia", "latvia", "lithuania"
]
KISIR_LIGLER = [
    "serie c", "primera b", "segunda b", "super league 2", 
    "botola", "girabola", "national", "ligue 2"
]
COPE_LIGLER = ["u19", "u20", "u21", "women", "kadınlar", "amateur", "reserve"]

# ==========================================
# 2. TELEGRAM MESAJ SERVİSİ
# ==========================================
def telegram_ilet(mesaj):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mesaj,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        requests.post(url, json=payload, timeout=12)
    except Exception as e:
        print(f"[TELEGRAM HATA]: {e}", flush=True)

# ==========================================
# 3. İSTATİSTİK AYRIŞTIRICI
# ==========================================
def derin_istatistik_coz(gelen_veri):
    ev_stat = {"sut": 0, "isabet": 0, "korner": 0, "kurtaris": 0}
    dep_stat = {"sut": 0, "isabet": 0, "korner": 0, "kurtaris": 0}

    if not gelen_veri or "response" not in gelen_veri:
        return ev_stat, dep_stat

    takimlar = gelen_veri.get("response", [])
    if not isinstance(takimlar, list) or len(takimlar) < 2:
        return ev_stat, dep_stat

    def parse_stats(stat_list):
        s, i, k, kurt = 0, 0, 0, 0
        for item in stat_list:
            tip = str(item.get("type", "")).strip().lower()
            val = item.get("value")
            sayi = int(str(val).strip()) if (val is not None and str(val).strip().isdigit()) else 0
            if "total shots" in tip: s = sayi
            elif "shots on goal" in tip: i = sayi
            elif "corner" in tip: k = sayi
            elif "goalkeeper saves" in tip: kurt = sayi
        return {"sut": s, "isabet": i, "korner": k, "kurtaris": kurt}

    ev_stat = parse_stats(takimlar[0].get("statistics", []))
    dep_stat = parse_stats(takimlar[1].get("statistics", []))
    return ev_stat, dep_stat

# ==========================================
# 4. ÇİFT KADEMELİ CANLI ANALİZ MOTORU
# ==========================================
def canli_tara():
    global bildirilen_maclar, aktif_gun

    bugun = datetime.now(TURKIYE_SAATI).day
    if bugun != aktif_gun:
        bildirilen_maclar.clear()
        aktif_gun = bugun
        print("[HAFIZA] Yeni gün başladı, sinyal hafızası sıfırlandı.", flush=True)

    try:
        res = requests.get(API_LIVE_URL, headers=API_HEADERS, timeout=15)
        kalan_kota = res.headers.get("x-ratelimit-requests-remaining", "Bilinmiyor")

        if res.status_code != 200:
            return

        data = res.json()
        maclar = data.get("response", [])
        print(f"[TARAMA] Canlı: {len(maclar)} Maç | Kalan Kota: {kalan_kota}", flush=True)

        for m in maclar:
            try:
                fixture = m.get("fixture", {})
                mac_id = fixture.get("id")
                status = fixture.get("status", {})
                dakika = status.get("elapsed")

                if not dakika:
                    continue

                league = m.get("league", {})
                lig_ad = league.get("name", "Lig")
                ulke = league.get("country", "")
                tam_lig = f"{lig_ad} {ulke}".lower()
                ulke_kucuk = ulke.lower()

                # Çöp ve kısır ligleri doğrudan ele
                if any(cl in tam_lig for cl in COPE_LIGLER) or any(ku in ulke_kucuk for ku in KISIR_ULKELER):
                    continue

                goals = m.get("goals", {})
                ev_gol = goals.get("home") if goals.get("home") is not None else 0
                dep_gol = goals.get("away") if goals.get("away") is not None else 0
                toplam_gol = ev_gol + dep_gol
                fark = abs(ev_gol - dep_gol)

                # 1. Aşama Kriteri: İkinci Yarı (60-76. dk, Skor Farkı <= 2)
                ikinci_yari_uygun = (60 <= dakika <= 76 and fark <= 2 and f"{mac_id}_IY2" not in bildirilen_maclar)

                # 2. Aşama Kriteri: İlk Yarı (25-38. dk, Skor Farkı <= 2, Toplam Gol <= 3)
                ilk_yari_uygun = (25 <= dakika <= 38 and fark <= 2 and toplam_gol <= 3 and f"{mac_id}_IY1" not in bildirilen_maclar)

                if not (ikinci_yari_uygun or ilk_yari_uygun):
                    continue

                # Eşiğe giren maçın istatistiğini çek
                stat_res = requests.get(f"{API_STATS_URL}?fixture={mac_id}", headers=API_HEADERS, timeout=12)
                if stat_res.status_code != 200:
                    continue

                ev_s, dep_s = derin_istatistik_coz(stat_res.json())
                toplam_sut = ev_s["sut"] + dep_s["sut"]
                toplam_isabet = ev_s["isabet"] + dep_s["isabet"]
                toplam_korner = ev_s["korner"] + dep_s["korner"]

                ev_ad = m.get("teams", {}).get("home", {}).get("name", "Ev")
                dep_ad = m.get("teams", {}).get("away", {}).get("name", "Dep")

                # ========================================================
                # SENARYO 1: İKİNCİ YARI GOL AVCISI (60-76')
                # ========================================================
                if ikinci_yari_uygun:
                    if toplam_korner >= 4 and toplam_isabet >= 5:
                        isabet_orani = (toplam_isabet / toplam_sut) if toplam_sut > 0 else 0
                        if isabet_orani >= 0.28:
                            ev_tehlike = (ev_s["isabet"] * 2.3) + ((ev_s["sut"] - ev_s["isabet"]) * 0.7) + (ev_s["korner"] * 1.1) + (dep_s["kurtaris"] * 1.5)
                            dep_tehlike = (dep_s["isabet"] * 2.3) + ((dep_s["sut"] - dep_s["isabet"]) * 0.7) + (dep_s["korner"] * 1.1) + (ev_s["kurtaris"] * 1.5)
                            toplam_tehlike = round((ev_tehlike * 1.12) + dep_tehlike, 1)

                            if toplam_tehlike >= 25.0:
                                bildiri = (
                                    f"🔥 <b>İKİNCİ YARI GOL AVCISI</b>\n\n"
                                    f"🏆 <b>Lig:</b> {ulke} - {lig_ad}\n"
                                    f"⚽ <b>Maç:</b> {ev_ad} <b>{ev_gol} - {dep_gol}</b> {dep_ad}\n"
                                    f"⏱ <b>Dakika:</b> {dakika}'\n\n"
                                    f"📊 <b>Baskı Verisi:</b>\n"
                                    f"• Toplam Şut: {toplam_sut} | İsabet: {toplam_isabet} | Korner: {toplam_korner}\n"
                                    f"🎯 <b>Tehlike İndeksi:</b> <b>{toplam_tehlike} Puan</b>\n\n"
                                    f"💡 <b>TERCİH:</b> ⚽ <b>1 Gol Daha Olur (Sıradaki Gol)</b>\n"
                                    f"💰 <b>Kasa Girişi:</b> Kasanın %2.5'i"
                                )
                                telegram_ilet(bildiri)
                                bildirilen_maclar.add(f"{mac_id}_IY2")
                                print(f"[BİLDİRİLDİ - İY2] {ev_ad} vs {dep_ad}", flush=True)

                # ========================================================
                # SENARYO 2: İLK YARI BASKI ALARMI (25-38')
                # ========================================================
                elif ilk_yari_uygun:
                    if toplam_sut >= 5 and toplam_isabet >= 2 and toplam_korner >= 2:
                        hedef_ust = toplam_gol + 0.5
                        bildiri = (
                            f"⚡ <b>İLK YARI BASKI ALARMI</b>\n\n"
                            f"🏆 <b>Lig:</b> {ulke} - {lig_ad}\n"
                            f"⚽ <b>Maç:</b> {ev_ad} <b>{ev_gol} - {dep_gol}</b> {dep_ad}\n"
                            f"⏱ <b>Dakika:</b> {dakika}'\n\n"
                            f"📊 <b>İlk Yarı Baskısı:</b>\n"
                            f"• Şut: {toplam_sut} ({toplam_isabet} İsabet) | Korner: {toplam_korner}\n"
                            f"🧤 <b>Kurtarışlar:</b> Ev: {ev_s['kurtaris']} | Dep: {dep_s['kurtaris']}\n\n"
                            f"💡 <b>TERCİH:</b> 💣 <b>İlk Yarı {hedef_ust} ÜST</b>\n"
                            f"⚠️ <i>KURAL: Oran 1.60 altındaysa kesinlikle girme!</i>\n"
                            f"💰 <b>Kasa Girişi:</b> Kasanın %2'si"
                        )
                        telegram_ilet(bildiri)
                        bildirilen_maclar.add(f"{mac_id}_IY1")
                        print(f"[BİLDİRİLDİ - İY1] {ev_ad} vs {dep_ad}", flush=True)

            except Exception as e:
                continue

    except Exception as genel_e:
        print(f"[TARAMA HATA]: {genel_e}", flush=True)

# ==========================================
# 5. ÇALIŞMA SAATLERİ VE PERİYOT
# ==========================================
def analiz_dongusu():
    time.sleep(3)
    telegram_ilet("👑 <b>Çift Kademeli Gol Avcısı Başarıyla Devrede!</b>\n\n• İlk Yarı Baskısı (25-38' | Fark <= 2) devrede.\n• İkinci Yarı Avcısı (60-76' | Fark <= 2) devrede.\n• Hafta içi 18:30, Hafta sonu 17:00 mesaisi aktif.")

    while True:
        try:
            anlik = datetime.now(TURKIYE_SAATI)
            saat = anlik.hour
            dakika = anlik.minute
            hafta_sonu = anlik.weekday() >= 5

            calissin = False
            bekleme = 300  # 5 dakika

            if hafta_sonu:
                if (17 <= saat < 23) or (saat == 23 and dakika <= 55):
                    calissin = True
                    bekleme = 300
            else:
                if (18 <= saat < 23 and (saat > 18 or dakika >= 30)) or (saat == 23 and dakika <= 55):
                    calissin = True
                    bekleme = 300

            if calissin:
                canli_tara()
                time.sleep(bekleme)
            else:
                time.sleep(600)  # Mesai dışı 10 dk bekleme

        except Exception as e:
            time.sleep(30)

# ==========================================
# 6. UYKU SAVAR (SELF-PING) & RENDER PORT DİNLEYİCİ
# ==========================================
def uyku_savar_dongusu():
    time.sleep(15)
    sunucu_url = "https://iddaa-bot-05vw.onrender.com"
    while True:
        try:
            requests.get(sunucu_url, timeout=10)
        except Exception:
            pass
        time.sleep(300)

class RenderHealthServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot Aktif Calisiyor!")
    def log_message(self, format, *args):
        return

def web_sunucu_baslat():
    port = int(os.environ.get("PORT", 8080))
    sunucu = HTTPServer(("0.0.0.0", port), RenderHealthServer)
    sunucu.serve_forever()

threading.Thread(target=web_sunucu_baslat, daemon=True).start()
threading.Thread(target=uyku_savar_dongusu, daemon=True).start()

analiz_dongusu()
