import telebot
import re
import asyncio
import requests
import os
import threading
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from flask import Flask

# 1. WEBSERVER DUMMY PER KEEP-ALIVE RENDER (EVITA PORT TIMEOUT)
app = Flask('')

@app.route('/')
def home():
    return "Bot Fantacalcio Online 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 2. TOKEN E ROSA
TOKEN = os.environ.get("TELEGRAM_TOKEN", "8458455550:AAGiOW1l2kI0q8iCAeF8CIVKp1cmS9hHgJo")
bot = telebot.TeleBot(TOKEN)

mia_rosa = {
    "P": ["Maignan", "Okoye", "Terracciano"],
    "D": ["Ramon", "Delprato", "Ostigard", "Vasquez", "Tiago Gabriel", "Haps", "Valle", "Comuzzo"],
    "C": ["Barella", "Da Cunha", "Diouf", "Mastantuono", "Chukwueze", "Frendrup", "Colpani", "Busio"],
    "A": ["Kean", "Douvikas", "Simeone", "Adams A", "Diao", "Varela G"]
}

# LINK DIRETTI COMPLETI PER TUTTI I GIOCATORI
URL_SCHEDE_GIOCATORI = {
    # Portieri
    "Maignan": "https://www.fantacalcio.it/serie-a/squadre/milan/maignan/4312",
    "Okoye": "https://www.fantacalcio.it/serie-a/squadre/udinese/okoye/6462",
    "Terracciano": "https://www.fantacalcio.it/serie-a/squadre/milan/terracciano/2815",
    
    # Difensori
    "Ramon": "https://www.fantacalcio.it/serie-a/squadre/como/ramon/6869",
    "Delprato": "https://www.fantacalcio.it/serie-a/squadre/parma/delprato/6664",
    "Ostigard": "https://www.fantacalcio.it/serie-a/squadre/genoa/ostigard/5750",
    "Vasquez": "https://www.fantacalcio.it/serie-a/squadre/genoa/vasquez/5514",
    "Tiago Gabriel": "https://www.fantacalcio.it/serie-a/squadre/lecce/tiago-gabriel/6989",
    "Haps": "https://www.fantacalcio.it/serie-a/squadre/venezia/haps/5695",
    "Valle": "https://www.fantacalcio.it/serie-a/squadre/como/valle/6867",
    "Comuzzo": "https://www.fantacalcio.it/serie-a/squadre/torino/comuzzo/6495",
    
    # Centrocampisti
    "Barella": "https://www.fantacalcio.it/serie-a/squadre/inter/barella/1870",
    "Da Cunha": "https://www.fantacalcio.it/serie-a/squadre/como/da-cunha/5559",
    "Diouf": "https://www.fantacalcio.it/serie-a/squadre/inter/diouf/6274",
    "Mastantuono": "https://www.fantacalcio.it/serie-a/squadre/fiorentina/mastantuono/7078",
    "Chukwueze": "https://www.fantacalcio.it/serie-a/squadre/milan/chukwueze/4856",
    "Frendrup": "https://www.fantacalcio.it/serie-a/squadre/genoa/frendrup/5791",
    "Colpani": "https://www.fantacalcio.it/serie-a/squadre/monza/colpani/5878",
    "Busio": "https://www.fantacalcio.it/serie-a/squadre/venezia/busio/5507",
    
    # Attaccanti
    "Kean": "https://www.fantacalcio.it/serie-a/squadre/como/kean/2097",
    "Douvikas": "https://www.fantacalcio.it/serie-a/squadre/como/douvikas/7017",
    "Simeone": "https://www.fantacalcio.it/serie-a/squadre/torino/simeone/2061",
    "Adams A": "https://www.fantacalcio.it/serie-a/squadre/venezia/adams-a/7484",
    "Diao": "https://www.fantacalcio.it/serie-a/squadre/como/diao/6967",
    "Varela G": "https://www.fantacalcio.it/serie-a/squadre/monza/varela-g/7523"
}

INFORTUNATI_EXPLICITI = ["Varela G"]
SQUALIFICATI_EXPLICITI = []

