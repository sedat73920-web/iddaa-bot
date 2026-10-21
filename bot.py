import os
import sys
import time
import threading
import requests
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

# Log tamponunu kapat, Render ekranına anında düşsün
os.environ["PYTHONUNBUFFERED"] = "1"

print(">>> [SISTEM] Hafta Sonu 17:00 & Nihai Kota Kilidi Devrede! <<<", flush=True)

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
bildirilen_maclar = set()
aktif_gun = datetime.now(TURKIYE_SAATI).day

# KISIR, KALİTESİZ VEYA BİTİRİCİLİĞİ SIFIR LİGLER
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
        res = requests.post(url, json=payload, timeout=12)
        if res.status_code != 200:
            print(f"[TELEGRAM HATA] Kod: {res.status_code}", flush=True)
    except Exception as e:
        print(f"[TELEGRAM AG HATA]: {e}", flush=True)

# ==========================================
# 3. İSTATİSTİK AYRIŞTIRICI
# ==========================================
def derin_istatistik_coz(gelen_veri):
    ev_stat = {"sut": 0, "isabet": 0, "korner": 0, "kurtaris": 0, "faul": 0}
    dep_stat = {"sut": 0, "isabet": 0, "korner": 0, "kurtaris": 0, "faul": 0}

    if not gelen_veri or "response" not in gelen_veri:
        return ev_stat, dep_stat

    takimlar = gelen_veri.get("response", [])
    if not isinstance(takimlar, list) or len(takimlar) < 2:
        return ev_stat, dep_stat

    def parse_stats(stat_list):
        s, i, k, kurt, f = 0, 0, 0, 0, 0
        for item in stat_list:
            tip = str(item.get("type", "")).strip().lower()
            val = item.get("value")
            sayi = int(str(val).strip()) if (val is not None and str(val).strip().isdigit()) else 0
            if "total shots" in tip: s = sayi
            elif "shots on goal" in tip: i = sayi
            elif "corner" in tip: k = sayi
            elif "goalkeeper saves" in tip: kurt = sayi
            elif "fouls" in tip: f = sayi
        return {"sut": s, "isabet": i, "korner": k, "kurtaris": kurt, "faul": f}

    ev_stat = parse_stats(takimlar[0].get("statistics", []))
    dep_stat = parse_stats(takimlar[1].get("statistics", []))

    return ev_stat, dep_stat

