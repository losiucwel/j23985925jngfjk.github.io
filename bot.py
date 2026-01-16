import telebot
from telebot import types
import uuid, os, json, time

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

# -------------------- STAŁE KURSY KRYPTO (PLN) --------------------
CRYPTO_RATES = {
    'btc': 346306.40,
    'eth': 11950.23,
    'ltc': 271.42,
    'tron': 0.45,
    'ton': 20.0,
    'xmr': 2310.87,
    'sol': 512.0,
    'usdt': 3.49
}

# -------------------- pomocnicze --------------------
def get_saldo(uid): return saldo_db.get(uid, 0)
def set_saldo(uid, v): saldo_db[uid] = max(0, v)

def crypto_amount(pln, crypto):
    return pln / CRYPTO_RATES.get(crypto, 1)

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
    try:
        if photo_name and os.path.exists(photo_name):
            with open(photo_name, 'rb') as img:
                return bot.send_photo(chat_id, img, caption=text, parse_mode='HTML', reply_markup=kb)
        if os.path.exists(FALLBACK_PIC):
            with open(FALLBACK_PIC, 'rb') as img:
                return bot.send_photo(chat_id, img, caption=text, parse_mode='HTML', reply_markup=kb)
        return bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=kb)
    except Exception as e:
        print("send_panel error:", e)
        return bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=kb)

def build_main_menu():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("👤 Mój profil", callback_data='my_profile'),
        types.InlineKeyboardButton("💵 Doładuj saldo", callback_data='top_up'),
        types.InlineKeyboardButton("📋 Cennik (info)", callback_data='price_list_info'),
        types.InlineKeyboardButton("🛍️ Sklep (dodaj do koszyka)", callback_data='shop'),
        types.InlineKeyboardButton("🏙️ Miasta – dostępność", callback_data='cities'),
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
            f"📦 Dead drop dostępny!\n\n"
            "<blockquote>Jesteśmy dostępni w miastach:\n"
            "• Warszawa\n• Gdańsk\n• Kraków\n• Wrocław\n• Legnica\n• Katowice</blockquote>")
    send_panel(message.chat.id, text, FALLBACK_PIC, build_main_menu())

