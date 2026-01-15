import telebot
from telebot import types
import uuid, os, json, time, requests

TOKEN   = '7870656606:AAHZDaDqOA0d3FYUEKdmcXbjJIUhtNmCktQ'
ADMIN_ID = 6029446099
FALLBACK_PIC = 'leprofessionnel.jpg'
MAIN_CHAN   = 'https://t.me/+8VLpDp5-Cqc4OTI0  '
OPINIE_CHAN = 'https://t.me/c/3635144020/28  '
CONTACT_USER = '@LeProfessionnel_operator'

bot = telebot.TeleBot(TOKEN)
saldo_db, user_cache, top_up_cache, cart = {}, {}, {}, {}
MIN_ORDER = 300
MIN_DEAD  = 1

# -------------------- pomocnicze --------------------
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
    with open(USERS_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2, ensure_ascii=False)

def save_user_order(uid, city, prod, grams, price_pln, crypto, amount_crypto, delivery):
    users = load_users(); uid_str = str(uid)
    if uid_str not in users: users[uid_str] = {'saldo': get_saldo(uid), 'history': [], 'last_order': 'brak'}
    ts = time.strftime("%d.%m.%Y %H:%M")
    order = f"{prod.upper()} {grams} g ({city}) – {price_pln:.2f} zł – {amount_crypto:.6f} {crypto.upper()} – {delivery} – {ts}"
    users[uid_str]['history'].append(order); users[uid_str]['last_order'] = order
    save_users(users)

def send_panel(chat_id, text, photo_name=None, kb=None):
    if photo_name and os.path.exists(photo_name):
        with open(photo_name, 'rb') as img: return bot.send_photo(chat_id, img, caption=text, parse_mode='HTML', reply_markup=kb)
    if os.path.exists(FALLBACK_PIC):
        with open(FALLBACK_PIC, 'rb') as img: return bot.send_photo(chat_id, img, caption=text, parse_mode='HTML', reply_markup=kb)
    return bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=kb)

def build_main_menu():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("👤 Mój profil", callback_data='my_profile'),
        types.InlineKeyboardButton("💵 Doładuj saldo", callback_data='top_up'),
        types.InlineKeyboardButton("📋 Cennik (info)", callback_data='price_list_info'),
        types.InlineKeyboardButton("🛍️ Sklep (dodaj do koszyka)", callback_data='shop'),
        types.InlineKeyboardButton("🛒 Koszyk", callback_data='show_cart'),
        types.InlineKeyboardButton("📢 Grupa TG", callback_data='channel_menu'),
        types.InlineKeyboardButton("📞 Kontakt", callback_data='contact')
    )
    return kb

def build_channel_menu():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("📣 Główny kanał", url=MAIN_CHAN),
           types.InlineKeyboardButton("⭐ Opinie", url=OPINIE_CHAN),
           types.InlineKeyboardButton("⬅️ Powrót", callback_data='back_to_start'))
    return kb

def count_user_orders(uid):
    return len(load_users().get(str(uid), {}).get('history', []))

# -------------------- START --------------------
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id; bal = get_saldo(uid)
    text = (f"👋 <b>Le Professionnel</b> – witaj {message.from_user.first_name}!\n\n"
            f"💰 Saldo: <code>{bal} zł</code>\n"
            f"🛒 Minimalne zamówienie: <b>{MIN_ORDER} zł</b>\n"
            f"📦 Dead-drop już od <b>{MIN_DEAD} g</b>\n\n"
            "<blockquote>Jesteśmy dostępni w miastach:\n"
            "• Warszawa\n• Gdańsk\n• Kraków\n• Wrocław\n• Legnica\n• Katowice</blockquote>")
    send_panel(message.chat.id, text, FALLBACK_PIC, build_main_menu())

