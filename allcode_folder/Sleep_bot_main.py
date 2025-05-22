from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackContext,
)
import sqlite3
import datetime
import logging

logging.basicConfig(level=logging.INFO)

# конфиг
TOKEN = "Ваш токен"  # ! сюда и в файле .env вставьте свой токен !
DB_NAME = "sleep.db"
user_states = {}

# Клавиатуры
main_menu_kb = ReplyKeyboardMarkup(
    [["Регистрация сна", "Посмотреть отчёт"], ["Помощь"]],
    resize_keyboard=True,
)

back_kb = ReplyKeyboardMarkup([["Назад"]], resize_keyboard=True)


# инит бд
def init_db():
    """Инициализация базы данных"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sleep_logs (
                user_id INTEGER,
                sleep_time TEXT,
                wake_time TEXT,
                date TEXT,
                UNIQUE(user_id, date)
            )
        """)
        conn.commit()


# команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌙 Добро пожаловать в Трекер сна!\n"
        "Я помогу отслеживать качество и продолжительность вашего сна.\n"
        "Если хотите вернуться к выбору другого трека, перейдите в @SaludHealthCareBot\n\n"
        "Для начала работы, выберите нужное действие из меню ниже",
        reply_markup=main_menu_kb,
    )


# команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Помощь по боту:\n\n"
        "Основные команды:\n"
        "• Регистрация сна - записать время отхода ко сну и пробуждения\n"
        "• Просмотреть отчёт - получить статистику за сегодня и сравнение с вчера\n"
        "• Назад - вернуться в главное меню в любой момент\n\n"
        "Важно!\n"
        "Вводите время в формате ЧЧ:ММ (например, 23:45 или 07:30)",
        reply_markup=main_menu_kb,
    )


# кнопка "Назад"
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_states:
        del user_states[user_id]
    await start(update, context)


# начало регистрации сна
async def register_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = {"step": "ask_sleep_time"}
    await update.message.reply_text(
        "Во сколько вы легли спать? (например, 23:45)",
        reply_markup=back_kb,
    )


# обработка введенного времени
async def process_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if text == "Назад":
        return await back_to_menu(update, context)

    if user_id not in user_states:
        return await start(update, context)

    state = user_states[user_id]

    # Проверка формата времени
    if not is_valid_time(text):
        await update.message.reply_text(
            "⏳ Пожалуйста, введите время в правильном формате ЧЧ:ММ (например, 23:45)",
            reply_markup=back_kb,
        )
        return

    if state["step"] == "ask_sleep_time":
        state["sleep_time"] = text
        state["step"] = "ask_wake_time"
        await update.message.reply_text(
            "Во сколько вы проснулись? (например, 08:00)",
            reply_markup=back_kb,
        )
    elif state["step"] == "ask_wake_time":
        save_sleep_data(user_id, state["sleep_time"], text)
        duration = calculate_duration(state["sleep_time"], text)

        await update.message.reply_text(
            f"Данные сохранены!\n" f"💤 Продолжительность сна: {duration:.2f} ч",
            reply_markup=main_menu_kb,
        )
        del user_states[user_id]


# проверка формата введенного времени
def is_valid_time(time_str):
    try:
        datetime.datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False


# сохранение данных
def save_sleep_data(user_id, sleep_time, wake_time):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            """
            INSERT INTO sleep_logs (user_id, sleep_time, wake_time, date)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, date) DO UPDATE SET
                sleep_time = excluded.sleep_time,
                wake_time = excluded.wake_time
            """,
            (user_id, sleep_time, wake_time, datetime.date.today().isoformat()),
        )


# расчет продолжительности сна
def calculate_duration(sleep_time, wake_time):
    try:
        sleep = datetime.datetime.strptime(sleep_time, "%H:%M").time()
        wake = datetime.datetime.strptime(wake_time, "%H:%M").time()

        sleep_dt = datetime.datetime.combine(datetime.date.today(), sleep)
        wake_dt = datetime.datetime.combine(
            (
                datetime.date.today() + datetime.timedelta(days=1)
                if wake < sleep
                else datetime.date.today()
            ),
            wake,
        )

        return (wake_dt - sleep_dt).total_seconds() / 3600
    except:
        return 0


# просмотр отчета
async def show_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = get_sleep_duration(user_id, datetime.date.today())
    yesterday = get_sleep_duration(
        user_id, datetime.date.today() - datetime.timedelta(days=1)
    )

    if today is None:
        await update.message.reply_text(
            "📊 У вас еще нет данных о сне за сегодня.", reply_markup=main_menu_kb
        )
        return

    msg = f"📊 Сегодня вы спали {today:.2f} ч"

    if yesterday:
        delta = today - yesterday
        if delta > 0:
            msg += f" (на {delta:.2f} ч больше, чем вчера)"
        elif delta < 0:
            msg += f" (на {abs(delta):.2f} ч меньше, чем вчера)"
        else:
            msg += " (как вчера)"

    await update.message.reply_text(msg, reply_markup=main_menu_kb)


def get_sleep_duration(user_id, date):
    with sqlite3.connect(DB_NAME) as conn:
        row = conn.execute(
            "SELECT sleep_time, wake_time FROM sleep_logs WHERE user_id = ? AND date = ?",
            (user_id, date.isoformat()),
        ).fetchone()

        if row and row[0] and row[1]:
            return calculate_duration(row[0], row[1])
        return None


# Обработка неизвестных команд
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я не понимаю эту команду. Используйте кнопки меню.", reply_markup=main_menu_kb
    )


def main():
    init_db()

    app = Application.builder().token(TOKEN).build()

    # обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # обработчики сообщений
    app.add_handler(MessageHandler(filters.Regex("^Регистрация сна$"), register_sleep))
    app.add_handler(MessageHandler(filters.Regex("^Посмотреть отчёт$"), show_report))
    app.add_handler(MessageHandler(filters.Regex("^Помощь$"), help_command))
    app.add_handler(MessageHandler(filters.Regex("^Назад$"), back_to_menu))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_time_input))

    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