# ==========================================
# 4. KOTA KORUMALI CANLI TARAMA MOTORU
# ==========================================
def canli_tara():
    global bildirilen_maclar, aktif_gun

    bugun = datetime.now(TURKIYE_SAATI).day
    if bugun != aktif_gun:
        bildirilen_maclar.clear()
        aktif_gun = bugun
        print("[HAFIZA] Yeni gun, bildirim havuzu temizlendi.", flush=True)

    try:
        res = requests.get(API_LIVE_URL, headers=API_HEADERS, timeout=15)
        kalan_kota = res.headers.get("x-ratelimit-requests-remaining", "Bilinmiyor")

        if res.status_code != 200:
            print(f"[API HATA] HTTP Kod: {res.status_code}", flush=True)
            return

        data = res.json()
        maclar = data.get("response", [])
        print(f"[TARAMA BASLADI] Canli: {len(maclar)} | Kalan Kota: {kalan_kota}", flush=True)

        if not maclar:
            return

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

                # Lig filtreleri (Gereksiz istatistik isteği atmadan elenir)
                if any(cl in tam_lig for cl in COPE_LIGLER):
                    continue

                if any(ku in ulke_kucuk for ku in KISIR_ULKELER):
                    continue

                goals = m.get("goals", {})
                ev_gol = goals.get("home") if goals.get("home") is not None else 0
                dep_gol = goals.get("away") if goals.get("away") is not None else 0
                fark = abs(ev_gol - dep_gol)

                if 60 <= dakika <= 75 and fark <= 2:
                    if mac_id in bildirilen_maclar:
                        continue

                    gollu_lig_mi = False
                    if "netherlands" in ulke_kucuk or "germany" in ulke_kucuk or "norway" in ulke_kucuk or "sweden" in ulke_kucuk:
                        gollu_lig_mi = True
                    elif "england" in ulke_kucuk and ("premier league" in tam_lig or "championship" in tam_lig):
                        gollu_lig_mi = True

                    kisir_lig_mi = any(kl in tam_lig for kl in KISIR_LIGLER)

                    kirmizi_ev, kirmizi_dep = False, False
                    son_gol_dakikasi = 0
                    for ev in m.get("events", []):
                        ev_tip = ev.get("type", "").lower()
                        ev_detay = ev.get("detail", "").lower()
                        if ev_tip == "card" and ev_detay == "red card":
                            takim_id = ev.get("team", {}).get("id")
                            if takim_id == m.get("teams", {}).get("home", {}).get("id"):
                                kirmizi_ev = True
                            else:
                                kirmizi_dep = True
                        elif ev_tip == "goal":
                            g_dak = ev.get("time", {}).get("elapsed", 0)
                            if g_dak > son_gol_dakikasi:
                                son_gol_dakikasi = g_dak

                    if dakika - son_gol_dakikasi < 4:
                        continue

                    stat_res = requests.get(f"{API_STATS_URL}?fixture={mac_id}", headers=API_HEADERS, timeout=12)
                    if stat_res.status_code == 200:
                        ev_s, dep_s = derin_istatistik_coz(stat_res.json())

                        toplam_sut = ev_s["sut"] + dep_s["sut"]
                        toplam_isabet = ev_s["isabet"] + dep_s["isabet"]
                        toplam_korner = ev_s["korner"] + dep_s["korner"]
                        toplam_faul = ev_s["faul"] + dep_s["faul"]

                        # DENGELİ EŞİKLER: En az 4 korner ve en az 5 isabet
                        if toplam_korner < 4 or toplam_isabet < 5:
                            continue

                        if toplam_faul >= 26:
                            continue

                        sut_hizi = toplam_sut / dakika
                        isabet_orani = (toplam_isabet / toplam_sut) if toplam_sut > 0 else 0

                        if sut_hizi < 0.16 or isabet_orani < 0.28:
                            continue

                        ev_tehlike = (ev_s["isabet"] * 2.3) + ((ev_s["sut"] - ev_s["isabet"]) * 0.7) + (ev_s["korner"] * 1.1) + (dep_s["kurtaris"] * 1.5)
                        dep_tehlike = (dep_s["isabet"] * 2.3) + ((dep_s["sut"] - dep_s["isabet"]) * 0.7) + (dep_s["korner"] * 1.1) + (ev_s["kurtaris"] * 1.5)

                        ev_tehlike *= 1.12
                        if kirmizi_dep: ev_tehlike *= 1.25
                        if kirmizi_ev: dep_tehlike *= 1.20

                        toplam_tehlike = ev_tehlike + dep_tehlike

                        if gollu_lig_mi:
                            toplam_tehlike *= 1.15

                        toplam_tehlike = round(toplam_tehlike, 1)

                        if toplam_tehlike < 25.0:
                            continue

                        tercih = "⚽ <b>1 Gol Daha Olur (Sıradaki Gol)</b>"
                        piyasa_gerekcesi = "Sürekli kale baskisi var, savunma direnci kirilmak uzere."
                        kasa_tavsiye = "Kasanin %2'si"

                        if (ev_gol == 0 and dep_gol >= 1 and ev_tehlike >= 14.0) or \
                           (dep_gol == 0 and ev_gol >= 1 and dep_tehlike >= 13.0):
                            tercih = "🔥 <b>KG VAR</b> veya <b>Siradaki Gol</b>"
                            piyasa_gerekcesi = "Gerideki takim kaleyi abluka altina aldi."
                            kasa_tavsiye = "Kasanin %3'u"

                        elif ev_gol < dep_gol and ev_tehlike >= 16.5 and fark == 1:
                            tercih = "🛡 <b>1X Cifte Sans</b> veya <b>Ev Sahibi Gol</b>"
                            piyasa_gerekcesi = "Ev sahibi sahada ezici ustunluk kurdu."
                            kasa_tavsiye = "Kasanin %3.5'i"

                        elif toplam_tehlike >= 32.0 and toplam_korner >= 6 and toplam_isabet >= 7:
                            tercih = "💣 <b>A+ ZIRVE SINYAL: 1 Gol Daha Olur</b>"
                            piyasa_gerekcesi = "Savunmalar coktu, kaleciler kritik kurtarislarla direniyor."
                            kasa_tavsiye = "Kasanin %4'u"

                        ev_ad = m.get("teams", {}).get("home", {}).get("name", "Ev")
                        dep_ad = m.get("teams", {}).get("away", {}).get("name", "Dep")

                        kart_durumu = ""
                        if kirmizi_ev or kirmizi_dep:
                            kart_durumu = f"\n🟥 <b>Kirmizi Kart:</b> {'Ev 10 Kisi' if kirmizi_ev else 'Dep 10 Kisi'}"

                        lig_etiketi = "\n⚡ <b>Gollu Lig Bonusu:</b> (+%15 Baski)" if gollu_lig_mi else ""

                        mesaj = (
                            f"👑 <b>GOL AVCISI ANALİZİ</b>\n\n"
                            f"🏆 <b>Lig:</b> {ulke} - {lig_ad} {lig_etiketi}\n"
                            f"⚽ <b>Mac:</b> <b>{ev_ad}</b> {ev_gol} - {dep_gol} <b>{dep_ad}</b>\n"
                            f"⏱ <b>Dakika:</b> {dakika}' {kart_durumu}\n\n"
                            f"📊 <b>Baski Verileri:</b>\n"
                            f"• Ev: {ev_s['sut']} Sut ({ev_s['isabet']} Isabet) / {ev_s['korner']} Korner\n"
                            f"• Dep: {dep_s['sut']} Sut ({dep_s['isabet']} Isabet) / {dep_s['korner']} Korner\n"
                            f"🧤 <b>Kurtarislar:</b> Ev: {ev_s['kurtaris']} | Dep: {dep_s['kurtaris']}\n"
                            f"🎯 <b>Tehlike Indeksi:</b> <b>{toplam_tehlike} Puan</b>\n"
                            f"📈 <b>Isabet Orani:</b> %{int(isabet_orani*100)}\n\n"
                            f"💡 <b>ONERILEN TERCIH:</b>\n{tercih}\n"
                            f"📌 <i>Gerekce: {piyasa_gerekcesi}</i>\n\n"
                            f"💰 <b>Kelly Kasa Girisi:</b> {kasa_tavsiye}"
                        )

                        telegram_ilet(mesaj)
                        bildirilen_maclar.add(mac_id)
                        print(f"[BILDIRILDI] {ev_ad} vs {dep_ad} | Tehlike: {toplam_tehlike}", flush=True)

            except Exception as tekil_e:
                print(f"[MAC HATA]: {tekil_e}", flush=True)

        print(f"[TARAMA BITTI] Kalan Kota: {kalan_kota}", flush=True)

    except Exception as genel_e:
        print(f"[TARAMA GENEL HATA]: {genel_e}", flush=True)