# -------------------- PROFILE / KONTAKT / POWROTY --------------------
@bot.callback_query_handler(func=lambda call: call.data == 'my_profile')
def my_profile(call):
    uid = call.from_user.id; bal = get_saldo(uid); orders = count_user_orders(uid)
    text = (f"👤 <b>Twój profil</b>\n\n"
            f"🆔 ID: <code>{uid}</code>\n"
            f"💰 Saldo: <code>{bal} zł</code>\n"
            f"📦 Zamówienia: <b>{orders}</b>")
    kb = types.InlineKeyboardMarkup(); kb.add(types.InlineKeyboardButton("⬅️ Powrót", callback_data='back_to_start'))
    bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                             caption=text, parse_mode='HTML', reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == 'contact')
def contact(call):
    text = f"📞 <b>Kontakt</b>\n\nNapisz do operatora:\n{CONTACT_USER}"
    kb = types.InlineKeyboardMarkup(); kb.add(types.InlineKeyboardButton("⬅️ Powrót", callback_data='back_to_start'))
    bot.send_message(call.message.chat.id, text, parse_mode='HTML', reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_start')
def back_to_start(call):
    start(call.message)
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

@bot.callback_query_handler(func=lambda call: call.data == 'channel_menu')
def channel_menu(call):
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                  reply_markup=build_channel_menu())

