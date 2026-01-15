import telebot
from telebot import types
import uuid, os, json, time, requests

TOKEN   = '7870656606:AAHZDaDqOA0d3FYUEKdmcXbjJIUhtNmCktQ'
ADMIN_ID = 6029446099
FALLBACK_PIC = 'leprofessionnel.jpg'

# ----------  LINKI DO KANAŁÓW  ----------
MAIN_CHAN   = 'https://t.me/+8VLpDp5-Cqc4OTI0'
OPINIE_CHAN = 'https://t.me/c/3635144020/28'
# ----------------------------------------

bot = telebot.TeleBot(TOKEN)
saldo_db, user_cache = {}, {}

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
    # jeśli podano zdjęcie i istnieje – wyślij je
    if photo_name and os.path.exists(photo_name):
        with open(photo_name, 'rb') as img:
            return bot.send_photo(chat_id, img, caption=text, parse_mode='HTML', reply_markup=kb)
    # jeśli podano zdjęcie, ale nie istnieje – wyślij fallback
    if photo_name:
        if os.path.exists(FALLBACK_PIC):
            with open(FALLBACK_PIC, 'rb') as img:
                return bot.send_photo(chat_id, img, caption=text, parse_mode='HTML', reply_markup=kb)
    # w pozostałych przypadkach – zwykła wiadomość
    return bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=kb)

# ----------  NOWY PRZYCISK „GRUPA TG”  ----------
def build_channel_menu():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("📣 Główny kanał", url=MAIN_CHAN),
           types.InlineKeyboardButton("⭐ Opinie", url=OPINIE_CHAN),
           types.InlineKeyboardButton("⬅️ Powrót", callback_data='back_to_cities'))
    return kb
# -----------------------------------------------

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id; bal = get_saldo(uid)
    text = (f"👋 <b>Le Professionnel</b> – witaj {message.from_user.first_name}!\n"
            f"💰 Saldo: <code>{bal} zł</code>\n"
            f"📦 <b>Wysyłka InPost/Poczta/DPD/Znaczek – tylko od 50 g (+40 zł)</b>\n\n"
            f"📍 <b>Wybierz miasto:</b>")
    kb = types.InlineKeyboardMarkup(row_width=2)
    cities = ["Wrocław", "Legnica", "Warszawa", "Katowice", "Gdańsk", "Kraków"]
    kb.add(*[types.InlineKeyboardButton(c, callback_data=f'city_{c}') for c in cities])
    kb.row(types.InlineKeyboardButton("📢 Grupa TG", callback_data='channel_menu'),
           types.InlineKeyboardButton("🏠 Home", callback_data='home'))
    send_panel(message.chat.id, text, kb=kb)