# 3. SCRAPING INTEGRATO PLAYWRIGHT (PROBABILI + SCHEDE GIOCATORI)
async def scarica_dati_live_playwright():
    percentuali = {}
    stati_speciali = {}
    fantamedia = {g: 6.0 for ruolo in mia_rosa for g in mia_rosa[ruolo]}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # A. SCRAPING PROBABILI FORMAZIONI
        try:
            await page.goto("https://www.fantamaster.it/probabili-formazioni-serie-a-live/", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(1000)
            content_prob = await page.content()
            soup_p = BeautifulSoup(content_prob, 'html.parser')
            testo_p = soup_p.get_text()

            for ruolo, giocatori in mia_rosa.items():
                for g in giocatori:
                    if g in INFORTUNATI_EXPLICITI:
                        percentuali[g] = 0
                        stati_speciali[g] = "INFORTUNATO"
                        continue
                    if g in SQUALIFICATI_EXPLICITI:
                        percentuali[g] = 0
                        stati_speciali[g] = "SQUALIFICATO"
                        continue

                    stati_speciali[g] = "OK"
                    cognome = g.split()[0]
                    match_p = re.search(r'\b' + re.escape(cognome) + r'\b.{0,15}?(\d{1,3})\s*%', testo_p, re.I) or \
                              re.search(r'(\d{1,3})\s*%.{0,15}?\b' + re.escape(cognome) + r'\b', testo_p, re.I)

                    if match_p:
                        percentuali[g] = int(match_p.group(1))
                    else:
                        percentuali[g] = 100 if re.search(r'\b' + re.escape(cognome) + r'\b', testo_p, re.I) else 5
        except Exception as e:
            print(f"Errore Probabili Formazioni: {e}")

        # B. SCRAPING FANTA-MEDIE DA SCHEDE GIOCATORE
        for ruolo, giocatori in mia_rosa.items():
            for g in giocatori:
                url = URL_SCHEDE_GIOCATORI.get(g, "")
                if not url or not url.startswith("http"):
                    continue

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=5000)
                    html_scheda = await page.content()
                    soup_s = BeautifulSoup(html_scheda, 'html.parser')
                    txt = soup_s.get_text()

                    match = re.search(r'FM[\s\n\r]*(\d{1,2}[\.,]\d{1,2})', txt, re.I) or \
                            re.search(r'(\d{1,2}[\.,]\d{1,2})[\s\n\r]*FM', txt, re.I)

                    if match:
                        fantamedia[g] = float(match.group(1).replace(',', '.'))
                    else:
                        valori = re.findall(r'\b\d{1,2}[\.,]\d{1,2}\b', txt)
                        validi = [float(v.replace(',', '.')) for v in valori if 3.5 <= float(v.replace(',', '.')) <= 15.0]
                        if validi:
                            fantamedia[g] = validi[1] if len(validi) >= 2 else validi[0]
                except Exception as e:
                    print(f"Errore scheda {g}: {e}")

        await browser.close()

    return percentuali, stati_speciali, fantamedia