# -------------------- STARY CENNIK (BEZ PRZYCISKÓW) --------------------
@bot.callback_query_handler(func=lambda call: call.data == 'price_list_info')
def price_list_info(call):
    text = (
        "📋 <b>CENNIK Le Professionnel</b>\n\n"

        "<blockquote>❄️ Czysta kokaina\n"
        "1 g – 300 zł\n"
        "5 g – 300 zł\n"
        "10 g – 240 zł\n"
        "25 g – 200 zł\n"
        "50 g – 160 zł\n"
        "100 g – 140 zł\n"
        "1000 g – 125 zł</blockquote>\n\n"

        "<blockquote>🌿 Marihuana InDoor z USA\n"
        "5 g – 32 zł\n"
        "10 g – 32 zł\n"
        "25 g – 30 zł\n"
        "50 g – 28 zł\n"
        "100 g – 26 zł\n"
        "250 g – 23 zł\n"
        "500 g – 22 zł\n"
        "1000 g – 21 zł</blockquote>\n\n"

        "<blockquote>🍬 MDMA tabletki 270 mg\n"
        "10 szt – 20 zł\n"
        "25 szt – 15 zł\n"
        "50 szt – 12 zł\n"
        "100 szt – 11 zł\n"
        "250 szt – 9 zł\n"
        "500 szt – 8 zł\n"
        "1000 szt – 4 zł\n"
        "5000 szt – 3 zł</blockquote>\n\n"

        "<blockquote>🍾 MDMA kryształ\n"
        "1 g – 60 zł\n"
        "5 g – 50 zł\n"
        "10 g – 45 zł\n"
        "25 g – 43 zł\n"
        "50 g – 38 zł\n"
        "100 g – 30 zł\n"
        "250 g – 25 zł\n"
        "500 g – 22 zł</blockquote>\n\n"

        "<blockquote>Sucha amfetamina\n"
        "5 g – 30 zł\n"
        "10 g – 25 zł\n"
        "25 g – 20 zł\n"
        "50 g – 16 zł\n"
        "100 g – 12 zł\n"
        "250 g – 10 zł\n"
        "500 g – 9 zł</blockquote>\n\n"

        "<blockquote>💊 4MMC Kenzo 280 mg\n"
        "50 szt – 550 zł\n"
        "100 szt – 1000 zł\n"
        "500 szt – 3000 zł</blockquote>\n\n"

        "<blockquote>💊 3-CMC\n"
        "5 g – 50 zł\n"
        "10 g – 28 zł\n"
        "25 g – 23 zł\n"
        "50 g – 21 zł\n"
        "100 g – 19 zł\n"
        "250 g – 18 zł\n"
        "500 g – 15 zł\n"
        "1000 g – 12 zł</blockquote>\n\n"

        "<blockquote>🔬 4-CMC\n"
        "5 g – 50 zł\n"
        "10 g – 28 zł\n"
        "25 g – 23 zł\n"
        "50 g – 21 zł\n"
        "100 g – 19 zł\n"
        "250 g – 15 zł\n"
        "500 g – 13 zł\n"
        "1000 g – 11 zł</blockquote>\n\n"

        "<blockquote>🌸 TUCI / Różowa Kokaina\n"
        "1 g – 140 zł\n"
        "2 g – 125 zł\n"
        "3 g – 120 zł\n"
        "4 g – 110 zł\n"
        "5 g – 100 zł\n"
        "10 g – 95 zł\n"
        "20 g – 90 zł\n"
        "30 g – 80 zł\n"
        "40 g – 75 zł\n"
        "50 g – 70 zł\n"
        "100 g – 65 zł\n"
        "200 g – 50 zł\n"
        "500 g – 45 zł</blockquote>\n\n"

        "<blockquote>💉 KETAMINA – IGŁY\n"
        "1 g – 75 zł\n"
        "3 g – 70 zł\n"
        "5 g – 60 zł\n"
        "10 g – 45 zł\n"
        "20 g – 40 zł\n"
        "30 g – 35 zł\n"
        "40 g – 32 zł\n"
        "50 g – 26 zł\n"
        "100 g – 16 zł\n"
        "200 g – 15 zł</blockquote>\n\n"

        "<blockquote>🍬 KETAMINA – KAMIENIE\n"
        "1 g – 75 zł\n"
        "3 g – 70 zł\n"
        "5 g – 60 zł\n"
        "10 g – 45 zł\n"
        "20 g – 40 zł\n"
        "30 g – 35 zł\n"
        "40 g – 32 zł\n"
        "50 g – 26 zł\n"
        "100 g – 16 zł\n"
        "200 g – 15 zł</blockquote>\n\n"

        "<blockquote>🍄 LSD Mario 250 µg\n"
        "10 szt – 15 zł\n"
        "50 szt – 10 zł\n"
        "100 szt – 9 zł\n"
        "200 szt – 8 zł\n"
        "300 szt – 7 zł\n"
        "400 szt – 6 zł\n"
        "500 szt – 5 zł\n"
        "1000 szt – 4,8 zł</blockquote>\n\n"

        "<blockquote>🧪 HEROINA\n"
        "1 g – 200 zł\n"
        "5 g – 850 zł\n"
        "10 g – 1600 zł\n"
        "25 g – 3500 zł\n"
        "50 g – 5900 zł\n"
        "100 g – 10 000 zł</blockquote>\n\n"

        "<blockquote>❄️ PIKO / METAMFETAMINA\n"
        "1 g – 180 zł\n"
        "5 g – 160 zł\n"
        "10 g – 150 zł\n"
        "25 g – 130 zł\n"
        "50 g – 110 zł\n"
        "100 g – 90 zł</blockquote>\n\n"

        "<blockquote>🟤 2CB 25 mg\n"
        "10 tab – 220 zł\n"
        "50 tab – 680 zł\n"
        "100 tab – 1100 zł\n"
        "500 tab – 3000 zł\n"
        "1000 tab – 5300 zł</blockquote>\n\n"

        "<blockquote>🍯 Żywica THC 90 %\n"
        "1 g – 220 zł\n"
        "2 g – 350 zł\n"
        "5 g – 700 zł\n"
        "10 g – 1000 zł\n"
        "50 g – 3500 zł\n"
        "100 g – 6000 zł</blockquote>"
    )
    kb = types.InlineKeyboardMarkup(); kb.add(types.InlineKeyboardButton("⬅️ Powrót", callback_data='back_to_start'))
    bot.send_message(call.message.chat.id, text, parse_mode='HTML', reply_markup=kb)