@bot.message_handler(commands=['saldo'])
def cmd_saldo(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, uid_s, kw_s = message.text.split(); uid, kw = int(uid_s), int(kw_s)
        set_saldo(uid, get_saldo(uid)+kw)
        bot.send_message(message.chat.id, f"✅ Saldo <code>{uid}</code> +{kw} zł → <b>{get_saldo(uid)} zł</b>", parse_mode='HTML')
    except: bot.reply_to(message, "❗ Użyj: <code>/saldo ID KWOTA</code>", parse_mode='HTML')

@bot.message_handler(commands=['reset'])
def reset_chat(message):
    chat_id = message.chat.id; bot.reply_to(message, "🧹 Rozpoczynam czyszczenie…")
    deleted = 0
    for i in range(message.message_id, message.message_id - 1000, -1):
        try: bot.delete_message(chat_id, i); deleted += 1
        except: continue
    bot.send_message(chat_id, f"✅ Usunięto {deleted} wiadomości. Czat czysty.")

@bot.callback_query_handler(func=lambda call: True)
def handle_inline(call):
    uid = call.from_user.id

    # -----------  NOWY HANDLER  -----------
    if call.data == 'channel_menu':
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=build_channel_menu())
        return
    # --------------------------------------

    if call.data.startswith('city_'):
        city = call.data.split('_',1)[1]; user_cache[uid] = {'city': city}
        bal = get_saldo(uid)
        text = (f"📍 <b>Miasto:</b> <code>{city}</code>  |  💰 Saldo: <code>{bal} zł</code>\n\n"
                "━━━━━━━━━━━━━━━\n📋 <b>CENNIK Le Professionnel</b>\n━━━━━━━━━━━━━━━\n\n<b>Wybierz kategorię:</b>")
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            types.InlineKeyboardButton("🌨️❄️ Czysta kokaina", callback_data=f'cat_kokaina_{city}'),
            types.InlineKeyboardButton("🌿🇺🇸 Marihuana InDoor z USA", callback_data=f'cat_weed_{city}'),
            types.InlineKeyboardButton("💊 3-CMC", callback_data=f'cat_3cmc_{city}'),
            types.InlineKeyboardButton("🔬 4-CMC", callback_data=f'cat_4cmc_{city}'),
            types.InlineKeyboardButton("💉 KETAMINA – IGŁY", callback_data=f'cat_ketaigly_{city}'),
            types.InlineKeyboardButton("🍬 KETAMINA – KAMUŁEK", callback_data=f'cat_ketakamulec_{city}'),
            types.InlineKeyboardButton("🍄 LSD Mario ‹3 250 µg", callback_data=f'cat_lsd_{city}'),
            types.InlineKeyboardButton("🧪 HEROINA", callback_data=f'cat_heroina_{city}'),
            types.InlineKeyboardButton("🍾 MDMA kryształ", callback_data=f'cat_mdma_krys_{city}'),
            types.InlineKeyboardButton("🍬 MDMA tabletki", callback_data=f'cat_mdma_tabs_{city}'),
            types.InlineKeyboardButton("💊 4MMC Kenzo 280mg", callback_data=f'cat_kenzo_{city}'),
            types.InlineKeyboardButton("🌸 TUCI / Różowa Kokaina", callback_data=f'cat_tuci_{city}'),
            types.InlineKeyboardButton("❄️ PIKO METH", callback_data=f'cat_piko_{city}'),
            types.InlineKeyboardButton("🟤 2CB 25mg", callback_data=f'cat_2cb_{city}'),
            types.InlineKeyboardButton("⚡ Amfa sucha", callback_data=f'cat_amfa_{city}'),
            types.InlineKeyboardButton("🍯 Żywica THC 90%", callback_data=f'cat_zywica_{city}')
        )
        kb.row(types.InlineKeyboardButton("⬅️ Powrót", callback_data='back_to_cities'), types.InlineKeyboardButton("🏠 Home", callback_data='home'))
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_panel(call.message.chat.id, text, kb=kb); return

    if call.data == 'back_to_cities':
        bal = get_saldo(uid)
        text = (f"👋 <b>Le Professionnel</b> – witaj {call.from_user.first_name}!\n"
                f"💰 Saldo: <code>{bal} zł</code>\n"
                f"📦 <b>Wysyłka InPost/Poczta/DPD/Znaczek – tylko od 50 g (+40 zł)</b>\n\n"
                f"📍 <b>Wybierz miasto:</b>")
        kb = types.InlineKeyboardMarkup(row_width=2)
        cities = ["Wrocław", "Legnica", "Warszawa", "Katowice", "Gdańsk", "Kraków"]
        kb.add(*[types.InlineKeyboardButton(c, callback_data=f'city_{c}') for c in cities])
        kb.row(types.InlineKeyboardButton("📢 Grupa TG", callback_data='channel_menu'),
               types.InlineKeyboardButton("🏠 Home", callback_data='home'))
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_panel(call.message.chat.id, text, kb=kb); return

    def build_gram_menu(city, prod_key, nice_name, photo, price_list):
        user_cache[uid] = {'city': city, 'prod': prod_key}
        text = f"{nice_name}\n📍 Miasto: {city}\n\n<b>Wybierz gramaturę:</b>"
        kb = types.InlineKeyboardMarkup(row_width=2)
        emoji = {'kokaina':'🧂','weed':'🌿','3cmc':'💊','4cmc':'🔬','ketaigly':'💉','ketakamulec':'🍬','lsd':'🍄','heroina':'💀','mdma_krys':'🍾','mdma_tabs':'🍬','kenzo':'💊','tuci':'🌸','piko':'❄️','2cb':'🟤','amfa':'⚡','zywica':'🍯'}[prod_key]
        for grams, price_per_g in price_list:
            total = grams * price_per_g
            kb.add(types.InlineKeyboardButton(f"{emoji} {grams}g – {total:,} PLN", callback_data=f'order_{prod_key}_{city}_{grams}_{total}'))
        kb.row(types.InlineKeyboardButton("⬅️ Powrót", callback_data=f'back_to_cats_{city}'), types.InlineKeyboardButton("🏠 Home", callback_data='home'))
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_panel(call.message.chat.id, text, photo, kb)

    def build_tab_menu(city, prod_key, nice_name, photo, price_list):
        user_cache[uid] = {'city': city, 'prod': prod_key}
        text = f"{nice_name}\n📍 Miasto: {city}\n\n<b>Wybierz ilość tabletek:</b>"
        kb = types.InlineKeyboardMarkup(row_width=2)
        emoji = {'mdma_tabs':'🍬','kenzo':'💊','2cb':'🟤'}[prod_key]
        for tabs, price_per_tab in price_list:
            total = tabs * price_per_tab
            kb.add(types.InlineKeyboardButton(f"{emoji} {tabs} szt – {total:,} PLN", callback_data=f'order_{prod_key}_{city}_{tabs}_{total}'))
        kb.row(types.InlineKeyboardButton("⬅️ Powrót", callback_data=f'back_to_cats_{city}'), types.InlineKeyboardButton("🏠 Home", callback_data='home'))
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_panel(call.message.chat.id, text, photo, kb)

    if call.data.startswith('cat_kokaina_'):
        city = call.data.split('_',2)[2]
        build_gram_menu(city, 'kokaina', '❄️ <b>Czysta kokaina</b>', 'koko.jpg', [(1,300),(5,300),(10,240),(25,200),(50,160),(100,140),(1000,125)])
    elif call.data.startswith('cat_weed_'):
        city = call.data.split('_',2)[2]
        build_gram_menu(city, 'weed', '🌿 <b>Marihuana InDoor z USA 🇺🇸</b>', 'zip.jpg', [(5,32),(10,32),(25,30),(50,28),(100,26),(250,23),(500,22),(1000,21)])
    elif call.data.startswith('cat_3cmc_'):
        city = call.data.split('_',2)[2]
        build_gram_menu(city, '3cmc', '💊 <b>3-CMC</b>', '3cmc.jpg', [(5,50),(10,28),(25,23),(50,21),(100,19),(250,18),(500,15),(1000,12)])
    elif call.data.startswith('cat_4cmc_'):
        city = call.data.split('_',2)[2]
        build_gram_menu(city, '4cmc', '🔬 <b>4-CMC</b>', '4cmc.jpg', [(5,50),(10,28),(25,23),(50,21),(100,19),(250,15),(500,13),(1000,11)])
    elif call.data.startswith('cat_ketaigly_'):
        city = call.data.split('_',2)[2]
        build_gram_menu(city, 'ketaigly', '💉 <b>KETAMINA – IGŁY</b>', 'ketaigly.jpg', [(1,75),(3,70),(5,60),(10,45),(20,40),(30,35),(40,32),(50,26),(100,16),(200,15)])
    elif call.data.startswith('cat_ketakamulec_'):
        city = call.data.split('_',2)[2]
        build_gram_menu(city, 'ketakamulec', '🍬 <b>KETAMINA – KAMUŁEK</b>', 'ketakamulec.jpg', [(1,75),(3,70),(5,60),(10,45),(20,40),(30,35),(40,32),(50,26),(100,16),(200,15)])
    elif call.data.startswith('cat_lsd_'):
        city = call.data.split('_',2)[2]
        build_gram_menu(city, 'lsd', '🍄 <b>LSD Mario ‹3 250 µg</b>', 'lsd.jpg', [(10,15),(50,10),(100,9),(200,8),(300,7),(400,6),(500,5),(1000,4.8)])
    elif call.data.startswith('cat_heroina_'):
        city = call.data.split('_',2)[2]
        build_gram_menu(city, 'heroina', '🧪 <b>HEROINA</b>', 'h.jpg', [(1,200),(5,850),(10,1600),(25,3500),(50,5900),(100,10000)])
    elif call.data.startswith('cat_mdma_krys_'):
        city = call.data.split('_',3)[3]
        build_gram_menu(city, 'mdma_krys', '🍾 <b>MDMA szampański kryształ</b>', 'mdma2.jpg', [(1,60),(5,50),(10,45),(25,43),(50,38),(100,30),(250,25),(500,22)])
    elif call.data.startswith('cat_mdma_tabs_'):
        city = call.data.split('_',3)[3]
        build_tab_menu(city, 'mdma_tabs', '🍬 <b>MDMA tabletki</b>', 'mdma.jpg', [(10,20),(25,15),(50,12),(100,11),(250,9),(500,8),(1000,4),(5000,3)])
    elif call.data.startswith('cat_kenzo_'):
        city = call.data.split('_',2)[2]
        build_tab_menu(city, 'kenzo', '💊 <b>4MMC Kenzo 280mg</b>', 'kenzo.jpg', [(50,11),(100,10),(500,6)])
    elif call.data.startswith('cat_tuci_'):
        city = call.data.split('_',2)[2]
        build_gram_menu(city, 'tuci', '🌸 <b>TUCI / Różowa Kokaina</b>', 'TUCI.jpg', [(1,140),(2,125),(3,120),(4,110),(5,100),(10,95),(20,90),(30,80),(40,75),(50,70),(100,65),(200,50),(500,45)])
    elif call.data.startswith('cat_piko_'):
        city = call.data.split('_',2)[2]
        build_gram_menu(city, 'piko', '❄️ <b>PIKO METH</b>', 'piko.jpg', [(1,180),(5,160),(10,150),(25,130),(50,110),(100,90)])
    elif call.data.startswith('cat_2cb_'):
        city = call.data.split('_',2)[2]
        build_tab_menu(city, '2cb', '🟤 <b>2CB 25mg</b>', '2cb.jpg', [(10,22),(50,13.6),(100,11),(500,6),(1000,5.3)])
    elif call.data.startswith('cat_amfa_'):
        city = call.data.split('_',2)[2]
        build_gram_menu(city, 'amfa', '⚡ <b>Sucha amfetamina</b>', 'amfa.jpg', [(5,30),(10,25),(25,20),(50,16),(100,12),(250,10),(500,9)])
    elif call.data.startswith('cat_zywica_'):
        city = call.data.split('_',2)[2]
        build_gram_menu(city, 'zywica', '🍯 <b>Żywica THC 90%</b>', 'zip2.jpg', [(1,220),(2,175),(5,140),(10,100),(50,70),(100,60)])

    # --- WYBÓR METODY DOSTAWY ---
    elif call.data.startswith('order_'):
        parts = call.data.split('_')
        prod, city, grams, base_price = parts[1], parts[2], float(parts[3]), float(parts[4])
        user_cache[uid] = {'prod': prod, 'city': city, 'grams': grams, 'base_price': base_price}
        bal = get_saldo(uid)
        if bal < base_price:
            bot.answer_callback_query(call.id, f"❗ Brak środków – potrzeba {base_price:.2f} zł", show_alert=True); return
        text = (f"<b>Le Professionnel</b>\n"
                f"📦 Towar: <b>{prod.upper()} {grams} g</b>\n"
                f"📍 Miasto: {city}\n"
                f"💰 Do zapłaty: <b>{base_price:.2f} zł</b>\n\n"
                f"<b>Wybierz metodę dostawy:</b>")
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton("🕳️ Dead drop", callback_data=f'delivery_dead_{prod}_{city}_{grams}_{base_price}'))
        if grams > 50:
            kb.add(
                types.InlineKeyboardButton("📦 InPost (+40 zł)", callback_data=f'delivery_inpost_{prod}_{city}_{grams}_{base_price}'),
                types.InlineKeyboardButton("📮 Poczta (+40 zł)", callback_data=f'delivery_poczta_{prod}_{city}_{grams}_{base_price}'),
                types.InlineKeyboardButton("🚚 DPD (+40 zł)", callback_data=f'delivery_dpd_{prod}_{city}_{grams}_{base_price}'),
                types.InlineKeyboardButton("✉️ Znaczek Pocztowy (+40 zł)", callback_data=f'delivery_znaczek_{prod}_{city}_{grams}_{base_price}')
            )
        kb.row(types.InlineKeyboardButton("⬅️ Powrót", callback_data=f'back_to_cats_{city}'), types.InlineKeyboardButton("🏠 Home", callback_data='home'))
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_panel(call.message.chat.id, text, kb=kb)

    # --- WYBÓR PŁATNOŚCI ---
    elif call.data.startswith('delivery_'):
        _, delivery_raw, prod, city, grams, base_price = call.data.split('_')
        delivery_map = {'dead':'Dead drop','inpost':'InPost','poczta':'Poczta','dpd':'DPD','znaczek':'Znaczek Pocztowy'}
        delivery_name = delivery_map[delivery_raw]
        delivery_fee = 0 if delivery_raw == 'dead' else 40
        final_price = float(base_price) + delivery_fee
        user_cache[uid]['delivery'] = delivery_name
        user_cache[uid]['final_price'] = final_price
        text = (f"<b>Le Professionnel</b>\n"
                f"📦 Towar: <b>{prod.upper()} {grams} g</b>\n"
                f"📍 Miasto: {city}\n"
                f"📦 Dostawa: <b>{delivery_name}</b>\n"
                f"💰 Do zapłaty: <b>{final_price:.2f} zł</b>\n\n"
                f"Wybierz metodę płatności:")
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("📞 BLIK / przelew", callback_data=f'pay_tel_{prod}_{city}_{final_price}_{delivery_raw}'),
            types.InlineKeyboardButton("ETH / USDT", callback_data=f'pay_eth_{prod}_{city}_{final_price}_{delivery_raw}'),
            types.InlineKeyboardButton("USDT (TRON)", callback_data=f'pay_tron_{prod}_{city}_{final_price}_{delivery_raw}'),
            types.InlineKeyboardButton("BTC", callback_data=f'pay_btc_{prod}_{city}_{final_price}_{delivery_raw}'),
            types.InlineKeyboardButton("LTC", callback_data=f'pay_ltc_{prod}_{city}_{final_price}_{delivery_raw}'),
            types.InlineKeyboardButton("TON", callback_data=f'pay_ton_{prod}_{city}_{final_price}_{delivery_raw}'),
            types.InlineKeyboardButton("XMR Monero", callback_data=f'pay_xmr_{prod}_{city}_{final_price}_{delivery_raw}'),
            types.InlineKeyboardButton("SOL Solana", callback_data=f'pay_sol_{prod}_{city}_{final_price}_{delivery_raw}')
        )
        kb.row(types.InlineKeyboardButton("⬅️ Powrót", callback_data=f'order_{prod}_{city}_{grams}_{base_price}'), types.InlineKeyboardButton("🏠 Home", callback_data='home'))
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_panel(call.message.chat.id, text, kb=kb)

    # --- EKRAN PŁATNOŚCI ---
    elif call.data.startswith('pay_'):
        parts = call.data.split('_')
        method, prod, city, final_price, delivery_raw = parts[1], parts[2], parts[3], float(parts[4]), parts[5]
        pay_id = str(uuid.uuid4())
        crypto_val = crypto_amount(final_price, method)
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
        delivery_name = {'dead':'Dead drop','inpost':'InPost','poczta':'Poczta','dpd':'DPD','znaczek':'Znaczek Pocztowy'}.get(delivery_raw,'-')
        text = (f"<b>Le Professionnel</b>\n"
                f"ID płatności: <code>{pay_id}</code>\n\n"
                f"💳 Metoda: <b>{method.upper()}</b>\n"
                f"📨 Adres: <code>{addr}</code>\n\n"
                f"💰 Kwota do zapłaty: <b>{crypto_val:.6f} {method.upper()}</b>\n"
                f"⏳ Czas: <b>29 minut</b>\n\n"
                f"⚠️ Wyślij dokładnie <b>{crypto_val:.6f}</b> (min. {min_dep}) jednym przelewem – inaczej środki przepadną!")
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton("📋 Kopiuj dane", callback_data=f'copy_{method}'), types.InlineKeyboardButton("✅ Sprawdzam płatność", callback_data=f'check_{pay_id}'))
        kb.row(types.InlineKeyboardButton("⬅️ Powrót", callback_data=f'delivery_{delivery_raw}_{prod}_{city}_{user_cache[uid]["grams"]}_{user_cache[uid]["base_price"]}'), types.InlineKeyboardButton("🏠 Home", callback_data='home'))
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_panel(call.message.chat.id, text, kb=kb)

        grams = user_cache[uid]['grams']
        save_user_order(uid, city, prod, grams, final_price, method, crypto_val, delivery_name)

    elif call.data in ('contact_ship', 'contact_inpost'):
        bot.answer_callback_query(call.id)
        session_id = "051cecec3fc6e34985eab778bf8b6692ae0fa8f388ea27fe4479a0b5ef468dba56"
        text = (f"<b>Le Professionnel - Kontakt</b>\n\n"
                f"📞 Session ID:\n<code>{session_id}</code>\n\n"
                f"Skopiuj powyższy Session ID i skontaktuj się przez Session Messenger.")
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')

    elif call.data == 'home':
        for i in range(call.message.message_id, 0, -1):
            try: bot.delete_message(call.message.chat.id, i)
            except: break
        start(call.message)

    elif call.data.startswith('copy_'):
        what = call.data.split('_',1)[1]
        msg = ("✅ Skopiowano numer: 503233443 – wklej w banku / BLIK-u!" if what == 'tel' else f"✅ Skopiowano adres {what.upper()} – wklej w portfelu!")
        bot.answer_callback_query(call.id, msg, show_alert=True)

    elif call.data.startswith('check_'):
        bot.answer_callback_query(call.id, "⏳ Sprawdzam… funkcja wkrótce!", show_alert=True)

if __name__ == '__main__':
    print("Le Professionnel (poprawione przyciski + 2 linki TG) działa…")
    bot.infinity_polling(skip_pending=True)
