from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from datetime import datetime
import logging

# настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# хранилище данных пользователей
user_data = {}


class WorkoutData:
    def __init__(self):
        self.selected_days = []  # дни тренировок
        self.completed = {}  # статистика выполнения (в формате "день": True/False)
        self.current_day = None  # текущий день


# клавиатуры
def get_keyboard(buttons):
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


START_KEYBOARD = get_keyboard([["Начать тренировки", "Мои тренировки"]])
DAYS_KEYBOARD = get_keyboard([["Пн", "Вт", "Ср"], ["Чт", "Пт", "Сб"], ["Вс", "Готово"]])
YES_NO_KEYBOARD = get_keyboard([["Да", "Нет"]])
MAIN_KEYBOARD = get_keyboard([["Назад", "Статистика", "Мои тренировки"]])


# конвертируем дни недели в цифровой формат
def day_to_num(day):
    days = {"пн": 0, "вт": 1, "ср": 2, "чт": 3, "пт": 4, "сб": 5, "вс": 6}
    return days.get(day.lower(), 0)


# команда start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в трекер тренировок!\n\n"
        "(Если хотите выбрать другие разделы, перейдите сюда @SaludHealthCareBot)",
        reply_markup=START_KEYBOARD
    )


# начало работы с тренировками
async def start_workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = WorkoutData()

    await update.message.reply_text(
        "Выберите дни для тренировок:",
        reply_markup=DAYS_KEYBOARD
    )


async def process_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.lower()

    if text == "готово":
        if not user_data[user_id].selected_days:
            await update.message.reply_text("Выберите хотя бы один день!")
            return

        await update.message.reply_text(
            f"Вы выбрали тренировки в: {', '.join(user_data[user_id].selected_days)}"
            f"\n\nДля отметки пройденных тренировок нажмите 'Мои тренировки'",
            reply_markup=MAIN_KEYBOARD
        )

    elif text in ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]:
        if text not in user_data[user_id].selected_days:
            user_data[user_id].selected_days.append(text)
            await update.message.reply_text(f"Добавлен {text}")
# Показ выбранных тренировок


async def show_my_workouts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data or not user_data[user_id].selected_days:
        await update.message.reply_text("У вас нет запланированных тренировок")
        return

    # Создаем кнопки для выбранных дней
    days_buttons = []
    for day in user_data[user_id].selected_days:
        days_buttons.append([day])

    days_buttons.append(["Назад"])

    await update.message.reply_text(
        "Ваши запланированные тренировки:\n\n"
        " Нажмите на интересующий вас день недели, чтобы отметить прогресс в тренировках в этот день!",
        reply_markup=get_keyboard(days_buttons)
    )


# обработка выбора дня для отметки
async def process_workout_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    day = update.message.text.lower()

    if user_id not in user_data:
        await update.message.reply_text("Сначала выберите дни тренировок")
        return

    if day not in user_data[user_id].selected_days:
        await update.message.reply_text("Этот день не выбран для тренировок")
        return

    # Запоминаем день для отметки
    user_data[user_id].current_day = day
    await update.message.reply_text(
        f"Вы сделали тренировку в {day}?",
        reply_markup=YES_NO_KEYBOARD
    )


# Обработка ответа о тренировке
async def process_workout_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    answer = update.message.text.lower()

    if user_id not in user_data or user_data[user_id].current_day is None:
        await update.message.reply_text("Ошибка обработки ответа")
        return

    day = user_data[user_id].current_day
    date_key = f"{day}_{datetime.now().strftime('%Y-%m-%d')}"

    user_data[user_id].completed[date_key] = (answer == "да")
    user_data[user_id].current_day = None

    await update.message.reply_text(
        "Отлично!" if answer == "да" else "Пропуск записан! Не забывайте про свои тренировки!",
        reply_markup=MAIN_KEYBOARD
    )


# статистикка
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data or not user_data[user_id].completed:
        await update.message.reply_text("У вас еще нет статистики!")
        return

    user = user_data[user_id]
    total = len(user.completed)
    done = sum(user.completed.values())

    stats = (
        "📊 Ваша статистика:\n"
        f"• Всего отметок: {total}\n"
        f"• Выполнено: {done}\n"
        f"• Пропущено: {total - done}\n"
        "Продолжайте в том же духе!"
    )
    await update.message.reply_text(stats)


# Главная функция
def main():
    application = Application.builder().token("ваш токен").build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Text(["Начать тренировки"]), start_workout))
    application.add_handler(MessageHandler(filters.Text(["Мои тренировки"]), show_my_workouts))
    application.add_handler(
        MessageHandler(filters.Text(["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс", "Готово"]), process_days))
    application.add_handler(MessageHandler(filters.Text(["Да", "Нет"]), process_workout_answer))
    application.add_handler(MessageHandler(filters.Text(["Статистика"]), show_stats))
    application.add_handler(MessageHandler(filters.Text(["Назад"]), start))

    # Добавляем обработчик для выбранных дней
    application.add_handler(MessageHandler(
        filters.Text(["пн", "вт", "ср", "чт", "пт", "сб", "вс"]),
        process_workout_day
    ))

    # Запуск бота
    application.run_polling()


if __name__ == "__main__":
    main()

