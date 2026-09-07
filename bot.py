import telebot
import re
import requests
import os
import threading
from bs4 import BeautifulSoup
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

INFORTUNATI_EXPLICITI = ["Varela G"]
SQUALIFICATI_EXPLICITI = []

# 3. SCRAPING VELOCE E SICURO
def scarica_dati_live_fast():
    percentuali = {}
    stati_speciali = {}
    fantamedia = {}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # A. PROBABILI FORMAZIONI LIVE
    try:
        res = requests.get("https://www.fantamaster.it/probabili-formazioni-serie-a-live/", headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        testo_p = soup.get_text()

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
                
                match_p = re.search(r'\b' + re.escape(cognome) + r'\b.{0,25}?(\d{1,3})\s*%', testo_p, re.I) or \
                          re.search(r'(\d{1,3})\s*%.{0,25}?\b' + re.escape(cognome) + r'\b', testo_p, re.I)

                if match_p:
                    percentuali[g] = int(match_p.group(1))
                else:
                    percentuali[g] = 70 if re.search(r'\b' + re.escape(cognome) + r'\b', testo_p, re.I) else 30
    except Exception as e:
        print(f"Errore probabili: {e}")
        for ruolo, giocatori in mia_rosa.items():
            for g in giocatori:
                percentuali[g] = 0 if g in INFORTUNATI_EXPLICITI else 60
                stati_speciali[g] = "INFORTUNATO" if g in INFORTUNATI_EXPLICITI else "OK"

    # B. REPOSITORY FANTA-MEDIE REALI
    medie_reali = {
        "Maignan": 5.8, "Okoye": 5.5, "Terracciano": 5.0,
        "Ramon": 6.1, "Delprato": 6.2, "Ostigard": 6.0, "Vasquez": 6.3, "Tiago Gabriel": 5.8, "Haps": 5.9, "Valle": 6.0, "Comuzzo": 6.2,
        "Barella": 7.1, "Da Cunha": 6.4, "Diouf": 6.0, "Mastantuono": 6.5, "Chukwueze": 6.3, "Frendrup": 6.4, "Colpani": 6.6, "Busio": 6.3,
        "Kean": 7.8, "Douvikas": 6.7, "Simeone": 6.8, "Adams A": 7.0, "Diao": 6.5, "Varela G": 5.5
    }

    for ruolo, giocatori in mia_rosa.items():
        for g in giocatori:
            fantamedia[g] = medie_reali.get(g, 6.0)

    return percentuali, stati_speciali, fantamedia

# 4. COMANDO /formazione
@bot.message_handler(commands=['formazione'])
def consiglia_formazione(message):
    bot.reply_to(message, "Estrazione Live: Probabili % + FM... 🎯")

    percentuali, stati_speciali, fantamedia = scarica_dati_live_fast()

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
    risposta += f"📐 *Modulo:* `{miglior_modulo}` | 📊 *Ottimizzazione:* _FM × Titolarità_\n"
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

# 5. AVVIO MULTI-THREADING (FLASK + TELEGRAM)
if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    bot.infinity_polling(skip_pending=True)
