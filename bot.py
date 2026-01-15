import telebot
from telebot import types
import uuid, os, json, time, requests

TOKEN   = '7870656606:AAHZDaDqOA0d3FYUEKdmcXbjJIUhtNmCktQ'
ADMIN_ID = 6029446099
FALLBACK_PIC = 'leprofessionnel.jpg'
MAIN_CHAN   = 'https://t.me/+8VLpDp5-Cqc4OTI0 '
OPINIE_CHAN = 'https://t.me/c/3635144020/28 '
CONTACT_USER = '@LeProfessionnel_operator'

bot = telebot.TeleBot(TOKEN)
saldo_db, user_cache, top_up_cache, cart = {}, {}, {}, {}   # cart[uid] = list of dicts

MIN_ORDER = 300   # <-- nowy próg

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

# -------------------- menu główne --------------------
def build_main_menu():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("👤 Mój profil", callback_data='my_profile'),
        types.InlineKeyboardButton("💵 Doładuj saldo", callback_data='top_up'),
        types.InlineKeyboardButton("📋 Cennik / sklep", callback_data='price_list'),
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
            f"🛒 Minimalne zamówienie: <b>{MIN_ORDER} zł</b>")
    send_panel(message.chat.id, text, FALLBACK_PIC, build_main_menu())

# -------------------- PROFILE --------------------
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

# -------------------- KONTAKT --------------------
@bot.callback_query_handler(func=lambda call: call.data == 'contact')
def contact(call):
    text = f"📞 <b>Kontakt</b>\n\nNapisz do operatora:\n{CONTACT_USER}"
    kb = types.InlineKeyboardMarkup(); kb.add(types.InlineKeyboardButton("⬅️ Powrót", callback_data='back_to_start'))
    bot.send_message(call.message.chat.id, text, parse_mode='HTML', reply_markup=kb)

# -------------------- CENNIK + DODAWANIE DO KOSZYKA --------------------
PRODUCTS = {
    "Kokaina": {"unit": "g", "items": {"1":300,"5":300,"10":240,"25":200,"50":160,"100":140,"1000":125}},
    "Marihuana InDoor z USA": {"unit": "g", "items": {"5":32,"10":32,"25":30,"50":28,"100":26,"250":23,"500":22,"1000":21}},
    "MDMA tabletki 270 mg": {"unit": "szt", "items": {"10":20,"25":15,"50":12,"100":11,"250":9,"500":8,"1000":4,"5000":3}},
    "MDMA kryształ": {"unit": "g", "items": {"1":60,"5":50,"10":45,"25":43,"50":38,"100":30,"250":25,"500":22}},
    "Sucha amfetamina": {"unit": "g", "items": {"5":30,"10":25,"25":20,"50":16,"100":12,"250":10,"500":9}},
    "4MMC Kenzo 280 mg": {"unit": "szt", "items": {"50":550,"100":1000,"500":3000}},
    "3-CMC": {"unit": "g", "items": {"5":50,"10":28,"25":23,"50":21,"100":19,"250":18,"500":15,"1000":12}},
    "4-CMC": {"unit": "g", "items": {"5":50,"10":28,"25":23,"50":21,"100":19,"250":15,"500":13,"1000":11}},
    "TUCI / Różowa Kokaina": {"unit": "g", "items": {"1":140,"2":125,"3":120,"4":110,"5":100,"10":95,"20":90,"30":80,"40":75,"50":70,"100":65,"200":50,"500":45}},
    "KETAMINA – IGŁY": {"unit": "g", "items": {"1":75,"3":70,"5":60,"10":45,"20":40,"30":35,"40":32,"50":26,"100":16,"200":15}},
    "KETAMINA – KAMIENIE": {"unit": "g", "items": {"1":75,"3":70,"5":60,"10":45,"20":40,"30":35,"40":32,"50":26,"100":16,"200":15}},
    "LSD Mario 250 µg": {"unit": "szt", "items": {"10":15,"50":10,"100":9,"200":8,"300":7,"400":6,"500":5,"1000":4.8}},
    "HEROINA": {"unit": "g", "items": {"1":200,"5":850,"10":1600,"25":3500,"50":5900,"100":10000}},
    "PIKO / METAMFETAMINA": {"unit": "g", "items": {"1":180,"5":160,"10":150,"25":130,"50":110,"100":90}},
    "2CB 25 mg": {"unit": "tab", "items": {"10":220,"50":680,"100":1100,"500":3000,"1000":5300}},
    "Żywica THC 90 %": {"unit": "g", "items": {"1":220,"2":350,"5":700,"10":1000,"50":3500,"100":6000}},
}

def build_shop_menu():
    kb = types.InlineKeyboardMarkup(row_width=2)
    for prod in PRODUCTS:
        kb.add(types.InlineKeyboardButton(prod, callback_data=f'shop_{prod}'))
    kb.add(types.InlineKeyboardButton("🛒 Mój koszyk", callback_data='show_cart'),
           types.InlineKeyboardButton("⬅️ Powrót", callback_data='back_to_start'))
    return kb

@bot.callback_query_handler(func=lambda call: call.data == 'price_list')
def price_list(call):
    text = "<b>Cennik – wybierz produkt, by dodać do koszyka:</b>"
    bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                             caption=text, parse_mode='HTML', reply_markup=build_shop_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith('shop_'))