# ==========================================
# 5. DÖNGÜ & HAFTA SONU TASARRUF MOTORU
# ==========================================
def analiz_dongusu():
    time.sleep(3)
    telegram_ilet(
        "🚀 <b>GOL AVCISI: Son Ayarlar Kilitlendi!</b>\n\n"
        "• Hafta sonu: 17:00 - 23:55 (16:00 maçlarının 60. dakikasıyla başlar).\n"
        "• Hafta içi: 18:30 - 23:55.\n"
        "• Altın denge filtreleri devrede, kota koruması tam."
    )

    while True:
        try:
            anlik = datetime.now(TURKIYE_SAATI)
            saat = anlik.hour
            dakika = anlik.minute
            hafta_sonu = anlik.weekday() >= 5  # Cumartesi ve Pazar

            calissin = False
            bekleme = 300  # Standart 5 dakika

            if hafta_sonu:
                # Cumartesi ve Pazar: 17:00 - 23:55 (~84 istek ile maksimum kota tasarrufu)
                if (17 <= saat < 23) or (saat == 23 and dakika <= 55):
                    calissin = True
                    bekleme = 300
            else:
                # Hafta içi: 18:30 - 23:55
                if (18 <= saat < 23 and (saat > 18 or dakika >= 30)) or (saat == 23 and dakika <= 55):
                    calissin = True
                    bekleme = 300

            if calissin:
                canli_tara()
                time.sleep(bekleme)
            else:
                print(f"[BEKLEME] Mac saatleri disi ({saat:02d}:{dakika:02d}). 10 dk uyku...", flush=True)
                time.sleep(600)

        except Exception as e:
            print(f"[DÖNGÜ HATA]: {e}", flush=True)
            time.sleep(30)

# ==========================================
# 6. UYKU SAVAR (5 DAKİKADA BİR SELF-PING)
# ==========================================
def uyku_savar_dongusu():
    time.sleep(15)
    sunucu_url = "https://iddaa-bot-05vw.onrender.com"
    while True:
        try:
            r = requests.get(sunucu_url, timeout=10)
            print(f"[NOBETCI] 5 Dk Ping basarili. Kod: {r.status_code}", flush=True)
        except Exception as e:
            print(f"[NOBETCI UYARI]: Ping atilamadi ({e})", flush=True)
        time.sleep(300)

# ==========================================
# 7. RENDER WEBSERVER
# ==========================================
class RenderHealthServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot Aktif!")

    def log_message(self, format, *args):
        return

def web_sunucu_baslat():
    try:
        port = int(os.environ.get("PORT", 8080))
        sunucu = HTTPServer(("0.0.0.0", port), RenderHealthServer)
        print(f"[WEB] Port {port} kilitlendi.", flush=True)
        sunucu.serve_forever()
    except Exception as e:
        print(f"[WEB HATA]: {e}", flush=True)

# Thread'ler tek parça halinde başlatılıyor
threading.Thread(target=web_sunucu_baslat, daemon=True).start()
threading.Thread(target=uyku_savar_dongusu, daemon=True).start()

analiz_dongusu()
