import os
import sys
import time
import threading
import requests
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

print(">>> [SISTEM] Kendi Kendini Uyanik Tutan Zirve Surum Devrede! <<<")

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

GOLLU_LIGLER = [
    "eredivisie", "eerste divisie", "bundesliga", "eliteserien", 
    "allsvenskan", "super league", "pro league", "premier league", 
    "championship", "bundesliga 2", "super lig"
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
            print(f"[TELEGRAM HATA] Kod: {res.status_code}")
    except Exception as e:
        print(f"[TELEGRAM AG HATA]: {e}")

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
        print("[HAFIZA] Yeni gun, bildirim havuzu temizlendi.")

    try:
        res = requests.get(API_LIVE_URL, headers=API_HEADERS, timeout=15)
        kalan_kota = res.headers.get("x-ratelimit-requests-remaining", "Bilinmiyor")

        if res.status_code != 200:
            return

        data = res.json()
        maclar = data.get("response", [])
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

                if any(cl in tam_lig for cl in COPE_LIGLER):
                    continue

                goals = m.get("goals", {})
                ev_gol = goals.get("home") if goals.get("home") is not None else 0
                dep_gol = goals.get("away") if goals.get("away") is not None else 0
                fark = abs(ev_gol - dep_gol)

                if 60 <= dakika <= 75 and fark <= 2:
                    if mac_id in bildirilen_maclar:
                        continue

                    gollu_lig_mi = any(gl in tam_lig for gl in GOLLU_LIGLER)
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

                        if toplam_faul >= 24:
                            continue

                        kriter = 0
                        if toplam_sut >= 10: kriter += 1
                        if toplam_isabet >= 4: kriter += 1
                        if toplam_korner >= 5: kriter += 1

                        if kriter >= 2:
                            sut_hizi = toplam_sut / dakika
                            isabet_orani = (toplam_isabet / toplam_sut) if toplam_sut > 0 else 0

                            if sut_hizi < 0.16 or isabet_orani < 0.28:
                                continue

                            ev_tehlike = (ev_s["isabet"] * 2.5) + ((ev_s["sut"] - ev_s["isabet"]) * 0.8) + (ev_s["korner"] * 1.2) + (dep_s["kurtaris"] * 1.5)
                            dep_tehlike = (dep_s["isabet"] * 2.5) + ((dep_s["sut"] - dep_s["isabet"]) * 0.8) + (dep_s["korner"] * 1.2) + (ev_s["kurtaris"] * 1.5)

                            ev_tehlike *= 1.15
                            if kirmizi_dep: ev_tehlike *= 1.25
                            if kirmizi_ev: dep_tehlike *= 1.20

                            toplam_tehlike = ev_tehlike + dep_tehlike

                            if gollu_lig_mi:
                                toplam_tehlike *= 1.20

                            toplam_tehlike = round(toplam_tehlike, 1)

                            if kisir_lig_mi and toplam_tehlike < 25.0:
                                continue

                            tercih = "⚽ <b>1 Gol Daha Olur (Sıradaki Gol)</b>"
                            piyasa_gerekcesi = "Sürekli hücum baskısı var, süre daraldığı için oran değerli."
                            kasa_tavsiye = "Kasanın %2'si"

                            if (ev_gol == 0 and dep_gol >= 1 and ev_tehlike >= 13.0) or \
                               (dep_gol == 0 and ev_gol >= 1 and dep_tehlike >= 12.0):
                                tercih = "🔥 <b>Karşılıklı Gol Var (KG VAR)</b> veya <b>Sıradaki Gol</b>"
                                piyasa_gerekcesi = "Geride olan takım tek kale oynuyor, beraberlik golü kapıda."
                                kasa_tavsiye = "Kasanın %3'ü"

                            elif ev_gol < dep_gol and ev_tehlike >= 16.0 and fark == 1:
                                tercih = "🛡 <b>1X Çifte Şans</b> veya <b>Ev Sahibi 1 Gol Daha</b>"
                                piyasa_gerekcesi = "Ev sahibi sahayı yıktı, beraberliği koparacak güçte."
                                kasa_tavsiye = "Kasanın %3.5'i"

                            elif toplam_tehlike >= 25.0:
                                tercih = "💣 <b>A+ SİNYAL: 1 Gol Daha Olur (Kasa Maçı)</b>"
                                piyasa_gerekcesi = "Savunmalar çöktü, kaleciler kritik kurt
