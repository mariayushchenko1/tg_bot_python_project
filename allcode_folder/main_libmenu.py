from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)


# создаем сами кнопки
START_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["Зарядка", "Трекер сна"],
        ["Трекер настроения", "Водный баланс"],
        ["Трекер приема таблеток"],
    ],
    resize_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): # функция начала
    await update.message.reply_text("Выберите раздел:", reply_markup=START_KEYBOARD)


# главный экран в самом начале


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # далее кнопки, которые мы выбираем

    if text == "Зарядка":
        await update.message.reply_text(
            "Переходите в этот бот:\n@Salud_sporttracker_bot"
        )

    elif text == "Трекер сна":
        await update.message.reply_text(
            "Переходите в этот бот:\n@Salud_sleeptracker_bot"
        )
    elif text == "Трекер настроения":
        await update.message.reply_text(
            "Переходите в этот бот:\n@Salud_moodtracker_bot"
        )
    elif text == "Водный баланс":
        await update.message.reply_text(
            "Переходите в этот бот:\n@Salud_watertracker_bot"
        )
    elif text == "Трекер приема таблеток":
        await update.message.reply_text(
            "Переходите в этот бот:\n@Salud_pillstracker_bot"
        )

    elif text == "Назад":
        await start(update, context)


def main(): #работа бота
    application = (
        Application.builder().token("токен").build()
    )  # вставьте сюда ваш токен

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu)
    )

    application.run_polling()


if __name__ == "__main__":
    main()
