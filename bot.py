import asyncio
import json
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

BOT_TOKEN = "8816416258:AAFgfi2GCv9WVlRLSJgnN7Mkrw_KY4Mx_Mw"

# Часовой пояс Москва (UTC+3)
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

# Дата начала 1-го семестра
SEMESTER_START = date(2026, 9, 1)

USERS_FILE = "users.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

WEEKDAYS = [
    "Понедельник", "Вторник", "Среда",
    "Четверг", "Пятница", "Суббота", "Воскресенье"
]

def load_schedule():
    with open("schedule.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_subscribers() -> set:
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_subscriber(user_id: int):
    users = load_subscribers()
    if user_id not in users:
        users.add(user_id)
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(users), f)

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
    save_subscriber(message.chat.id)
    await message.answer(
        "👋 Бот расписания для группы <b>14.6-520</b>.\n"
        "Вы автоматически подписаны на ежедневную рассылку в 06:00 (МСК).\n\n"
        "Также вы можете запросить расписание вручную:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.message(F.text == "Сегодня")
async def send_today(message: Message):
    now_msk = datetime.now(MOSCOW_TZ)
    text = get_day_schedule_text(now_msk)
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "Завтра")
async def send_tomorrow(message: Message):
    tomorrow_msk = datetime.now(MOSCOW_TZ) + timedelta(days=1)
    text = get_day_schedule_text(tomorrow_msk)
    await message.answer(text, parse_mode="HTML")

# Ежедневная рассылка в 06:00 по Москве
async def daily_scheduler():
    while True:
        now = datetime.now(MOSCOW_TZ)
        # Целевое время — ближайшие 06:00 МСК
        target = now.replace(hour=6, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        
        sleep_seconds = (target - now).total_seconds()
        await asyncio.sleep(sleep_seconds)
        
        # Момент отправки (06:00 МСК)
        send_time = datetime.now(MOSCOW_TZ)
        text = "🌅 <b>Доброе утро! Расписание на сегодня:</b>\n\n" + get_day_schedule_text(send_time)
        subscribers = load_subscribers()
        
        for chat_id in subscribers:
            try:
                await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
                await asyncio.sleep(0.05)
            except Exception:
                pass

# Заглушка для открытого порта Render
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
    # Запуск фонового планировщика рассылки
    asyncio.create_task(daily_scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
