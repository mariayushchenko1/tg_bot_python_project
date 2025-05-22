from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackContext,
    CommandHandler
)
import sqlite3

# Конфигурация бота
TOKEN = "токен"
DB_NAME = "mood.db"

# Клавиатуры
main_kb = ReplyKeyboardMarkup(
    [["1", "2", "3"], ["4", "5", "Статистика"], ["Назад"]],
    resize_keyboard=True
)

factor_kb = ReplyKeyboardMarkup(
    [["Друзья", "Семья"], ["Работа", "Учеба"], ["Здоровье", "Другое"], ["Назад"]],
    resize_keyboard=True,
)


# Инициализация базы данных
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS moods (
            user_id INTEGER,
            rating INTEGER,
            factor TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в трекер настроения!Если хотите вернуться к выбору другого трека, перейдите в @SaludHealthCareBot",
        reply_markup=ReplyKeyboardMarkup([["Трекер настроения"]], resize_keyboard=True)
    )


async def start_mood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Оцените настроение:", reply_markup=main_kb)


async def process_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Статистика":
        return await show_stats(update, context)
    if text == "Назад":
        return await start(update, context)

    if text in ["1", "2", "3", "4", "5"]:
        context.user_data["rating"] = int(text)
        await update.message.reply_text("Что повлияло?", reply_markup=factor_kb)


async def process_factor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад":
        return await start_mood(update, context)

    if "rating" not in context.user_data:
        return await update.message.reply_text(
            "Пожалуйста, начните сначала", reply_markup=main_kb
        )

    user_id = update.effective_user.id
    rating = context.user_data["rating"]
    factor = text

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO moods (user_id, rating, factor) VALUES (?, ?, ?)",
        (user_id, rating, factor),
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"✅ Сохранено! Настроение: {rating}", reply_markup=main_kb
    )
    context.user_data.clear()


async def show_stats(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT AVG(rating) FROM moods WHERE user_id = ?", (user_id,))
    avg = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT factor, COUNT(*) as count
        FROM moods
        WHERE user_id = ?
        GROUP BY factor
        ORDER BY count DESC
        LIMIT 1
        """,
        (user_id,),
    )
    result = cursor.fetchone()
    conn.close()

    if avg is None:
        await update.message.reply_text(
            "У вас пока нет сохраненных данных", reply_markup=main_kb
        )
    else:
        message = (
            "📊 Ваша статистика:\n"
            f"• Средний балл: {round(avg, 2)}\n"
            f"• Самый частый фактор: {result[0] if result else 'нет данных'}"
        )
        await update.message.reply_text(message, reply_markup=main_kb)


# Настройка и запуск бота
def main():
    application = Application.builder().token(TOKEN).build()
    init_db()

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^Трекер настроения$"), start_mood))

    # Обработчик для кнопок 1-5 и Статистика
    application.add_handler(MessageHandler(filters.Regex("^([1-5]|Статистика)$"), process_rating))

    # Обработчик для факторов влияния
    application.add_handler(MessageHandler(
        filters.Regex("^(Друзья|Семья|Работа|Учеба|Здоровье|Другое)$"),
        process_factor
    ))

    # Обработчик для кнопки Назад (добавлен отдельно)
    application.add_handler(MessageHandler(filters.Regex("^Назад$"), back_handler))

    print("Бот запущен...")
    application.run_polling()


# Обработчик для кнопки Назад
async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_state = context.user_data.get("current_state")

    if "rating" in context.user_data:
        # Если пользователь выбирал рейтинг, возвращаем к оценке настроения
        await start_mood(update, context)
    else:
        # Иначе возвращаем в начало
        await start(update, context)


if __name__ == "__main__":
    main()
