import asyncio
import json
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

BOT_TOKEN = "8816416258:AAFgfi2GCv9WVlRLSJgnN7Mkrw_KY4Mx_Mw"

# Вставьте ваш числовой Telegram ID из @userinfobot (или оставьте 0)
ADMIN_ID = 5229528293

MOSCOW_TZ = ZoneInfo("Europe/Moscow")
SEMESTER_START = date(2026, 9, 1)

USERS_FILE = "users.json"
ALL_USERS_FILE = "all_users.json"
HOLIDAYS_FILE = "holidays.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

WEEKDAYS = [
    "Понедельник", "Вторник", "Среда",
    "Четверг", "Пятница", "Суббота", "Воскресенье"
]

def load_schedule():
    with open("schedule.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_holidays() -> dict:
    if os.path.exists(HOLIDAYS_FILE):
        try:
            with open(HOLIDAYS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def load_all_users() -> dict:
    if os.path.exists(ALL_USERS_FILE):
        try:
            with open(ALL_USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_user_info(user) -> bool:
    users = load_all_users()
    uid_str = str(user.id)
    is_new = uid_str not in users
    
    users[uid_str] = {
        "id": user.id,
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "username": f"@{user.username}" if user.username else "нет",
        "registered_at": users.get(uid_str, {}).get("registered_at", datetime.now(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M"))
    }
    
    with open(ALL_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    return is_new

def load_subscribers() -> set:
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def toggle_subscriber(user_id: int) -> bool:
    users = load_subscribers()
    if user_id in users:
        users.remove(user_id)
        status = False
    else:
        users.add(user_id)
        status = True
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(users), f)
    return status

def is_subscribed(user_id: int) -> bool:
    return user_id in load_subscribers()

def get_main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    notify_text = "🔕 Отключить рассылку" if is_subscribed(user_id) else "🔔 Включить рассылку"
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Сегодня"), KeyboardButton(text="Завтра")],
            [KeyboardButton(text="Вся неделя"), KeyboardButton(text="🎉 Праздники")],
            [KeyboardButton(text=notify_text)]
        ],
        resize_keyboard=True
    )

def get_study_week_number(target_date: date) -> int:
    start_monday = SEMESTER_START - timedelta(days=SEMESTER_START.weekday())
    target_monday = target_date - timedelta(days=target_date.weekday())
    delta_days = (target_monday - start_monday).days
    return (delta_days // 7) + 1

def get_holidays_text(target_date: date) -> str:
    month_names = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    date_formatted = f"{target_date.day} {month_names[target_date.month - 1]}"
    holidays_dict = load_holidays()
    key = f"{target_date.month}-{target_date.day}"
    holidays = holidays_dict.get(key, ["Отличный день для учёбы и отдыха!"])
    
    formatted_list = "\n".join([f"▫️ {h}" for h in holidays])
    return f"🎉 <b>Праздники на {date_formatted}:</b>\n\n{formatted_list}"

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
        return f"{header}\n🎉 В этот день пар нет!"
    
    return f"{header}\n" + "\n\n".join(active_lessons)

def get_week_schedule_text(current_datetime: datetime) -> str:
    schedule = load_schedule()
    today_date = current_datetime.date()
    current_week = get_study_week_number(today_date)
    monday = today_date - timedelta(days=today_date.weekday())
    
    if current_week < 1:
        week_header = "🗓 <b>РАСПИСАНИЕ НА НЕДЕЛЮ</b>\n<i>(Семестр ещё не начался, старт 01.09)</i>\n"
    elif current_week > 17:
        week_header = f"🗓 <b>РАСПИСАНИЕ НА НЕДЕЛЮ</b>\n<i>(Семестр завершён, {current_week}-я неделя)</i>\n"
    else:
        week_header = f"🗓 <b>РАСПИСАНИЕ НА НЕДЕЛЮ ({current_week}-я учебная неделя)</b>\n"
    
    days_blocks = []
    for day_offset in range(6):
        day_date = monday + timedelta(days=day_offset)
        day_key = str(day_offset)
        day_name = WEEKDAYS[day_offset]
        date_str = day_date.strftime("%d.%m")
        
        lessons = schedule.get(day_key, [])
        active_lessons = []
        for item in lessons:
            start_w, end_w = item["weeks"]
            if start_w <= current_week <= end_w:
                active_lessons.append(f"• <b>{item['time']}</b> | {item['text']}")
        
        if active_lessons:
            lessons_str = "\n".join(active_lessons)
            days_blocks.append(f"<b>{day_name} ({date_str})</b>:\n{lessons_str}")
        else:
            days_blocks.append(f"<b>{day_name} ({date_str})</b>:\n<i>— Пар нет</i>")
    
    return week_header + "\n\n" + "\n\n".join(days_blocks)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    is_new = save_user_info(user)
    
    if is_new and ADMIN_ID != 0 and user.id != ADMIN_ID:
        try:
            admin_alert = (
                f"👤 <b>Новый пользователь в боте!</b>\n\n"
                f"▫️ Имя: {user.full_name}\n"
                f"▫️ Юзернейм: @{user.username if user.username else 'нет'}\n"
                f"▫️ ID: <code>{user.id}</code>"
            )
            await bot.send_message(chat_id=ADMIN_ID, text=admin_alert, parse_mode="HTML")
        except Exception:
            pass

    status_text = "включена" if is_subscribed(message.chat.id) else "выключена"
    await message.answer(
        "👋 Бот расписания для группы <b>14.6-520</b>.\n"
        f"Утренняя рассылка в 06:00 сейчас: <b>{status_text}</b>.\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard(message.chat.id),
        parse_mode="HTML"
    )

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if ADMIN_ID != 0 and message.chat.id != ADMIN_ID:
        return
    
    users = load_all_users()
    subscribers = load_subscribers()
    
    text = f"📊 <b>Статистика бота:</b>\n\n"
    text += f"Всего пользователей: <b>{len(users)}</b> чел.\n"
    text += f"Подписаны на рассылку: <b>{len(subscribers)}</b> чел.\n\n"
    text += "👥 <b>Список:</b>\n"
    
    for u in users.values():
        text += f"• {u['first_name']} {u['last_name']} ({u['username']}) — <code>{u['id']}</code>\n"
    
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "Сегодня")
async def send_today(message: Message):
    now_msk = datetime.now(MOSCOW_TZ)
    text = get_day_schedule_text(now_msk)
    await message.answer(text, reply_markup=get_main_keyboard(message.chat.id), parse_mode="HTML")

@dp.message(F.text == "Завтра")
async def send_tomorrow(message: Message):
    tomorrow_msk = datetime.now(MOSCOW_TZ) + timedelta(days=1)
    text = get_day_schedule_text(tomorrow_msk)
    await message.answer(text, reply_markup=get_main_keyboard(message.chat.id), parse_mode="HTML")

@dp.message(F.text == "Вся неделя")
async def send_week(message: Message):
    now_msk = datetime.now(MOSCOW_TZ)
    text = get_week_schedule_text(now_msk)
    await message.answer(text, reply_markup=get_main_keyboard(message.chat.id), parse_mode="HTML")

@dp.message(F.text == "🎉 Праздники")
async def send_holidays(message: Message):
    now_msk = datetime.now(MOSCOW_TZ)
    text = get_holidays_text(now_msk.date())
    await message.answer(text, reply_markup=get_main_keyboard(message.chat.id), parse_mode="HTML")

@dp.message(F.text.in_(["🔔 Включить рассылку", "🔕 Отключить рассылку"]))
async def toggle_notification(message: Message):
    new_status = toggle_subscriber(message.chat.id)
    if new_status:
        msg = "🔔 <b>Утренняя рассылка включена!</b>\nКаждый день в 06:00 (МСК) вам будет приходить расписание на текущий день."
    else:
        msg = "🔕 <b>Утренняя рассылка отключена.</b>\nВы можете запрашивать расписание вручную через кнопки."
    
    await message.answer(msg, reply_markup=get_main_keyboard(message.chat.id), parse_mode="HTML")

async def daily_scheduler():
    while True:
        now = datetime.now(MOSCOW_TZ)
        target = now.replace(hour=6, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        
        sleep_seconds = (target - now).total_seconds()
        await asyncio.sleep(sleep_seconds)
        
        send_time = datetime.now(MOSCOW_TZ)
        text = "🌅 <b>Доброе утро! Расписание на сегодня:</b>\n\n" + get_day_schedule_text(send_time)
        subscribers = load_subscribers()
        
        for chat_id in subscribers:
            try:
                await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
                await asyncio.sleep(0.05)
            except Exception:
                pass

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
    asyncio.create_task(daily_scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