# -------------------- NOWY SKLEP Z FOTKAMI --------------------
PRODUCTS = {
    "Kokaina": {"unit": "g", "pic": "koko.jpg", "items": {"1":300,"5":300,"10":240,"25":200,"50":160,"100":140,"1000":125}},
    "Marihuana InDoor z USA": {"unit": "g", "pic": "zip.jpg", "items": {"5":32,"10":32,"25":30,"50":28,"100":26,"250":23,"500":22,"1000":21}},
    "MDMA tabletki 270 mg": {"unit": "szt", "pic": "mdma.jpg", "items": {"10":20,"25":15,"50":12,"100":11,"250":9,"500":8,"1000":4,"5000":3}},
    "MDMA kryształ": {"unit": "g", "pic": "mdma2.jpg", "items": {"1":60,"5":50,"10":45,"25":43,"50":38,"100":30,"250":25,"500":22}},
    "Sucha amfetamina": {"unit": "g", "pic": "amfa.jpg", "items": {"5":30,"10":25,"25":20,"50":16,"100":12,"250":10,"500":9}},
    "4MMC Kenzo 280 mg": {"unit": "szt", "pic": "kenzo.jpg", "items": {"50":550,"100":1000,"500":3000}},
    "3-CMC": {"unit": "g", "pic": "3cmc.jpg", "items": {"5":50,"10":28,"25":23,"50":21,"100":19,"250":18,"500":15,"1000":12}},
    "4-CMC": {"unit": "g", "pic": "4cmc.jpg", "items": {"5":50,"10":28,"25":23,"50":21,"100":19,"250":15,"500":13,"1000":11}},
    "TUCI / Różowa Kokaina": {"unit": "g", "pic": "TUCI.jpg", "items": {"1":140,"2":125,"3":120,"4":110,"5":100,"10":95,"20":90,"30":80,"40":75,"50":70,"100":65,"200":50,"500":45}},
    "KETAMINA – IGŁY": {"unit": "g", "pic": "ketaigly.jpg", "items": {"1":75,"3":70,"5":60,"10":45,"20":40,"30":35,"40":32,"50":26,"100":16,"200":15}},
    "KETAMINA – KAMIENIE": {"unit": "g", "pic": "ketakamulec.jpg", "items": {"1":75,"3":70,"5":60,"10":45,"20":40,"30":35,"40":32,"50":26,"100":16,"200":15}},
    "LSD Mario 250 µg": {"unit": "szt", "pic": "lsd.jpg", "items": {"10":15,"50":10,"100":9,"200":8,"300":7,"400":6,"500":5,"1000":4.8}},
    "HEROINA": {"unit": "g", "pic": "h.jpg", "items": {"1":200,"5":850,"10":1600,"25":3500,"50":5900,"100":10000}},
    "PIKO / METAMFETAMINA": {"unit": "g", "pic": "piko.jpg", "items": {"1":180,"5":160,"10":150,"25":130,"50":110,"100":90}},
    "2CB 25 mg": {"unit": "tab", "pic": "2cb.jpg", "items": {"10":220,"50":680,"100":1100,"500":3000,"1000":5300}},
    "Żywica THC 90 %": {"unit": "g", "pic": "zip2.jpg", "items": {"1":220,"2":350,"5":700,"10":1000,"50":3500,"100":6000}},
}

def build_shop_menu():
    kb = types.InlineKeyboardMarkup(row_width=2)
    for prod in PRODUCTS:
        kb.add(types.InlineKeyboardButton(prod, callback_data=f'shop_{prod}'))
    kb.add(types.InlineKeyboardButton("🛒 Mój koszyk", callback_data='show_cart'),
           types.InlineKeyboardButton("⬅️ Start", callback_data='back_to_start'))
    return kb

@bot.callback_query_handler(func=lambda call: call.data == 'shop')
def shop(call):
    text = "<b>Sklep – wybierz produkt, by dodać do koszyka:</b>"
    bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                             caption=text, parse_mode='HTML', reply_markup=build_shop_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith('shop_'))
