import telebot
from telebot import types
import uuid, os, json, time, requests

TOKEN   = '7870656606:AAHZDaDqOA0d3FYUEKdmcXbjJIUhtNmCktQ'
ADMIN_ID = 6029446099
FALLBACK_PIC = 'leprofessionnel.jpg'

MAIN_CHAN   = 'https://t.me/+8VLpDp5-Cqc4OTI0'
OPINIE_CHAN = 'https://t.me/c/3635144020/28'

bot = telebot.TeleBot(TOKEN)
saldo_db, user_cache, top_up_cache = {}, {}, {}

def get_saldo(uid): return saldo_db.get(uid, 0)
def set_saldo(uid, v): saldo_db[uid] = max(0, v)

COINGECKO_URL = 'https://api.coingecko.com/api/v3/simple/price'

def fetch_rates():
    ids = 'litecoin,bitcoin,ethereum,tether,monero,solana,the-open-network'; vs = 'pln'
    try:
        r = requests.get(COINGECKO_URL, params={'ids': ids, 'vs_currencies': vs}, timeout=10)
        r.raise_for_status(); return {k: r.json()[k]['pln'] for k in r.json()}
    except: return None

def crypto_amount(pln, crypto):
    r = fetch_rates(); return None if r is None else pln / r.get(crypto, 1)

USERS_FILE = 'users.json'
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    return {}
def save_users(data):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def save_user_order(uid, city, prod, grams, price_pln, crypto, amount_crypto, delivery):
    users = load_users(); uid_str = str(uid)
    if uid_str not in users: users[uid_str] = {'saldo': get_saldo(uid), 'history': [], 'last_order': 'brak'}
    ts = time.strftime("%d.%m.%Y %H:%M")
    order = f"{prod.upper()} {grams} g ({city}) – {price_pln:.2f} zł – {amount_crypto:.6f} {crypto.upper()} – {delivery} – {ts}"
    users[uid_str]['history'].append(order); users[uid_str]['last_order'] = order
    save_users(users)

def send_panel(chat_id, text, photo_name=None, kb=None):
    if photo_name and os.path.exists(photo_name):
        with open(photo_name, 'rb') as img:
            return bot.send_photo(chat_id, img, caption=text, parse_mode='HTML', reply_markup=kb)
    if photo_name:
        if os.path.exists(FALLBACK_PIC):
            with open(FALLBACK_PIC, 'rb') as img:
                return bot.send_photo(chat_id, img, caption=text, parse_mode='HTML', reply_markup=kb)
    return bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=kb)

def build_channel_menu():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("📣 Główny kanał", url=MAIN_CHAN),
           types.InlineKeyboardButton("⭐ Opinie", url=OPINIE_CHAN),
           types.InlineKeyboardButton("⬅️ Powrót", callback_data='back_to_start'))
    return kb

def build_main_menu():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("👤 Mój profil", callback_data='my_profile'),
        types.InlineKeyboardButton("💵 Doładuj saldo", callback_data='top_up'),
        types.InlineKeyboardButton("📋 Cennik", callback_data='price_list'),
        types.InlineKeyboardButton("📢 Grupa TG", callback_data='channel_menu')
    )
    return kb

def count_user_orders(uid):
    users = load_users()
    return len(users.get(str(uid), {}).get('history', []))

# ===============  START  ===============
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id; bal = get_saldo(uid)
    text = (f"👋 <b>Le Professionnel</b> – witaj {message.from_user.first_name}!</b>\n\n"
            f"💰 Saldo: <code>{bal} zł</code>\n"
            f"📦 <b>Wysyłka InPost/Poczta/DPD/Znaczek – tylko od 50 g (+40 zł)</b>")
    send_panel(message.chat.id, text, FALLBACK_PIC, build_main_menu())

# ===============  PROFILE  ===============
@bot.callback_query_handler(func=lambda call: call.data == 'my_profile')
def my_profile(call):
    uid = call.from_user.id
    bal = get_saldo(uid)
    orders = count_user_orders(uid)
    text = (f"👤 <b>Twój profil</b>\n\n"
            f"🆔 ID: <code>{uid}</code>\n"
            f"💰 Saldo: <code>{bal} zł</code>\n"
            f"📦 Łączna liczba zamówień: <b>{orders}</b>")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅️ Powrót", callback_data='back_to_start'))
    bot.edit_message_caption(chat_id=call.message.chat.id,
                             message_id=call.message.message_id,
                             caption=text,
                             parse_mode='HTML',
                             reply_markup=kb)

# ===============  TOP-UP  ===============
@bot.callback_query_handler(func=lambda call: call.data == 'top_up')
def top_up_start(call):
    text = "💵 <b>Ile złotych chcesz doładować?</b>\n\nNapisz tylko kwotę (np. 200):"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅️ Anuluj", callback_data='back_to_start'))
    bot.edit_message_caption(chat_id=call.message.chat.id,
                             message_id=call.message.message_id,
                             caption=text,
                             parse_mode='HTML',
                             reply_markup=kb)
    bot.register_next_step_handler(call.message, top_up_amount)

