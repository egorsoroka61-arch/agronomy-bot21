import asyncio
import sqlite3
import logging
import os  # Додано для роботи з перемінними сервера
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# --- 1. НАЛАШТУВАННЯ ТА БЕЗПЕКА ---
# Бот спочатку шукає BOT_TOKEN у налаштуваннях Railway, якщо не знаходить — використовує порожній рядок
API_TOKEN = os.getenv('BOT_TOKEN', '') 
ADMINS = [8507310778, 123456789] # Твій ID вже тут

if not API_TOKEN:
    exit("Помилка: BOT_TOKEN не знайдено в налаштуваннях Railway!")

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
    
    # Твої посилання НУБіП
    links = [
        ("Грунтознавство", "https://us04web.zoom.us/j/78495547395?pwd=G7fd6KedJHhcfiSOfYlfW7Ca6l4Vk1.1"),
        ("Ботаніка", "https://us05web.zoom.us/j/4317764346?pwd=Ylp6M3lhZG9Fd0xoc0RVdEZTME9Idz09&omn=87697232433"),
        ("Філософія", "https://us04web.zoom.us/j/71119670230?pwd=U26kO6oupnE0iIjZFQiyIFC0doO7g2.1"),
        ("Фізичне виховання", "https://us04web.zoom.us/j/2545730297?pwd=eipmanYl5ybFS6e9GVl536aCvXLOw0.1"),
        ("Сільськогосподарські машини", "https://us04web.zoom.us/j/3572859845?pwd=dCbsuQi0zFa4LZFtcQYPP92FrTBcF4.1"),
        ("Агрометеорологія", "https://nubip-edu-ua.zoom.us/j/9587441507?pwd=VW1GSVR0ejRzRzJ6aWp3OHhjeWphdz09"),
        ("Правова культура", "https://meet.google.com/tro-apjn-qxa"),
        ("Агроекологія", "https://meet.google.com/gbg-yotb-kvx?hs=224")
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
    await message.answer(f"Бот на зв'язку! 📡\nТвій ID: `{message.from_user.id}`", reply_markup=keyboard, parse_mode="Markdown")

@dp.message(F.text == "📝 Домашнє завдання")
async def show_hw(message: types.Message):
    conn = sqlite3.connect('group_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM homework")
    hw_list = cursor.fetchall()
    conn.close()
    if not hw_list: return await message.answer("Завдань немає! Відпочивай. 🌴")
    res = "📝 **АКТУАЛЬНЕ ДЗ:**\n\n" + "\n".join([f"🔹 **{s}**: {t}" for s, t in hw_list])
    await message.answer(res, parse_mode="Markdown")

@dp.message(F.text == "🌐 Онлайн заняття")
async def show_online(message: types.Message):
    week_type = get_week_type()
    days = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]
    curr_day = days[datetime.now().weekday()]
    if curr_day in ["Субота", "Неділя"]: return await message.answer("Вихідний! 😊")

    conn = sqlite3.connect('group_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM online_links")
    links_dict = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()

    day_data = SCHEDULE.get(curr_day, {})
    res_text = f"🌐 **ОНЛАЙН РОЗКЛАД**\n📅 {curr_day} ({week_type})\n"
    kb = []
    
    lessons = []
    if "Загальне" in day_data: lessons.extend(day_data["Загальне"].split('\n'))
    if week_type in day_data: lessons.extend(day_data[week_type].split('\n'))

    for lesson in lessons:
        clean = lesson.split('(')[0].strip()
        link = "#"
        for sub, l in links_dict.items():
            if sub.lower() in clean.lower():
                link = l
                break
        
        res_text += f"📘 **{clean}**\n"
        if link != "#": kb.append([InlineKeyboardButton(text=f"🔗 Приєднатися: {clean}", url=link)])
    
    await message.answer(res_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb) if kb else None, parse_mode="Markdown")

# (Хендлери для Адмінки та Очного розкладу залишаються такими ж, як ми робили раніше)

async def main():
    init_db()
    logging.info("Polling started...") # Лог для Railway
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