def shop_product(call):
    prod = call.data.split('_',1)[1]
    unit = PRODUCTS[prod]["unit"]
    pic  = PRODUCTS[prod]["pic"]
    kb = types.InlineKeyboardMarkup(row_width=2)
    for g, price in PRODUCTS[prod]["items"].items():
        kb.add(types.InlineKeyboardButton(f"{g} {unit} – {price} zł", callback_data=f'add_{prod}_{g}_{price}'))
    kb.add(types.InlineKeyboardButton("⬅️ Sklep", callback_data='shop'))
    bot.send_photo(call.message.chat.id, open(pic,'rb'),
                   caption=f"<b>{prod}</b> – wybierz ilość:", parse_mode='HTML', reply_markup=kb)

# -------------------- MNOŻENIE CEN SZTUK --------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith('add_'))
def add_to_cart(call):
    _, prod, grams, price = call.data.split('_')
    uid = call.from_user.id
    if uid not in cart: cart[uid] = []
    qty = int(grams)
    unit_price = float(price)
    if PRODUCTS[prod]["unit"] in ("szt","tab"):
        total_price = qty * unit_price
    else:
        total_price = unit_price
    cart[uid].append({"prod": prod, "grams": grams, "price": total_price})
    bot.answer_callback_query(call.id, "✅ Dodano do koszyka", show_alert=False)

# -------------------- KOSZYK + OPCJE DOSTAWY --------------------
def cart_summary(uid):
    if uid not in cart or not cart[uid]: return "🛒 Koszyk pusty", 0
    lines = []; total = 0
    for idx, item in enumerate(cart[uid],1):
        lines.append(f"{idx}. {item['prod']} {item['grams']} – {item['price']} zł")
        total += item['price']
    return "\n".join(lines), total

@bot.callback_query_handler(func=lambda call: call.data == 'show_cart')
def show_cart(call):
    uid = call.from_user.id
    lines, total = cart_summary(uid)
    text = f"<b>Twój koszyk</b>\n\n{lines}\n\nSuma: <b>{total} zł</b>"
    kb = types.InlineKeyboardMarkup(row_width=2)
    if total >= MIN_ORDER:
        kb.add(types.InlineKeyboardButton("💳 Przejdź do kasy", callback_data='checkout'))
    else:
        text += f"\n\n❗ Minimum {MIN_ORDER} zł, brakuje <b>{MIN_ORDER-total} zł</b>"
    kb.add(types.InlineKeyboardButton("🗑️ Wyczyść koszyk", callback_data='clear_cart'),
           types.InlineKeyboardButton("⬅️ Start", callback_data='back_to_start'))
    bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                             caption=text, parse_mode='HTML', reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == 'clear_cart')
def clear_cart(call):
    uid = call.from_user.id; cart[uid] = []
    bot.answer_callback_query(call.id, "🗑️ Koszyk wyczyszczony")
    show_cart(call)

# -------------------- CHECKOUT Z WYBOREM DOSTAWY --------------------
@bot.callback_query_handler(func=lambda call: call.data == 'checkout')
def checkout(call):
    uid = call.from_user.id
    lines, total = cart_summary(uid)
    if total < MIN_ORDER:
        bot.answer_callback_query(call.id, f"❗ Minimum {MIN_ORDER} zł!", show_alert=True); return
    bal = get_saldo(uid)
    if bal < total:
        bot.answer_callback_query(call.id, "❗ Za małe saldo – doładuj!", show_alert=True); return
    text = (f"✅ <b>Zamówienie zrealizowane!</b>\n\n"
            f"Całkowita wartość: <b>{total} zł</b>\n"
            f"Pozostałe saldo: <code>{get_saldo(uid)} zł</code>")
    kb = types.InlineKeyboardMarkup(); kb.add(types.InlineKeyboardButton("⬅️ Start", callback_data='back_to_start'))
    bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                             caption=text, parse_mode='HTML', reply_markup=kb)

