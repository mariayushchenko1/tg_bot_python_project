from telegram import Update, ReplyKeyboardMarkup  # библиотека для телеграмма
from telegram.ext import (  # расширенная
    Application,
    CommandHandler,
    filters,
    MessageHandler,
    ContextTypes,
)



# клавиатуры
# клавиатура доступных функций
main_kb = ReplyKeyboardMarkup(
    [["Добавить новый препарат"], ["Я ем", "Удалить препарат"], ["В главное меню"]],
    resize_keyboard=True,
    input_field_placeholder="Воспользуйтесь меню:",
    one_time_keyboard=True,
)
# обычная да клавиатура
yn_kb = ReplyKeyboardMarkup(
    [["Да"], ["В начало"]],
    resize_keyboard=True,
    input_field_placeholder="Воспользуйтесь меню:",
    one_time_keyboard=True,
)


# клавиатура приемов (закрытый список)
priem_kb = ReplyKeyboardMarkup(
    [["Завтрак", "Обед", "Ужин"], ["Я все выбрал(а)"], ["В начало"]],
    resize_keyboard=True,
    input_field_placeholder="Воспользуйтесь меню:",
    one_time_keyboard=False,
)

# клавиатура выбора приемов для выдачи информации
em_kb = ReplyKeyboardMarkup(
    [["Завтракаю"], ["Обедаю"], ["Ужинаю"], ["В начало"]],
    resize_keyboard=True,
    input_field_placeholder="Воспользуйтесь меню:",
    one_time_keyboard=False,
)

# клавиатура выбора до/после
when_kb = ReplyKeyboardMarkup(
    [
        ["До еды", "Во время еды", "После еды"],
        ["Хочу выбрать еще прием(ы)"],
        ["В начало"],
    ],
    resize_keyboard=True,
    input_field_placeholder="Воспользуйтесь меню:",
    one_time_keyboard=True,
)

# глобальные переменные

users_info = {}