def top_up_amount(message):
    try:
        amount = int(message.text)
        if amount <= 0: raise ValueError
    except:
        bot.reply_to(message, "❗ Nieprawidłowa kwota. Wpisz liczbę całkowitą > 0.")
        bot.register_next_step_handler(message, top_up_amount); return
    uid = message.from_user.id
    top_up_cache[uid] = amount
    text = (f"💵 <b>Doładuj saldo</b>\n\n"
            f"Kwota: <b>{amount} zł</b>\n\n"
            f"Wybierz metodę płatności:")
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📞 BLIK / przelew", callback_data=f'topup_tel_{amount}'),
        types.InlineKeyboardButton("ETH / USDT", callback_data=f'topup_eth_{amount}'),
        types.InlineKeyboardButton("USDT (TRON)", callback_data=f'topup_tron_{amount}'),
        types.InlineKeyboardButton("BTC", callback_data=f'topup_btc_{amount}'),
        types.InlineKeyboardButton("LTC", callback_data=f'topup_ltc_{amount}'),
        types.InlineKeyboardButton("TON", callback_data=f'topup_ton_{amount}'),
        types.InlineKeyboardButton("XMR Monero", callback_data=f'topup_xmr_{amount}'),
        types.InlineKeyboardButton("SOL Solana", callback_data=f'topup_sol_{amount}')
    )
    kb.row(types.InlineKeyboardButton("⬅️ Anuluj", callback_data='back_to_start'))
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=kb)

# ===============  TOP-UP PAYMENT  ===============
@bot.callback_query_handler(func=lambda call: call.data.startswith('topup_'))
def topup_payment(call):
    parts = call.data.split('_')
    method, amount = parts[1], float(parts[2])
    uid = call.from_user.id
    pay_id = str(uuid.uuid4())
    crypto_val = crypto_amount(amount, method)
    if crypto_val is None:
        bot.answer_callback_query(call.id, "❗ Błąd pobierania kursów walut", show_alert=True); return
    min_dep = 0.00003 if method in ('btc','ltc','eth','tron') else 0.1
    addr = {
        'eth': '0x05e8c9e064d52C3F63b278B8120C53e49E70e26c',
        'tron': 'TVCeVXceuZtiQ9sZj3j4mDQ87Zw9NfvG3T',
        'btc': 'bc1qfwsz3ltfuxe33trezk0mdvsvcqx48d6250tda8',
        'ltc': 'LQfBdUpBfrUN5KYkZPmjPB1ieZcSSFXKaM',
        'ton': 'EQD4KZ1lXqCmRXXnY3L9fH9Y3L9fH9Y3L9fH9Y3L9fH9',
        'xmr': '46yz1JJP9k8GTgN3Vb5mYYCJgQWgXJHmXJtF5yU7L9fH9Y3L9fH9Y3L9fH9',
        'sol': 'SoLWl1234567890abcdef'
    }.get(method, '-')
    text = (f"<b>Le Professionnel - doładowanie</b>\n"
            f"ID płatności: <code>{pay_id}</code>\n\n"
            f"💳 Metoda: <b>{method.upper()}</b>\n"
            f"📨 Adres: <code>{addr}</code>\n\n"
            f"💰 Kwota do zapłaty: <b>{crypto_val:.6f} {method.upper()}</b>\n"
            f"⏳ Czas: <b>29 minut</b>\n\n"
            f"⚠️ Wyślij dokładnie <b>{crypto_val:.6f}</b> (min. {min_dep}) jednym przelewem – inaczej środki przepadną!")
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("📋 Kopiuj dane", callback_data=f'copy_{method}'),
           types.InlineKeyboardButton("✅ Sprawdzam płatność", callback_data=f'topup_check_{pay_id}_{uid}_{amount}'))
    kb.row(types.InlineKeyboardButton("⬅️ Anuluj", callback_data='back_to_start'))
    bot.edit_message_caption(chat_id=call.message.chat.id,
                             message_id=call.message.message_id,
                             caption=text,
                             parse_mode='HTML',
                             reply_markup=kb)

