import asyncio
import json
import os
from datetime import date, datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

BOT_TOKEN = "8816416258:AAFgfi2GCv9WVlRLSJgnN7Mkrw_KY4Mx_Mw"

# Начало учебного года
SEMESTER_START = date(2026, 9, 1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

WEEKDAYS = [
    "Понедельник", "Вторник", "Среда",
    "Четверг", "Пятница", "Суббота", "Воскресенье"
]

def load_schedule():
    with open("schedule.json", "r", encoding="utf-8") as f:
        return json.load(f)

def get_study_week_number(target_date: date) -> int:
    start_monday = SEMESTER_START - timedelta(days=SEMESTER_START.weekday())
    target_monday = target_date - timedelta(days=target_date.weekday())
    delta_days = (target_monday - start_monday).days
    return (delta_days // 7) + 1

def get_day_schedule_text(target_datetime: datetime) -> str:
    schedule = load_schedule()
    target_date = target_datetime.date()
    day_key = str(target_date.weekday())
    day_name = WEEKDAYS[target_date.weekday()]
    date_str = target_date.strftime("%d.%m.%Y")
    
    current_week = get_study_week_number(target_date)
    lessons = schedule.get(day_key, [])
    
    if current_week < 1:
        week_info = "<i>(Семестр ещё не начался, старт 01.09)</i>"
    elif current_week > 17:
        week_info = f"<i>(Семестр завершён, {current_week}-я неделя)</i>"
    else:
        week_info = f"<b>{current_week}-я учебная неделя</b>"

    active_lessons = []
    for item in lessons:
        start_w, end_w = item["weeks"]
        if start_w <= current_week <= end_w:
            active_lessons.append(f"⏱ <b>{item['time']}</b>\n▫️ {item['text']}")
    
    header = f"📅 <b>{day_name} ({date_str})</b>\n📌 {week_info}\n"
    if not active_lessons:
        return f"{header}\n🎉 В этот день пар нет (или они не выпадают на эту неделю)!"
    
    return f"{header}\n" + "\n\n".join(active_lessons)

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Сегодня"), KeyboardButton(text="Завтра")]
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Бот расписания для группы <b>14.6-520</b>.\nВыберите день:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.message(F.text == "Сегодня")
async def send_today(message: Message):
    text = get_day_schedule_text(datetime.now())
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "Завтра")
async def send_tomorrow(message: Message):
    text = get_day_schedule_text(datetime.now() + timedelta(days=1))
    await message.answer(text, parse_mode="HTML")

# Заглушка для Render, чтобы он видел открытый порт
async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/healthz", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