# 4. COMANDO /formazione
@bot.message_handler(commands=['formazione'])
def consiglia_formazione(message):
    bot.reply_to(message, "Estrazione Live: Probabili % + FM da schede... 🎯")

    percentuali, stati_speciali, fantamedia = asyncio.run(scarica_dati_live_playwright())

    indice_schierabilita = {}
    for ruolo, giocatori in mia_rosa.items():
        for g in giocatori:
            if stati_speciali.get(g) != "OK":
                indice_schierabilita[g] = 0.0
            else:
                p = percentuali.get(g, 0)
                fm = fantamedia.get(g, 6.0)
                indice_schierabilita[g] = (p / 100.0) * fm

    disponibili = {"P": [], "D": [], "C": [], "A": []}
    for ruolo, giocatori in mia_rosa.items():
        for g in giocatori:
            if percentuali.get(g, 0) >= 20 and stati_speciali.get(g) == "OK":
                disponibili[ruolo].append(g)

    coppie_ballottaggio = [("Kean", "Douvikas"), ("Maignan", "Terracciano")]
    for t1, t2 in coppie_ballottaggio:
        ruolo_target = next((r for r, lista in mia_rosa.items() if t1 in lista), None)
        if t1 in disponibili[ruolo_target] and t2 in disponibili[ruolo_target]:
            if indice_schierabilita.get(t1, 0) >= indice_schierabilita.get(t2, 0):
                disponibili[ruolo_target].remove(t2)
            else:
                disponibili[ruolo_target].remove(t1)

    for r in disponibili:
        disponibili[r].sort(key=lambda g: indice_schierabilita.get(g, 0), reverse=True)

    portiere_titolare = disponibili["P"][0] if disponibili["P"] else mia_rosa["P"][0]
    portieri_panchina = [p for p in mia_rosa["P"] if p != portiere_titolare]

    moduli_ammessi = [(3, 4, 3), (4, 3, 3), (3, 5, 2), (4, 4, 2), (4, 5, 1), (5, 3, 2)]
    miglior_modulo = None
    max_punteggio_is = -1.0
    miglior_undici = {"D": [], "C": [], "A": []}

    for d, c, a in moduli_ammessi:
        def_scelti = disponibili["D"][:d]
        cent_scelti = disponibili["C"][:c]
        att_scelti = disponibili["A"][:a]

        punteggio_modulo = sum(indice_schierabilita.get(g, 0) for g in def_scelti + cent_scelti + att_scelti)

        if punteggio_modulo > max_punteggio_is:
            max_punteggio_is = punteggio_modulo
            miglior_modulo = f"{d}-{c}-{a}"
            miglior_undici["D"] = def_scelti + [p for p in mia_rosa["D"] if p not in def_scelti][:d - len(def_scelti)]
            miglior_undici["C"] = cent_scelti + [p for p in mia_rosa["C"] if p not in cent_scelti][:c - len(cent_scelti)]
            miglior_undici["A"] = att_scelti + [p for p in mia_rosa["A"] if p not in att_scelti][:a - len(att_scelti)]

    panchina_ordinata = portieri_panchina.copy()
    for ruolo in ["D", "C", "A"]:
        esclusi = [g for g in mia_rosa[ruolo] if g not in miglior_undici[ruolo] and stati_speciali.get(g) == "OK"]
        panchina_ordinata.extend(esclusi)

    # OUTPUT MESSAGGIO TELEGRAM
    risposta = f"🏆 *FORMAZIONE CONSIGLIATA* 🏆\n"
    risposta += f"📐 *Modulo:* `{miglior_modulo}` | 📊 *Ottimizzazione:* _FM Schede × Titolarità_\n"
    risposta += f"━━━━━━━━━━━━━━━━━━━━━━\n\n"

    p_perc = percentuali.get(portiere_titolare, 0)
    p_fm = fantamedia.get(portiere_titolare, 6.0)
    p_badge = "🟢" if p_perc >= 70 else "🟡"
    risposta += f"🧤 *PORTA*\n└ {p_badge} *{portiere_titolare}* — `{p_perc}%` _(FM: {p_fm})_\n\n"

    nomi_ruoli = {"D": "🛡 DIFESA", "C": "⚙️ CENTROCAMPO", "A": "🎯 ATTACCO"}
    for ruolo in ["D", "C", "A"]:
        risposta += f"*{nomi_ruoli[ruolo]}*\n"
        for g in miglior_undici[ruolo]:
            perc = percentuali.get(g, 0)
            fm = fantamedia.get(g, 6.0)
            badge = "🟢" if perc >= 70 else "🟡"
            risposta += f"├ {badge} *{g}* — `{perc}%` _(FM: {fm})_\n"
        risposta += "\n"

    risposta += f"━━━━━━━━━━━━━━━━━━━━━━\n"
    risposta += f"🪑 *PANCHINA ORDINATA*\n\n"

    for ruolo in ["P", "D", "C", "A"]:
        giocatori_p = [p for p in panchina_ordinata if p in mia_rosa[ruolo]]
        if giocatori_p:
            risposta += f"*{ruolo}:* "
            elenco_p = [f"{p} ({percentuali.get(p, 0)}% - FM: {fantamedia.get(p, 6.0)})" for p in giocatori_p]
            risposta += " • ".join(elenco_p) + "\n"

    infortunati = [g for g, st in stati_speciali.items() if st == "INFORTUNATO"]
    squalificati = [g for g, st in stati_speciali.items() if st == "SQUALIFICATO"]

    if infortunati or squalificati:
        risposta += f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
        risposta += f"🚑 *INDISPONIBILI*\n"
        if infortunati:
            inf_str = [f"{g} (FM: {fantamedia.get(g, 6.0)})" for g in infortunati]
            risposta += f"🏥 *Infortunati:* {', '.join(inf_str)}\n"
        if squalificati:
            sq_str = [f"{g} (FM: {fantamedia.get(g, 6.0)})" for g in squalificati]
            risposta += f"🟥 *Squalificati:* {', '.join(sq_str)}\n"

    titolari_certi = sum(1 for r in miglior_undici for g in miglior_undici[r] if percentuali.get(g, 0) >= 70)
    if percentuali.get(portiere_titolare, 0) >= 70:
        titolari_certi += 1

    risposta += f"\n📊 *Riepilogo:* 🟢 `{titolari_certi}/11` Titolari | 🟡 `{11 - titolari_certi}` Ballottaggi"

    bot.send_message(message.chat.id, risposta, parse_mode="Markdown")

# 5. AVVIO MULTI-THREADING (FLASK SERVER + TELEGRAM BOT ANTI-CONFLITTO)
if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    bot.infinity_polling(skip_pending=True)