# команда начала
async def start_med(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in users_info:
        users_info[update.effective_user.id] = {"step": None, "medicines": {}}
    await update.message.reply_text(
        "Добро пожаловать в блокнотик лекарств!\nВыберите, что хотите делать, из списка ниже\nЕсли хотите вернуться к выбору другого трека, перейдите в @SaludHealthCareBot",
        reply_markup=main_kb,
    )


async def handle_newmed(update, context):  # запускаем ветку добавление лекарства
    users_info[update.effective_user.id]["step"] = "ask_new_medicine"
    await update.message.reply_text("Введите название нового препарата:")


async def handle_food(update, context):  # запускаем ветку выдача информации
    users_info[update.effective_user.id]["step"] = "ask_food_priem"
    await update.message.reply_text(
        "Выберите прием пищи, чтобы получить список препаратов для него",
        reply_markup=em_kb,
    )


async def del_med(update, context):  # запускаем ветку удаление лекарства
    users_info[update.effective_user.id]["step"] = "ask_delete"
    await update.message.reply_text(
        f"Вот список всех принимаемых лекарств. Введите название того, что хотели бы удалить: {', '.join(list(users_info[update.effective_user.id]['medicines'].keys()))}"
    )


# выбираем ветку действия и обрабатываем сообщения
async def handle_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):  # функция первого выбора направления
    text = update.message.text
    user_id = update.effective_user.id
    if text == "Добавить новый препарат":
        return await handle_newmed(update, context)
    elif text == "Я ем":
        return await handle_food(update, context)
    elif text == "В начало" or text == "В главное меню":
        return await start_med(update, context)
    elif text == "Удалить препарат":
        return await del_med(update, context)

    state = users_info.get(user_id)

    if state:  # этапы вопросов
        if state["step"] == "ask_new_medicine":  # обрабатываем название
            if text not in state["medicines"]:
                text = text.title()
                state["medicines"][text] = []
                state["current_medicine"] = text
                medicine_name = state["current_medicine"]
                state["step"] = "ask_dose"
                await update.message.reply_text(
                    "Введите разовую дозу приема (например, 100 мг, или 20 кап, или 1 таб):"
                )
            else:
                await update.message.reply_text(
                    "Вы уже загрузили информацию об этом препарате"
                )

        elif state["step"] == "ask_dose":  # обрабатываем дозу
            medicine_name = state["current_medicine"]
            state["medicines"][medicine_name].append(text)
            state["step"] = "ask_longitude"
            await update.message.reply_text(
                "Сколько дней курс приема (введите целым числом)?\nВведите 'регулярно', если Вы принимаете препарат регулярно:"
            )

        elif state["step"] == "ask_longitude":  # обрабатываем продолжительность приема
            if not text.isdigit():
                return await update.message.reply_text("Введите количество дней числом")
            medicine_name = state["current_medicine"]
            state["medicines"][medicine_name].append(text)
            state["step"] = "ask_depend"
            await update.message.reply_text(
                "Выберите прием(ы) пищи, когда надо принять препарат",
                reply_markup=priem_kb,
            )

        elif state["step"] == "ask_depend":  # спрашиваем, от чего хотят зависимость
            medicine_name = state["current_medicine"]
            if text != "Я все выбрал(а)":
                state["medicines"][medicine_name].append(text)

                await update.message.reply_text(
                    "Можно выбрать и другие приемы", reply_markup=priem_kb
                )

            else:
                state["step"] = "ask_when"
                await update.message.reply_text(
                    "Все приемы пищи записаны\nВыберите, когда нужно принимать препарат:",
                    reply_markup=when_kb,
                )

        elif state["step"] == "ask_when":  # выбор до/после еды
            medicine_name = state["current_medicine"]
            if text == "Хочу выбрать еще прием(ы)":
                state["step"] = "ask_depend"
                await update.message.reply_text(
                    "Что хотите добавить?", reply_markup=priem_kb
                )

            elif text == "До еды":
                state["medicines"][medicine_name].append(text)
                state["step"] = "ask_before"
                await update.message.reply_text(
                    "Введите, за сколько минут до еды надо принять препарат (например, 15 минут или 1 час)"
                )

            else:
                state["medicines"][medicine_name].append(text)
                state["step"] = "ask_end"
                await update.message.reply_text(
                    "Спасибо за информацию!\nКогда будете принимать пищу, нажмите кнопку 'Я ем', и бот выдаст список необходимых препаратов",
                    reply_markup=main_kb,
                )

        elif state["step"] == "ask_before":  # выбор минуток для до
            medicine_name = state["current_medicine"]
            state["medicines"][medicine_name].append(text)
            state["step"] = "ask_end"
            await update.message.reply_text(
                "Спасибо за информацию!\nКогда будете принимать пищу, нажмите кнопку 'Я ем', и бот выдаст список необходимых препаратов",
                reply_markup=main_kb,
            )

        elif (
            state["step"] == "ask_food_priem"
        ):  # обработка словаря для получения данных по приему пищи
            printed = {
                "Выпить до еды": [],
                "Выпить во время еды": [],
                "Выпить после еды": [],
            }
            if text == "Завтракаю":
                for key, value in state["medicines"].items():
                    if "Завтрак" in value:
                        if "До еды" in value:
                            printed["Выпить до еды"].append(
                                f"• {key} по {value[0]} за {value[-1]} до еды, кол-во дней: {value[1]}"
                            )
                        elif "Во время еды" in value:
                            printed["Выпить во время еды"].append(
                                f"• {key} по {value[0]}, кол-во дней: {value[1]}"
                            )
                        else:
                            printed["Выпить после еды"].append(
                                f"• {key} по {value[0]}, кол-во дней: {value[1]}"
                            )

                if len(printed["Выпить до еды"]) != 0:
                    await update.message.reply_text(
                        f"До еды надо было принять:\n{'\n'.join(printed['Выпить до еды'])}\nВы сделали это?",
                        reply_markup=yn_kb,
                    )
                await update.message.reply_text(
                    f"Приятного аппетита!\nВыпить во время еды:\n{'\n'.join(printed['Выпить во время еды'])}\n\nВыпить после еды:\n{'\n'.join(printed['Выпить после еды'])}"
                )

            elif text == "Обедаю":
                for key, value in state["medicines"].items():
                    if "Обед" in value:
                        if "До еды" in value:
                            printed["Выпить до еды"].append(
                                f"• {key} по {value[0]}, кол-во дней: {value[1]}"
                            )
                        elif "Во время еды" in value:
                            printed["Выпить во время еды"].append(
                                f"• {key} по {value[0]}, кол-во дней: {value[1]}"
                            )
                        else:
                            printed["Выпить после еды"].append(
                                f"• {key} по {value[0]}, кол-во дней: {value[1]}"
                            )

                if len(printed["Выпить до еды"]) != 0:
                    await update.message.reply_text(
                        f"Надо было принять:\n{'\n'.join(printed['Выпить до еды'])}\nВы сделали это?",
                        reply_markup=yn_kb,
                    )
                await update.message.reply_text(
                    f"Приятного аппетита!\nВыпить во время еды:\n{'\n'.join(printed['Выпить во время еды'])}\n\nВыпить после еды:\n{'\n'.join(printed['Выпить после еды'])}"
                )

            elif text == "Ужинаю":
                for key, value in state["medicines"].items():
                    if "Ужин" in value:
                        if "До еды" in value:
                            printed["Выпить до еды"].append(
                                f"• {key} по {value[0]}, кол-во дней: {value[1]}"
                            )
                        elif "Во время еды":
                            printed["Выпить во время еды"].append(
                                f"• {key} по {value[0]}, кол-во дней: {value[1]}"
                            )
                        else:
                            printed["Выпить после еды"].append(
                                f"• {key} по {value[0]}, кол-во дней: {value[1]}"
                            )
                if len(printed["Выпить до еды"]) != 0:
                    await update.message.reply_text(
                        f"Надо было принять:\n{'\n'.join(printed['Выпить до еды'])}\nВы сделали это?",
                        reply_markup=yn_kb,
                    )
                await update.message.reply_text(
                    f"Приятного аппетита!\nВыпить во время еды:\n{'\n'.join(printed['Выпить во время еды'])}\n\nВыпить после еды:\n{'\n'.join(printed['Выпить после еды'])}"
                )

        elif state["step"] == "ask_delete":  # обработка удаления препарата
            text = text.title()
            del state["medicines"][text]
            await update.message.reply_text(f"Препарат {text} удален")

    else:
        await update.message.reply_text(
            "Пожалуйста, выберите действие с клавиатуры:", reply_markup=main_kb
        )


def main():
    # Создание и настройка приложения
    application = (
        Application.builder()
        .token("ваш токен") #Вставьте сюда токен вашего бота
        .build()
    )
    application.add_handler(CommandHandler("start", start_med))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    # Запуск бота
    print("Бот запущен...")
    application.run_polling()


if __name__ == "__main__":
    main()