# -------------------- KOMENDA /saldo (tylko ADMIN) --------------------
@bot.message_handler(commands=['saldo'])
def cmd_saldo(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Brak uprawnień.")
        return
    try:
        args = message.text.split()
        uid = int(args[1])
        new_val = float(args[2])
        set_saldo(uid, new_val)
        bot.reply_to(message, f"✅ Saldo użytkownika {uid} ustawione na {new_val} zł.")
    except:
        bot.reply_to(message, "❗ Użyj: <code>/saldo UID kwota</code>", parse_mode='HTML')

# -------------------- PRODUKTY (ORYGINALNE NAZWY) --------------------
PRODUCTS = {
    # --- MNOŻONE przez ilość (szt/tab) ---
    "MDMA tabletki 270 mg": {"unit": "szt", "pic": "mdma.jpg", "items": {"10":20,"25":15,"50":12,"100":11,"250":9,"500":8,"1000":4,"5000":3}},
    "4MMC Kenzo 280 mg": {"unit": "szt", "pic": "kenzo.jpg", "items": {"50":550,"100":1000,"500":3000}},
    "2CB 25 mg": {"unit": "tab", "pic": "2cb.jpg", "items": {"10":220,"50":680,"100":1100,"500":3000,"1000":5300}},
    "LSD Mario 250 µg": {"unit": "szt", "pic": "lsd.jpg", "items": {"10":15,"50":10,"100":9,"200":8,"300":7,"400":6,"500":5,"1000":4.8}},

    # --- MNOŻONE przez gram (g) – DO POPRAWY PRZEZ CIEBIE/CLAUDE ---
    "Kokaina": {"unit": "g", "pic": "koko.jpg", "items": {"1":300,"5":300,"10":240,"25":200,"50":160,"100":140,"1000":125}},
    "Marihuana InDoor z USA": {"unit": "g", "pic": "zip.jpg", "items": {"5":32,"10":32,"25":30,"50":28,"100":26,"250":23,"500":22,"1000":21}},
    "MDMA kryształ": {"unit": "g", "pic": "mdma2.jpg", "items": {"1":60,"5":50,"10":45,"25":43,"50":38,"100":30,"250":25,"500":22}},
    "Sucha amfetamina": {"unit": "g", "pic": "amfa.jpg", "items": {"5":30,"10":25,"25":20,"50":16,"100":12,"250":10,"500":9}},
    "3-CMC": {"unit": "g", "pic": "3cmc.jpg", "items": {"5":50,"10":28,"25":23,"50":21,"100":19,"250":18,"500":15,"1000":12}},
    "4-CMC": {"unit": "g", "pic": "4cmc.jpg", "items": {"5":50,"10":28,"25":23,"50":21,"100":19,"250":15,"500":13,"1000":11}},
    "TUCI / Różowa Kokaina": {"unit": "g", "pic": "TUCI.jpg", "items": {"1":140,"2":125,"3":120,"4":110,"5":100,"10":95,"20":90,"30":80,"40":75,"50":70,"100":65,"200":50,"500":45}},
    "KETAMINA – IGŁY": {"unit": "g", "pic": "ketaigly.jpg", "items": {"1":75,"3":70,"5":60,"10":45,"20":40,"30":35,"40":32,"50":26,"100":16,"200":15}},
    "KETAMINA – KAMIENIE": {"unit": "g", "pic": "ketakamulec.jpg", "items": {"1":75,"3":70,"5":60,"10":45,"20":40,"30":35,"40":32,"50":26,"100":16,"200":15}},
    "HEROINA": {"unit": "g", "pic": "h.jpg", "items": {"1":200,"5":850,"10":1600,"25":3500,"50":5900,"100":10000}},
    "PIKO / METAMFETAMINA": {"unit": "g", "pic": "piko.jpg", "items": {"1":180,"5":160,"10":150,"25":130,"50":110,"100":90}},
    "Żywica THC 90 %": {"unit": "g", "pic": "zip2.jpg", "items": {"1":220,"2":350,"5":700,"10":1000,"50":3500,"100":6000}},
}

# -------------------- STATUS DOSTĘPNOŚCI (PO PRODUCTS) --------------------
PRODUCT_STATUS = {prod: True for prod in PRODUCTS}  # ✅ wszystko dostępne

# -------------------- MIASTA – DOSTĘPNOŚĆ --------------------
CITIES = {
    "Warszawa": {"callback": "city_warszawa"},
    "Gdańsk": {"callback": "city_gdansk"},
    "Kraków": {"callback": "city_krakow"},
    "Wrocław": {"callback": "city_wroclaw"},
    "Legnica": {"callback": "city_legnica"},
    "Katowice": {"callback": "city_katowice"},
}

def build_cities_menu():
    kb = types.InlineKeyboardMarkup(row_width=2)
    for city, data in CITIES.items():
        kb.add(types.InlineKeyboardButton(city, callback_data=data["callback"]))
    kb.add(types.InlineKeyboardButton("⬅️ Powrót", callback_data='back_to_start'))
    return kb

@bot.callback_query_handler(func=lambda call: call.data == 'cities')
def cities_menu(call):
    text = "<b>Wybierz miasto – sprawdzamy dostępność towaru:</b>"
    bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                             caption=text, parse_mode='HTML', reply_markup=build_cities_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith('city_'))
def city_stock(call):
    city = call.data.replace('city_', '').title()
    lines = [f"<b>🏙️ {city} – dostępność towaru:</b>\n"]
    for prod, info in PRODUCTS.items():
        status = "✅" if PRODUCT_STATUS.get(prod, True) else "❌"
        lines.append(f"{status} {prod}")
    text = "\n".join(lines)
    kb = types.InlineKeyboardMarkup(); kb.add(types.InlineKeyboardButton("⬅️ Miasta", callback_data='cities'))
    bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                             caption=text, parse_mode='HTML', reply_markup=kb)

# -------------------- PROFILE / KONTAKT / POWROTY --------------------
@bot.callback_query_handler(func=lambda call: call.data == 'my_profile')
def my_profile(call):
    uid = call.from_user.id; bal = get_saldo(uid); orders = count_user_orders(uid)
    text = (f"👤 <b>Twój profil</b>\n\n"
            f"🆔 ID: <code>{uid}</code>\n"
            f"💰 Saldo: <code>{bal} zł</code>\n"
            f"📦 Zamówienia: <b>{orders}</b>")
    kb = types.InlineKeyboardMarkup(); kb.add(types.InlineKeyboardButton("⬅️ Powrót", callback_data='back_to_start'))
    try:
        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                 caption=text, parse_mode='HTML', reply_markup=kb)
    except:
        bot.send_message(call.message.chat.id, text, parse_mode='HTML', reply_markup=kb)

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

# -------------------- CENNIK --------------------
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

# -------------------- SKLEP --------------------
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

# -------------------- MNOŻENIE CEN – GWARANCJA --------------------
@bot.callback_query_handler(func=lambda call:
