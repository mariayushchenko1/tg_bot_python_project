import logging
from aiogram import Bot, types, executor
from aiogram.utils import executor
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token="YOUR_BOT_TOKEN")

# Хранилище данных в памяти
user_tasks = {}

# Клавиатура выбора частоты
def get_frequency_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["Каждый час", "Каждые 2 часа", "Каждые 3 часа", "Три раза в день"]
    keyboard.add(*buttons)
    return keyboard

# Клавиатура для уведомлений
def get_drank_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Выпил стакан ✅", callback_data="drank"))
    return keyboard

# Функция уведомлений
async def water_notifier(user_id: int, interval: int):
    while user_id in user_tasks:
        try:
            await bot.send_message(
                user_id,
                "💧 Пора выпить воды! 💧",
                reply_markup=get_drank_keyboard()
            )
            await asyncio.sleep(interval)
        except Exception as e:
            logging.error(f"Ошибка уведомления для {user_id}: {e}")
            break

# Обработчик команды /start
@bot.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer(
        "💧 Привет! Я помогу тебе не забывать пить воду.\n"
        "Выбери частоту напоминаний:",
        reply_markup=get_frequency_keyboard()
    )

# Обработчик выбора частоты
@bot.message_handler(content_types=['text'])
async def handle_text(message: types.Message):
    frequencies = {
        "Каждый час": 3600,
        "Каждые 2 часа": 7200,
        "Каждые 3 часа": 10800,
        "Три раза в день": 28800
    }
    
    if message.text in frequencies:
        user_id = message.from_user.id
        interval = frequencies[message.text]
        
        # Останавливаем предыдущую задачу, если была
        if user_id in user_tasks:
            user_tasks[user_id].cancel()
        
        # Запускаем новую задачу
        task = asyncio.create_task(water_notifier(user_id, interval))
        user_tasks[user_id] = task
        
        await message.answer(
            f"✅ Напоминания включены: {message.text}",
            reply_markup=types.ReplyKeyboardRemove()
        )

# Обработчик кнопки "Выпил стакан"
@bot.callback_query_handler(func=lambda call: call.data == "drank")
async def drank_water(callback: types.CallbackQuery):
    await callback.answer("Отлично! Так держать! 💧")
    await callback.message.edit_reply_markup()

# Обработчик команды /stop
@bot.message_handler(commands=['stop'])
async def cmd_stop(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_tasks:
        user_tasks[user_id].cancel()
        del user_tasks[user_id]
        await message.answer("🔕 Напоминания отключены")

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(bot, skip_updates=True)