# -------------------- TOP-UP (BEZ ZMIAN) --------------------
CRYPTO_ADDRS = {
    'eth':  '0x319BbaA92e7Bb3A12787E5FE8287d16353c1A411',
    'tron': 'TYQZ5hZmnHr15BJYMqPQbGfSRJ9vKvoXjN',
    'btc':  'bc1qc63jdwksx78g94prggp7khx6k2qsy6s492duhg',
    'ltc':  'LQxzpqeDJqWPRnGz9W2Abtd4igFvNTJgcP',
    'ton':  'UQA99e-32uJkHREMcaQDNfRwm5GGcSr0edAV1_s8EKu6rlTu',
    'xmr':  '484JJVZcAwWRiDXh3ivw15Ei8T9bJ7K7X1T464Hit2Zc3EewyEtFui3G1oT4orUyeYaYTHKfTfDdmV3mhsyK4idyHvDobzM',
    'sol':  'MwCkeFFKPTRvJqGDYSwhsQCSLJUERSrQrHWZBmyLJ2B'
}

@bot.callback_query_handler(func=lambda call: call.data == 'top_up')
def top_up_start(call):
    text = "💵 <b>Ile złotych chcesz doładować?</b>\n\nNapisz tylko kwotę (np. 200):"
    kb = types.InlineKeyboardMarkup(); kb.add(types.InlineKeyboardButton("⬅️ Anuluj", callback_data='back_to_start'))
    bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                             caption=text, parse_mode='HTML', reply_markup=kb)
    bot.register_next_step_handler(call.message, top_up_amount)

def top_up_amount(message):
    try:
        amount = int(message.text)
        if amount <= 0: raise ValueError
    except:
        bot.reply_to(message, "❗ Nieprawidłowa kwota. Wpisz liczbę całkowitą > 0.")
        bot.register_next_step_handler(message, top_up_amount); return
    uid = message.from_user.id; top_up_cache[uid] = amount
    text = f"💵 <b>Doładuj saldo</b>\n\nKwota: <b>{amount} zł</b>\n\nWybierz metodę płatności:"
    kb = types.InlineKeyboardMarkup(row_width=2)
    methods = ['blik','eth','tron','btc','ltc','ton','xmr','sol']
    for m in methods:
        kb.add(types.InlineKeyboardButton(m.upper(), callback_data=f'topup_{m}_{amount}'))
    kb.row(types.InlineKeyboardButton("⬅️ Anuluj", callback_data='back_to_start'))
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith('topup_'))
def topup_payment(call):
    parts = call.data.split('_')
    method, amount = parts[1], float(parts[2])
    uid = call.from_user.id
    pay_id = str(uuid.uuid4())

    if method == 'blik':
        bot.answer_callback_query(call.id, "💈 BLIK – dostępne niedługo!", show_alert=True)
        return

    crypto_val = crypto_amount(amount, method)
    if crypto_val is None:
        bot.answer_callback_query(call.id, "❗ Błąd pobierania kursów walut", show_alert=True); return

    addr = CRYPTO_ADDRS.get(method, '-')
    text = (
        f"<b>Le Professionnel – doładowanie</b>\n"
        f"ID płatności: <code>{pay_id}</code>\n\n"
        f"💳 Metoda: <b>{method.upper()}</b>\n"
        f"📨 Adres: <code>{addr}</code>\n\n"
        f"💰 Kwota PLN: <b>{amount} zł</b>\n"
        f"💰 Kwota krypto: <b>{crypto_val:.6f} {method.upper()}</b>\n\n"
        f"⚠️ Wyślij dokładnie <b>{crypto_val:.6f} {method.upper()}</b> "
        f"(jednym przelewem) – inaczej środki przepadną!"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📋 Kopiuj dane", callback_data=f'copy_{method}'),
           types.InlineKeyboardButton("✅ Sprawdzam płatność",
                                      callback_data=f'topup_check_{pay_id}_{uid}_{amount}'))
    kb.row(types.InlineKeyboardButton("⬅️ Anuluj", callback_data='back_to_start'))
    bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                             caption=text, parse_mode='HTML', reply_markup=kb)

# -------------------- START --------------------
if __name__ == '__main__':
    print("Le Professionnel – gotowy do działania…")
    bot.infinity_polling(skip_pending=True)