# ===============  CENNIK  ===============
@bot.callback_query_handler(func=lambda call: call.data == 'price_list')
def price_list(call):
    text = (
        "📋 <b>CENNIK Le Professionnel</b>\n\n"

        "❄️ <b>Czysta kokaina</b>\n"
        "1 g – 300 zł  5 g – 300 zł  10 g – 240 zł  25 g – 200 zł  50 g – 160 zł  100 g – 140 zł  1000 g – 125 zł\n\n"

        "🌿 <b>Marihuana InDoor z USA</b>\n"
        "5 g – 32 zł  10 g – 32 zł  25 g – 30 zł  50 g – 28 zł  100 g – 26 zł  250 g – 23 zł  500 g – 22 zł  1000 g – 21 zł\n\n"

        "🍬 <b>MDMA tabletki 270 mg</b>\n"
        "10 szt – 20 zł  25 szt – 15 zł  50 szt – 12 zł  100 szt – 11 zł  250 szt – 9 zł  500 szt – 8 zł  1000 szt – 4 zł  5000 szt – 3 zł\n\n"

        "🍾 <b>MDMA kryształ</b>\n"
        "1 g – 60 zł  5 g – 50 zł  10 g – 45 zł  25 g – 43 zł  50 g – 38 zł  100 g – 30 zł  250 g – 25 zł  500 g – 22 zł\n\n"

        "⚡ <b>Sucha amfetamina</b>\n"
        "5 g – 30 zł  10 g – 25 zł  25 g – 20 zł  50 g – 16 zł  100 g – 12 zł  250 g – 10 zł  500 g – 9 zł\n\n"

        "💊 <b>4MMC Kenzo 280 mg</b>\n"
        "50 szt – 550 zł  100 szt – 1000 zł  500 szt – 3000 zł\n\n"

        "💊 <b>3-CMC</b>\n"
        "5 g – 50 zł  10 g – 28 zł  25 g – 23 zł  50 g – 21 zł  100 g – 19 zł  250 g – 18 zł  500 g – 15 zł  1000 g – 12 zł\n\n"

        "🔬 <b>4-CMC</b>\n"
        "5 g – 50 zł  10 g – 28 zł  25 g – 23 zł  50 g – 21 zł  100 g – 19 zł  250 g – 15 zł  500 g – 13 zł  1000 g – 11 zł\n\n"

        "🌸 <b>TUCI / Różowa Kokaina</b>\n"
        "1 g – 140 zł  2 g – 125 zł  3 g – 120 zł  4 g – 110 zł  5 g – 100 zł  10 g – 95 zł  20 g – 90 zł  30 g – 80 zł  40 g – 75 zł  50 g – 70 zł  100 g – 65 zł  200 g – 50 zł  500 g – 45 zł\n\n"

        "💉 <b>KETAMINA – IGŁY</b>\n"
        "1 g – 75 zł  3 g – 70 zł  5 g – 60 zł  10 g – 45 zł  20 g – 40 zł  30 g – 35 zł  40 g – 32 zł  50 g – 26 zł  100 g – 16 zł  200 g – 15 zł\n\n"

        "🍬 <b>KETAMINA – KAMIENIE</b>\n"
        "1 g – 75 zł  3 g – 70 zł  5 g – 60 zł  10 g – 45 zł  20 g – 40 zł  30 g – 35 zł  40 g – 32 zł  50 g – 26 zł  100 g – 16 zł  200 g – 15 zł\n\n"

        "🍄 <b>LSD Mario 250 µg</b>\n"
        "10 szt – 15 zł  50 szt – 10 zł  100 szt – 9 zł  200 szt – 8 zł  300 szt – 7 zł  400 szt – 6 zł  500 szt – 5 zł  1000 szt – 4,8 zł\n\n"

        "🧪 <b>HEROINA</b>\n"
        "1 g – 200 zł  5 g – 850 zł  10 g – 1600 zł  25 g – 3500 zł  50 g – 5900 zł  100 g – 10 000 zł\n\n"

        "❄️ <b>PIKO / METAMFETAMINA</b>\n"
        "1 g – 180 zł  5 g – 160 zł  10 g – 150 zł  25 g – 130 zł  50 g – 110 zł  100 g – 90 zł\n\n"

        "🟤 <b>2CB 25 mg</b>\n"
        "10 tab – 220 zł  50 tab – 680 zł  100 tab – 1100 zł  500 tab – 3000 zł  1000 tab – 5300 zł\n\n"

        "🍯 <b>Żywica THC 90 %</b>\n"
        "1 g – 220 zł  2 g – 350 zł  5 g – 700 zł  10 g – 1000 zł  50 g – 3500 zł  100 g – 6000 zł"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅️ Powrót", callback_data='back_to_start'))
    bot.edit_message_caption(chat_id=call.message.chat.id,
                             message_id=call.message.message_id,
                             caption=text,
                             parse_mode='HTML',
                             reply_markup=kb)

# ===============  POWROTY  ===============
@bot.callback_query_handler(func=lambda call: call.data == 'back_to_start')
def back_to_start(call):
    start(call.message)
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

@bot.callback_query_handler(func=lambda call: call.data == 'channel_menu')
def channel_menu(call):
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                  reply_markup=build_channel_menu())

# ===============  START  ===============
if __name__ == '__main__':
    print("Le Professionnel (nowy panel powitalny + cennik estetyka) działa…")
    bot.infinity_polling(skip_pending=True)
