import asyncio
import sqlite3
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# --- 1. НАЛАШТУВАННЯ ---
# ВПИШИ СВОЇ ID СЮДИ: [111, 222]
API_TOKEN = '8641455876:AAEt-VQa2dxRQZlOGhd1krymhZ6xzPm6yVY'
ADMINS = [5965241633,1604690472] # Заміни на свої реальні ID

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class AdminStates(StatesGroup):
    waiting_for_hw_text = State()

# --- 2. БАЗА ДАНИХ ---
def init_db():
    conn = sqlite3.connect('group_bot.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS homework (subject TEXT PRIMARY KEY, task TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS online_links (subject TEXT PRIMARY KEY, link TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cursor.execute('INSERT OR IGNORE INTO settings VALUES ("week_type", "Знаменник")')
    
    links = [
        ("Грунтознавство", "https://us04web.zoom.us/j/78495547395?pwd=G7fd6KedJHhcfiSOfYlfW7Ca6l4Vk1.1"),
        ("Ботаніка", "https://us05web.zoom.us/j/4317764346?pwd=Ylp6M3lhZG9Fd0xoc0RVdEZTME9Idz09&omn=87697232433"),
        ("Філософія", "https://us04web.zoom.us/j/71119670230?pwd=U26kO6oupnE0iIjZFQiyIFC0doO7g2.1"),
        ("Фізичне виховання", "https://us04web.zoom.us/j/2545730297?pwd=eipmanYl5ybFS6e9GVl536aCvXLOw0.1"),
        ("Сільськогосподарські машини", "https://us04web.zoom.us/j/3572859845?pwd=dCbsuQi0zFa4LZFtcQYPP92FrTBcF4.1"),
        ("Агрометеорологія", "https://nubip-edu-ua.zoom.us/j/9587441507?pwd=VW1GSVR0ejRzRzJ6aWp3OHhjeWphdz09"),
        ("Правова культура", "https://meet.google.com/tro-apjn-qxa"),
        ("Агроекологія", "https://meet.google.com/gbg-yotb-kvx?hs=224"),
        ("Агроекологія ПРАКТИКА", "https://us05web.zoom.us/j/88065987617?pwd=dHdwK3pOMFNiYTFJZHQwdzI5cE5kdz09"),
        ("Грунтознавство ЛЕКЦІЯ", "https://us04web.zoom.us/j/73085482273?pwd=KH9KmE2jAK4zTGLtNqz6KOBIWdQ1kS.1")
    ]
    cursor.executemany("INSERT OR REPLACE INTO online_links VALUES (?, ?)", links)
    conn.commit()
    conn.close()

def get_week_type():
    conn = sqlite3.connect('group_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = "week_type"')
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else "Знаменник"

# --- 3. РОЗКЛАД ---
SCHEDULE = {
    "Понеділок": {
        "Знаменник": "1. 08:30 — Грунтознавство (к.2, ауд. 33)\n2. 10:10 — Грунтознавство (к.2, ауд. 40)\n3. 11:50 — Ботаніка (к.1, ауд. 111)\n4. 13:30 — Ботаніка (к.1, ауд. 111)",
        "Чисельник": "2. 10:10 — Сільськогосподарські машини (к.7а, ауд. 102)\n3. 11:50 — Ботаніка (к.1, ауд. 111)\n4. 13:30 — Ботаніка (к.1, ауд. 111)"
    },
    "Вівторок": {
        "Загальне": "1. 10:10 — Філософія (к.4, ауд. 57к)\n2. 11:50 — Фізичне виховання\n3. 13:30 — Сільськогосподарські машини (к.7а, ауд. 103)"
    },
    "Середа": {
        "Знаменник": "2. 10:10 — Грунтознавство (к.2, ауд. 53)\n3. 11:50 — Ботаніка (к.2, ауд. 15)",
        "Чисельник": "2. 10:10 — Грунтознавство (к.2, ауд. 53)\n3. 11:50 — Ботаніка (к.2, ауд. 15)\n4. 13:30 — Ботаніка (к.2, ауд. 15)"
    },
    "Четвер": {
        "Загальне": "1. 08:30 — Агрометеорологія (к.4, ауд. 37)",
        "Чисельник": "2. 10:10 — Агроекологія (к.2, ауд. 15)\n3. 11:50 — Правова культура (к.2, ауд. 15)",
        "Знаменник": "2. 10:10 — Філософія (к.2, ауд. 36)\n3. 11:50 — Правова культура (к.2, ауд. 36)"
    },
    "П'ятниця": {
        "Знаменник": "1. 08:30 — Сільськогосподарські машини (к.11, ауд. 136)\n2. 10:10 — Сільськогосподарські машини\n3. 11:50 — Агрометеорологія",
        "Чисельник": "2. 10:10 — Сільськогосподарські машини (к.11, ауд. 136)\n3. 11:50 — Агрометеорологія\n4. 13:30 — Агроекологія (к.4, ауд. 74)"
    }
}

# --- 4. ХЕНДЛЕРИ ---

@dp.message(Command("start"))
async def start(message: types.Message):
    is_admin = message.from_user.id in ADMINS
    kb = [
        [KeyboardButton(text="🏫 Очний розклад"), KeyboardButton(text="🌐 Онлайн заняття")],
        [KeyboardButton(text="📝 Домашнє завдання"), KeyboardButton(text="📅 Який тиждень?")]
    ]
    if is_admin: kb.append([KeyboardButton(text="⚙️ Адмінка")])
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer(f"Привіт! Твій ID: `{message.from_user.id}`\nСтатус: {'Адмін' if is_admin else 'Студент'}", 
                         reply_markup=keyboard, parse_mode="Markdown")

# ПЕРЕГЛЯД ДЗ (ДЛЯ ВСІХ)
@dp.message(F.text == "📝 Домашнє завдання")
async def show_hw(message: types.Message):
    conn = sqlite3.connect('group_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM homework")
    hw_list = cursor.fetchall()
    conn.close()
    
    if not hw_list:
        return await message.answer("Завдань немає! Відпочивай. 🌴")
    
    res = "📝 **АКТУАЛЬНЕ ДЗ:**\n\n"
    for sub, task in hw_list:
        res += f"🔹 **{sub}**:\n{task}\n\n"
    await message.answer(res, parse_mode="Markdown")

# АДМІН-ПАНЕЛЬ
@dp.message(F.text == "⚙️ Адмінка")
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMINS: return
    kb = [
        [InlineKeyboardButton(text="🔄 Чисельник", callback_data="set_week_Чисельник"), InlineKeyboardButton(text="🔄 Знаменник", callback_data="set_week_Знаменник")],
        [InlineKeyboardButton(text="📝 Редагувати ДЗ", callback_data="admin_edit_hw")]
    ]
    await message.answer("⚙️ ПАНЕЛЬ КЕРУВАННЯ", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("set_week_"))
async def set_week_callback(callback: types.CallbackQuery):
    new_type = callback.data.replace("set_week_", "")
    conn = sqlite3.connect('group_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE settings SET value = ? WHERE key = "week_type"', (new_type,))
    conn.commit()
    conn.close()
    await callback.message.answer(f"✅ Встановлено: {new_type}")
    await callback.answer()

@dp.callback_query(F.data == "admin_edit_hw")
async def start_edit_hw(callback: types.CallbackQuery):
    subjects = ["Грунтознавство", "Ботаніка", "Філософія", "Сільгосп машини", "Агрометеорологія", "Правова культура", "Агроекологія"]
    kb = [[InlineKeyboardButton(text=s, callback_data=f"edit_hw_{s}")] for s in subjects]
    await callback.message.edit_text("Обери предмет для ДЗ:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("edit_hw_"))
async def get_subject_for_hw(callback: types.CallbackQuery, state: FSMContext):
    subject = callback.data.replace("edit_hw_", "")
    await state.update_data(curr_sub=subject)
    await state.set_state(AdminStates.waiting_for_hw_text)
    await callback.message.answer(f"Напиши ДЗ для **{subject}** (або '-' для видалення):")
    await callback.answer()

@dp.message(AdminStates.waiting_for_hw_text)
async def save_hw(message: types.Message, state: FSMContext):
    data = await state.get_data()
    sub = data['curr_sub']
    conn = sqlite3.connect('group_bot.db')
    cursor = conn.cursor()
    if message.text == "-":
        cursor.execute("DELETE FROM homework WHERE subject = ?", (sub,))
    else:
        cursor.execute("INSERT OR REPLACE INTO homework VALUES (?, ?)", (sub, message.text))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer(f"✅ Оновлено!")

@dp.message(F.text == "🌐 Онлайн заняття")
async def show_online(message: types.Message):
    week_type = get_week_type()
    days = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]
    curr_day = days[datetime.now().weekday()]
    if curr_day in ["Субота", "Неділя"]: return await message.answer("Вихідний! 😊")

    TEACHERS = {"Грунтознавство": "Карабач К.С.", "Ботаніка": "Меженська Л.О.", "Філософія": "Кичкирук Т.В.", "Фізичне виховання": "Бербеничук В.Ю.", "Сільськогосподарські машини": "Вечера О.М.", "Агрометеорологія": "Завгородня С.В.", "Правова культура": "Попова О.В.", "Агроекологія": "Міняйло А."}

    conn = sqlite3.connect('group_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM online_links")
    links_dict = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()

    day_data = SCHEDULE.get(curr_day, {})
    res_text = f"🌐 **ОНЛАЙН РОЗКЛАД**\n📅 {curr_day} ({week_type})\n────────────────────\n"
    kb = []
    
    lessons = []
    if "Загальне" in day_data: lessons.extend(day_data["Загальне"].split('\n'))
    if week_type in day_data: lessons.extend(day_data[week_type].split('\n'))

    for lesson in lessons:
        clean = lesson.split('(')[0].strip()
        found_sub = next((s for s in TEACHERS if s.lower() in clean.lower()), None)
        if found_sub:
            link = links_dict.get("Агроекологія ПРАКТИКА" if "агроекологія" in clean.lower() and "13:30" in clean in clean else found_sub, "#")
            res_text += f"📘 **{clean}**\n👨‍🏫 {TEACHERS[found_sub]}\n\n"
            if link != "#": kb.append([InlineKeyboardButton(text=f"🔗 Приєднатися: {found_sub}", url=link)])
    
    await message.answer(res_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@dp.message(F.text == "🏫 Очний розклад")
async def show_offline(message: types.Message):
    week_type = get_week_type()
    days = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]
    curr_day = days[datetime.now().weekday()]
    if curr_day in ["Субота", "Неділя"]: return await message.answer("Вихідний! 😊")
    day_data = SCHEDULE.get(curr_day, {})
    res = f"🏫 **ОЧНИЙ РОЗКЛАД**\n📅 {curr_day} ({week_type})\n\n"
    if "Загальне" in day_data: res += day_data["Загальне"] + "\n"
    if week_type in day_data: res += day_data[week_type]
    await message.answer(res, parse_mode="Markdown")

@dp.message(F.text == "📅 Який тиждень?")
async def check_week_type(message: types.Message):
    await message.answer(f"Зараз встановлено: **{get_week_type()}**", parse_mode="Markdown")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())