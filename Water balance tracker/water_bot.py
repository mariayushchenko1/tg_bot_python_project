# импорт библиотек

import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, time

# определение состояний (шагов, на которых находится пользователь)

class WaterTracker(StatesGroup):
    weight = State()
    frequency = State()
    start_time = State()
    end_time = State()
    tracking = State()

# определение переменных (данные пользователя и запущенные задачи)

current_users = {}
user_timers = {}

# прозрачные кнопки (кнопка для того, чтоб отметить выпитый стакан + клавиатура для частоты напоминаний)

def glass_buttons():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🥤 Стакан выпит", callback_data="drink")]]
    )

def frequency_buttons():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=" Каждые 30 минут ", callback_data="freq_30")],
            [InlineKeyboardButton(text=" Каждый час ", callback_data="freq_60")],
            [InlineKeyboardButton(text=" Каждые 2 часа ", callback_data="freq_120")],
            [InlineKeyboardButton(text=" Каждые 3 часа ", callback_data="freq_180")]
        ]
    )

# расчёт нормы воды в литрах и стаканах

def calculate_litr(weight):
    return max(round(weight * 30 / 1000, 1), 1)  # переводим миллилитры в литры

def calculate_norm(weight):
    return max(round(weight * 30 / 250), 1) # в стакане 250 мл

# обработка команды "старт"

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.set_state(WaterTracker.weight)
    await message.answer("💧 Водный трекер\n\nС помощью этого раздела вы без проблем сможете поддерживать необходимый водный баланс!\nДля расчёта дневной нормы введите свой вес (в кг):")

# перевод веса в норму воды

@dp.message(WaterTracker.weight)
async def get_weight(message: types.Message, state: FSMContext):
    try:
        weight = float(message.text)
        if weight < 1:
            await message.answer("❌ Вес должен быть не менее 1 кг. Введите снова:")
            return
        if weight > 250:
            await message.answer("❌ Вес должен быть не более 250 кг. Введите снова:")
            return
            
        await state.update_data(
            weight=weight,
            norm=calculate_norm(weight),
            drunk=0
        )
        await state.set_state(WaterTracker.frequency)
        await message.answer(
            f"Супер! Ваша дневная норма — {calculate_litr(weight)} литров воды. Это около {calculate_norm(weight)} стаканов\n"
            "Выберите частоту напоминаний:",
            reply_markup=frequency_buttons()
        )
    except ValueError:
        await message.answer("Введите число больше 0 и меньше 250")

# callback для клавиатуры с частотой напоминания

@dp.callback_query(lambda c: c.data.startswith("freq_"))
async def process_frequency(callback: types.CallbackQuery, state: FSMContext):
    freq = int(callback.data.split("_")[1])
    await state.update_data(frequency=freq)
    await state.set_state(WaterTracker.start_time)
    await callback.message.edit_text(
        f"✅ Выбрано: каждые {freq} минут\n"
        "Во сколько начинать напоминания? (Например: 09:00)"
    )
    await callback.answer()

# принимаем во сколько начинать, спрашиваем во сколько заканчивать

@dp.message(WaterTracker.start_time)
async def get_start_time(message: types.Message, state: FSMContext):
    try:
        start = datetime.strptime(message.text, "%H:%M").time()
        await state.update_data(start_time=start)
        await state.set_state(WaterTracker.end_time)
        await message.answer("Во сколько заканчивать напоминания? (Например: 21:00)")
    except ValueError:
        await message.answer("Неверный формат — пожалуйста, введите время в формате ЧЧ:MM")

# вывод сохраненных настроек

@dp.message(WaterTracker.end_time)
async def get_end_time(message: types.Message, state: FSMContext):
    try:
        end = datetime.strptime(message.text, "%H:%M").time()
        user_data = await state.get_data()
        
        current_users[message.from_user.id] = user_data
        await state.set_state(WaterTracker.tracking)
        
        task = asyncio.create_task(schedule_reminders(message.from_user.id, user_data['frequency']))
        user_timers[message.from_user.id] = task
        
        await message.answer(
            f"✅ Настройки сохранены!\n"
            f"• Дневная норма: {user_data['norm']} стаканов\n"
            f"• Напоминания: каждые {user_data['frequency']} минут\n"
            f"• Время напоминаний: с {user_data['start_time'].strftime('%H:%M')} до {end.strftime('%H:%M')}"
        )
        
    except ValueError:
        await message.answer("Пожалуйста, введите время в формате ЧЧ:MM")


# запуск напоминаний

async def schedule_reminders(user_id: int, interval_minutes: int):
    while user_id in current_users:
        try:
            data = current_users[user_id]
            remaining = data['norm'] - data['drunk']
            
            if remaining <= 0:
                await bot.send_message(user_id, "🎉 Ура, дневная норма выполнена! До завтра")
                break
                
            await bot.send_message(
                user_id,
                f"⏰ Пора пить воду! Осталось {remaining} стаканов",
                reply_markup=glass_buttons()
            )
            
            await asyncio.sleep(interval_minutes * 60)
            
        except Exception as e:
            print(f"Ошибка в напоминаниях для {user_id}: {e}")
            break

# callback для кнопки со стаканом

@dp.callback_query(lambda c: c.data == "drink")
async def drink_water(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in current_users:
        return
        
    current_users[user_id]['drunk'] += 1
    remaining = current_users[user_id]['norm'] - current_users[user_id]['drunk']
    
    if remaining > 0:
        await callback.message.edit_text(
            f"💙 Принято! Осталось {remaining} стаканов", # пока пользователь не выпьет дневную норму
            reply_markup=glass_buttons()
        )
    else:
        await callback.message.edit_text("🎉 Ура, дневная норма выполнена! До завтра")
        if user_id in user_timers:
            user_timers[user_id].cancel()
            del user_timers[user_id]
        if user_id in current_users:
            del current_users[user_id]
    
    await callback.answer()

# обнуление счётчика в 00:00

async def daily_reset():
    for user_id in list(current_users.keys()):
        try:
            await bot.send_message(user_id, "🔄 Новый день! Начинаем отсчёт заново.")
            current_users[user_id]['drunk'] = 0
            if user_id in user_timers:
                user_timers[user_id].cancel()
            task = asyncio.create_task(schedule_reminders(user_id, current_users[user_id]['frequency']))
            user_timers[user_id] = task
        except:
            if user_id in current_users:
                del current_users[user_id]
            if user_id in user_timers:
                user_timers[user_id].cancel()
                del user_timers[user_id]

async def run_periodic_tasks():
    while True:
        now = datetime.now()
        if now.hour == 0 and now.minute == 0:
            await daily_reset()
        await asyncio.sleep(60)
