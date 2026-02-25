import asyncio
import sqlite3
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# --- 1. НАЛАШТУВАННЯ ТА БЕЗПЕКА ---
# Бот бере токен із вкладки Variables на Railway
API_TOKEN = os.getenv('8641455876:AAEt-VQa2dxRQZlOGhd1krymhZ6xzPm6yVY', '') 
ADMINS = [] # Твій ID
ADMINS = [1604690472] # Твій ID

# Шлях до бази даних на підключеному диску Volume
DB_PATH = '/app/data/group_bot.db'

if not API_TOKEN:
    exit("Помилка: BOT_TOKEN не знайдено в Variables на Railway!")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- 2. БАЗА ДАНИХ ---
def init_db():
    # Створюємо папку /app/data, якщо її ще немає на диску
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
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

# --- 3. ЛОГІКА БОТА (Хендлери) ---
@dp.message(Command("start"))
async def start(message: types.Message):
    kb = [
        [KeyboardButton(text="🏫 Очний розклад"), KeyboardButton(text="🌐 Онлайн заняття")],
        [KeyboardButton(text="📝 Домашнє завдання"), KeyboardButton(text="📅 Який тиждень?")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer(f"Бот працює на сервері! 🚀\nТвій ID: `{message.from_user.id}`", reply_markup=keyboard, parse_mode="Markdown")

# (Тут мають бути інші твої хендлери для розкладу та ДЗ)

async def main():
    init_db()
    logging.info("Бот запускається...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