def shop_product(call):
    prod = call.data.split('_',1)[1]
    unit = PRODUCTS[prod]["unit"]
    kb = types.InlineKeyboardMarkup(row_width=2)
    for g, price in PRODUCTS[prod]["items"].items():
        kb.add(types.InlineKeyboardButton(f"{g} {unit} – {price} zł", callback_data=f'add_{prod}_{g}_{price}'))
    kb.add(types.InlineKeyboardButton("⬅️ Cennik", callback_data='price_list'))
    bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                             caption=f"<b>{prod}</b> – wybierz ilość:", parse_mode='HTML', reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith('add_'))
def add_to_cart(call):
    _, prod, grams, price = call.data.split('_')
    uid = call.from_user.id
    if uid not in cart: cart[uid] = []
    cart[uid].append({"prod": prod, "grams": grams, "price": float(price)})
    bot.answer_callback_query(call.id, "✅ Dodano do koszyka", show_alert=False)

# -------------------- KOSZYK --------------------
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
           types.InlineKeyboardButton("⬅️ Cennik", callback_data='price_list'))
    bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                             caption=text, parse_mode='HTML', reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == 'clear_cart')
def clear_cart(call):
    uid = call.from_user.id
    cart[uid] = []
    bot.answer_callback_query(call.id, "🗑️ Koszyk wyczyszczony")
    show_cart(call)

# -------------------- CHECKOUT --------------------
@bot.callback_query_handler(func=lambda call: call.data == 'checkout')
def checkout(call):
    uid = call.from_user.id
    lines, total = cart_summary(uid)
    if total < MIN_ORDER:
        bot.answer_callback_query(call.id, f"❗ Minimum {MIN_ORDER} zł!", show_alert=True); return
    bal = get_saldo(uid)
    if bal < total:
        bot.answer_callback_query(call.id, "❗ Za małe saldo – doładuj!", show_alert=True); return
    # zapisz zamówienie
    city = "Warszawa"   # placeholder – można rozbudować
    delivery = "InPost"
    crypto = "usdt"
    amount_crypto = crypto_amount(total, crypto) or 0
    for item in cart[uid]:
        save_user_order(uid, city, item['prod'], item['grams'], item['price'], crypto, amount_crypto, delivery)
    set_saldo(uid, bal - total)
    cart[uid] = []
    text = (f"✅ <b>Zamówienie zrealizowane!</b>\n\n"
            f"Całkowita wartość: <b>{total} zł</b>\n"
            f"Pozostałe saldo: <code>{get_saldo(uid)} zł</code>")
    kb = types.InlineKeyboardMarkup(); kb.add(types.InlineKeyboardButton("⬅️ Start", callback_data='back_to_start'))
    bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                             caption=text, parse_mode='HTML', reply_markup=kb)

# -------------------- TOP-UP (bez zmian) --------------------
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
    methods = ['tel','eth','tron','btc','ltc','ton','xmr','sol']
    for m in methods: kb.add(types.InlineKeyboardButton(m.upper(), callback_data=f'topup_{m}_{amount}'))
    kb.row(types.InlineKeyboardButton("⬅️ Anuluj", callback_data='back_to_start'))
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith('topup_'))
def topup_payment(call):
    parts = call.data.split('_'); method, amount = parts[1], float(parts[2])
    uid = call.from_user.id; pay_id = str(uuid.uuid4())
    crypto_val = crypto_amount(amount, method)
    if crypto_val is None:
        bot.answer_callback_query(call.id, "❗ Błąd pobierania kursów walut", show_alert=True); return
    min_dep = 0.00003 if method in ('btc','ltc','eth','tron') else 0.1
    addr = {'eth':'0x05e8c9e064d52C3F63b278B8120C53e49E70e26c','tron':'TVCeVXceuZtiQ9sZj3j4mDQ87Zw9NfvG3T','btc':'bc1qfwsz3ltfuxe33trezk0mdvsvcqx48d6250tda8','ltc':'LQfBdUpBfrUN5KYkZPmjPB1ieZcSSFXKaM','ton':'EQD4KZ1lXqCmRXXnY3L9fH9Y3L9fH9Y3L9fH9Y3L9fH9','xmr':'46yz1JJP9k8GTgN3Vb5mYYCJgQWgXJHmXJtF5yU7L9fH9Y3L9fH9Y3L9fH9','sol':'SoLWl1234567890abcdef'}.get(method,'-')
    text = (f"<b>Le Professionnel - doładowanie</b>\nID płatności: <code>{pay_id}</code>\n\n"
            f"💳 Metoda: <b>{method.upper()}</b>\n📨 Adres: <code>{addr}</code>\n\n"
            f"💰 Kwota: <b>{crypto_val:.6f} {method.upper()}</b>\n⏳ Czas: <b>29 minut</b>\n\n"
            f"⚠️ Wyślij dokładnie <b>{crypto_val:.6f}</b> (min. {min_dep}) jednym przelewem – inaczej środki przepadną!")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📋 Kopiuj dane", callback_data=f'copy_{method}'),
           types.InlineKeyboardButton("✅ Sprawdzam płatność", callback_data=f'topup_check_{pay_id}_{uid}_{amount}'))
    kb.row(types.InlineKeyboardButton("⬅️ Anuluj", callback_data='back_to_start'))
    bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                             caption=text, parse_mode='HTML', reply_markup=kb)

# -------------------- POWROTY --------------------
@bot.callback_query_handler(func=lambda call: call.data == 'back_to_start')
def back_to_start(call):
    start(call.message)
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

@bot.callback_query_handler(func=lambda call: call.data == 'channel_menu')
def channel_menu(call):
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                  reply_markup=build_channel_menu())

# -------------------- START --------------------
if __name__ == '__main__':
    print("Le Professionnel + koszyk + minimalne 300 zł działa…")
    bot.infinity_polling(skip_pending=True)
