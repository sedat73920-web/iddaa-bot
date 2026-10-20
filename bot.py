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

# ==========================================
# 2. NESİNE & İDDAA CANLI BÜLTENİ LİGLERİ
# ==========================================
IDDAA_LIGLERI = {
    # --- UEFA Turnuvaları & Uluslararası ---
    848,  # UEFA Konferans Ligi
    2,    # UEFA Şampiyonlar Ligi
    3,    # UEFA Avrupa Ligi
    531,  # UEFA Süper Kupa
    5,    # UEFA Uluslar Ligi
    4,    # Avrupa Şampiyonası (EURO)
    1,    # FIFA Dünya Kupası
    6,    # UEFA Kadınlar Şampiyonlar Ligi
    13,   # CONMEBOL Libertadores
    11,   # CONMEBOL Sudamericana
    16,   # Asya Şampiyonlar Ligi (AFC)

    # --- Türkiye ---
    203,  # Trendyol Süper Lig
    204,  # Trendyol 1. Lig
    552,  # Ziraat Türkiye Kupası
    555,  # TFF 2. Lig

    # --- İngiltere ---
    39,   # Premier League
    40,   # Championship
    41,   # League One
    42,   # League Two
    45,   # FA Cup
    48,   # EFL Cup (Carabao Cup)
    46,   # EFL Trophy

    # --- İspanya ---
    140,  # La Liga
    141,  # La Liga 2
    143,  # Copa del Rey

    # --- İtalya ---
    135,  # Serie A
    136,  # Serie B
    137,  # Coppa Italia

    # --- Almanya ---
    78,   # Bundesliga
    79,   # 2. Bundesliga
    81,   # DFB Pokal

    # --- Fransa ---
    61,   # Ligue 1
    62,   # Ligue 2
    66,   # Coupe de France

    # --- Popüler Avrupa Ligleri & Yerel Kupalar ---
    88,   # Hollanda Eredivisie
    90,   # Hollanda KNVB Beker
    89,   # Hollanda Eerste Divisie
    94,   # Portekiz Primeira Liga
    96,   # Portekiz Kupası
    95,   # Portekiz Segunda Liga
    144,  # Belçika Pro League
    147,  # Belçika Kupası
    179,  # İskoçya Premiership
    180,  # İskoçya Kupası
    218,  # Avusturya Bundesliga
    219,  # Avusturya Kupası
    207,  # İsviçre Super League
    209,  # İsviçre Kupası
    119,  # Danimarka Superliga
    120,  # Danimarka Kupası
    103,  # Norveç Eliteserien
    104,  # Norveç Kupası
    113,  # İsveç Allsvenskan
    114,  # İsveç Kupası
    106,  # Polonya Ekstraklasa
    108,  # Polonya Kupası
    197,  # Yunanistan Süper Lig
    199,  # Yunanistan Kupası
    345,  # Çekya 1. Liga
    347,  # Çekya Kupası
    235,  # Rusya Premier Ligi
    237,  # Rusya Kupası

    # --- Amerika / Gece Kuşağı ---
    253,  # ABD MLS
    257,  # US Open Cup
    71,   # Brezilya Serie A
    72,   # Brezilya Serie B
    73,   # Brezilya Kupası
    128,  # Arjantin Liga Profesional
    130,  # Arjantin Copa de la Liga
    262,  # Meksika Liga MX
    239,  # Kolombiya Primera A

    # --- Asya / Gündüz Kuşağı ---
    98,   # Japonya J1 League
    102,  # Japonya İmparatorluk Kupası
    292,  # Güney Kore K League 1
    294   # Güney Kore FA Cup
}

# ==========================================
# 3. ZAMAN, BELLEK VE YEREL DEĞİŞKENLER
# ==========================================
TURKIYE_SAATI = timezone(timedelta(hours=3))
bildirilen_maclar_kumesi = set()
aktif_sifirlama_gunu = datetime.now(TURKIYE_SAATI).day

# ==========================================
# 4. RENDER BULUT UYKU ÖNLEYİCİ WEBSERVER
# ==========================================
class RenderHealthServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Iddaa Analiz Botu Calisiyor.")

    def log_message(self, format, *args):
        return

def arka_plan_web_sunucusu_baslat():
    try:
        atanan_port = int(os.environ.get("PORT", 8080))
        sunucu = HTTPServer(("0.0.0.0", atanan_port), RenderHealthServer)
        print(f"[BILGI] Uyku onleyici web sunucu {atanan_port} portunda devrede.")
        sunucu.serve_forever()
    except Exception as sunucu_hatasi:
        print(f"[UYARI] Web sunucu baslatilamadi: {sunucu_hatasi}")

# ==========================================
# 5. TELEGRAM HABERLEŞME SERVİSİ
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
        if yanit.status_code != 200:
            print(f"[TELEGRAM YANIT HATASI] Kod: {yanit.status_code} - Aciklama: {yanit.text}")
        else:
            print("[TELEGRAM] Bildirim basariyla iletildi.")
    except Exception as ag_hatasi:
        print(f"[TELEGRAM AG HATASI] Mesaj gonderilemedi: {ag_hatasi}")

# ==========================================
# 6. İSTATİSTİK AYRIŞTIRICI FONKSİYON
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
# 7. CANLI MAÇ TARAMA MOTORU
# ==========================================
def canli_bulteni_tara():
    global bildirilen_maclar_kumesi, aktif_sifirlama_gunu

    su_anki_gun = datetime.now(TURKIYE_SAATI).day
    if su_anki_gun != aktif_sifirlama_gunu:
        bildirilen_maclar_kumesi.clear()
        aktif_sifirlama_gunu = su_anki_gun
        print("[HAFIZA] Yeni gun basladi. Bildirilen maclar listesi sifirlandi.")

    try:
        canli_istek = requests.get(API_LIVE_URL, headers=API_HEADERS, timeout=15)
        kalan_api_kotasi = canli_istek.headers.get("x-ratelimit-requests-remaining", "Bilinmiyor")

        if canli_istek.status_code != 200:
            print(f"[API HATASI] Kod: {canli_istek.status_code} | Kalan Kota: {kalan_api_kotasi}")
            return

        ana_veri = canli_istek.json()
        canli_mac_listesi = ana_veri.get("response", [])

        if not canli_mac_listesi:
            print(f"[TARAMA] Su anda canli mac bulunmuyor. Kota: {kalan_api_kotasi}")
            return

        bultene_uyan_mac_sayisi = 0
        dakikasi_uyan_mac_sayisi = 0

        for mac in canli_mac_listesi:
            try:
                fikstur_bilgisi = mac.get("fixture", {})
                mac_id = fikstur_bilgisi.get("id")
                durum_bilgisi = fikstur_bilgisi.get("status", {})
                dakika = durum_bilgisi.get("elapsed")

                lig_bilgisi = mac.get("league", {})
                lig_id = lig_bilgisi.get("id")
                lig_adi = lig_bilgisi.get("name", "Bilinmeyen Turnuva")
                ulke_adi = lig_bilgisi.get("country", "")

                if not lig_id or lig_id not in IDDAA_LIGLERI:
                    continue

                if not dakika:
                    continue

                bultene_uyan_mac_sayisi += 1

                skor_bilgisi = mac.get("goals", {})
                ev_gol = skor_bilgisi.get("home")
                dep_gol = skor_bilgisi.get("away")

                if ev_gol is None:
                    ev_gol = 0
                if dep_gol is None:
                    dep_gol = 0

                skor_farki = abs(ev_gol - dep_gol)

                # 60 - 75. DAKİKALAR ARASI VE EN FAZLA 2 FARK
                if 60 <= dakika <= 75 and skor_farki <= 2:
                    dakikasi_uyan_mac_sayisi += 1

                    if mac_id in bildirilen_maclar_kumesi:
                        continue

                    ev_takim = mac.get("teams", {}).get("home", {}).get("name", "Ev Sahibi")
                    dep_takim = mac.get("teams", {}).get("away", {}).get("name", "Deplasman")

                    istatistik_istek_adresi = f"{API_STATS_URL}?fixture={mac_id}"
                    stat_istek = requests.get(istatistik_istek_adresi, headers=API_HEADERS, timeout=12)

                    if stat_istek.status_code == 200:
                        sut, isabet, korner = istatistik_verilerini_cozumle(stat_istek.json())

                        # HERHANGİ 3 ŞARTTAN EN AZ 2'Sİ SAĞLANMALI
                        kazanilan_puan = 0
                        if sut >= 11:
                            kazanilan_puan += 1
                        if isabet >= 4:
                            kazanilan_puan += 1
                        if korner >= 5:
                            kazanilan_puan += 1

                        print(f"[ANALIZ] {ev_takim} {ev_gol}-{dep_gol} {dep_takim} ({dakika}') | Sut: {sut} | Isabet: {isabet} | Korner: {korner} | Kriter Skoru: {kazanilan_puan}/3")

                        if kazanilan_puan >= 2:
                            sut_simgesi = "✅" if sut >= 11 else "❌"
                            isabet_simgesi = "✅" if isabet >= 4 else "❌"
                            korner_simgesi = "✅" if korner >= 5 else "❌"

                            bildirim_metni = (
                                f"🔥 <b>CANLI GOL SİNYALİ (60-75 dk)!</b>\n\n"
                                f"🏆 <b>Lig:</b> {ulke_adi} - {lig_adi}\n"
                                f"⚽ <b>Maç:</b> <b>{ev_takim}</b> {ev_gol} - {dep_gol} <b>{dep_takim}</b>\n"
                                f"⏱ <b>Dakika:</b> {dakika}'\n\n"
                                f"📊 <b>Canlı Baskı İstatistikleri ({kazanilan_puan}/3 Şart):</b>\n"
                                f"• Toplam Şut: <b>{sut}</b> {sut_simgesi} (Hedef: 11+)\n"
                                f"• İsabetli Şut: <b>{isabet}</b> {isabet_simgesi} (Hedef: 4+)\n"
                                f"• Korner: <b>{korner}</b> {korner_simgesi} (Hedef: 5+)\n\n"
                                f"💡 <b>Tavsiye:</b> Nesine/Misli canlısında '1 Gol Daha' oranını bekleyip değerlendirin."
                            )

                            telegram_mesaji_ilet(bildirim_metni)
                            bildirilen_maclar_kumesi.add(mac_id)
                            print(f"[BASARILI] Bildirim gonderildi: {ev_takim} vs {dep_takim}")

            except Exception as tekil_mac_hatasi:
                print(f"[TEKIL MAC ISLEME HATASI]: {tekil_mac_hatasi}")

        print(f"[RAPOR] Canli: {len(canli_mac_listesi)} | Bultende: {bultene_uyan_mac_sayisi} | 60-75 Dk: {dakikasi_uyan_mac_sayisi} | Kalan Kota: {kalan_api_kotasi}")

    except Exception as genel_tarama_hatasi:
        print(f"[GENEL TARAMA MOTORU HATASI]: {genel_tarama_hatasi}")

# ==========================================
# 8. ANA ZAMANLAYICI DÖNGÜSÜ
# ==========================================
def ana_calisma_dongusu():
    acilis_mesaji = (
        "🚀 <b>İddaa Canlı Analiz Sistemi Devrede!</b>\n\n"
        "• <b>Dakika Aralığı:</b> 60 - 75. Dakikalar\n"
        "• <b>Skor Limiti:</b> En fazla 2 fark (2-0, 1-1, 0-2 vb.)\n"
        "• <b>Baskı Kuralı:</b> 3 kriterden (Şut >= 11, İsabet >= 4, Korner >= 5) herhangi 2'si sağlandığında sinyal iletilir.\n"
        "• <b>Kapsam:</b> Türkiye yasal bülteni, tüm Avrupa kupaları ve yerel kupalar."
    )
    telegram_mesaji_ilet(acilis_mesaji)

    while True:
        try:
            anlik_zaman = datetime.now(TURKIYE_SAATI)
            mevcut_saat = anlik_zaman.hour
            hafta_sonu_mu = anlik_zaman.weekday() >= 5

            tarama_yapilsin_mi = False
            bekleme_periyodu = 300

            if hafta_sonu_mu:
                # Hafta sonu: 14:00 - 23:45 (6 dakikada bir tarama)
                if 14 <= mevcut_saat <= 23:
                    tarama_yapilsin_mi = True
                    bekleme_periyodu = 360
            else:
                # Hafta içi: 19:00 - 23:45 (4 dakikada bir tarama)
                if 19 <= mevcut_saat <= 23:
                    tarama_yapilsin_mi = True
                    bekleme_periyodu = 240

            if tarama_yapilsin_mi:
                canli_bulteni_tara()
                time.sleep(bekleme_periyodu)
            else:
                time.sleep(600)

        except Exception as ana_dongu_hatasi:
            print(f"[ANA DONGU KRITIK HATA]: {ana_dongu_hatasi}")
            time.sleep(30)

# ==========================================
# 9. PROGRAM GİRİŞ NOKTASI
# ==========================================
if __name__ == "__main__":
    web_is_parcacigi = threading.Thread(target=arka_plan_web_sunucusu_baslat, daemon=True)
    web_is_parcacigi.start()
    ana_calisma_dongusu()
