import pandas as pd
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, MessageHandler, filters, \
    ConversationHandler
import os
import re

# Определяем состояния
MAIN_MENU, DIRECTION_SELECT, GROUP_SELECT, SEARCH_FIO = range(4)


def load_schedule():
    try:
        df = pd.read_excel("raspisanie_by_cabinets.xlsx", header=0)
        df = df.dropna(how='all')
        return df
    except Exception as e:
        print(f"Ошибка при загрузке расписания: {e}")
        return None


def load_users():
    try:
        if os.path.exists("users.xlsx"):
            df = pd.read_excel("users.xlsx")
            return df
        return pd.DataFrame(columns=['ФИО', 'Группа'])
    except Exception as e:
        print(f"Ошибка при загрузке пользователей: {e}")
        return pd.DataFrame(columns=['ФИО', 'Группа'])


def save_users(df):
    try:
        df.to_excel("users.xlsx", index=False)
    except Exception as e:
        print(f"Ошибка при сохранении пользователей: {e}")


def extract_directions(df):
    directions = set()
    for direction in df['Направление'].dropna():
        if isinstance(direction, str):
            directions.add(direction.strip())
    return sorted(directions)


def extract_groups(df, direction=None):
    groups = set()
    if direction:
        filtered = df[df['Направление'] == direction]
    else:
        filtered = df

    for group in filtered['Группа'].dropna():
        if isinstance(group, str):
            groups.add(group.strip())
    return sorted(groups)


async def show_developer_info(update: Update, context: CallbackContext):
    developer_info = """
👨‍💻 Информация о разработчике:

📌 Имя: Ваулин Матвей Анатольевич
👨‍🏫 Наставник: Мальцев Алексей Александрович
📧 Email: SyLex74@yandex.ru
📅 Обучение: 4 года IT-cube г.Сатка
🛠️ Закончил курсы:
    - Системное администрирование
    - Мобильная разработка
    - Виртуальная разработка(3D)
    - программирование на Python

По вопросам пишите @SyLex_74
"""
    await update.message.reply_text(
        developer_info,
        reply_markup=ReplyKeyboardMarkup([['Назад']], one_time_keyboard=True, resize_keyboard=True)
    )
    return MAIN_MENU


async def start(update: Update, context: CallbackContext):
    if not os.path.exists("raspisanie_by_cabinets.xlsx"):
        await update.message.reply_text(
            "Файл расписания не найден. Убедитесь, что файл 'raspisanie_by_cabinets.xlsx' находится в той же папке, что и бот.")
        return ConversationHandler.END

    keyboard = [
        ['Выбрать направление', 'Поиск по ФИО'],
        ['Все расписание', 'Разработчик']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=reply_markup
    )
    return MAIN_MENU


async def main_menu(update: Update, context: CallbackContext):
    if update.message.text == 'Назад':
        return await start(update, context)

    choice = update.message.text

    if choice == 'Выбрать направление':
        df = load_schedule()
        if df is None:
            await update.message.reply_text("Ошибка при чтении файла расписания")
            return await start(update, context)

        directions = extract_directions(df)
        if not directions:
            await update.message.reply_text("Направления не найдены в расписании")
            return await start(update, context)

        keyboard = [directions[i:i + 2] for i in range(0, len(directions), 2)]
        keyboard.append(['Назад'])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Выберите направление:", reply_markup=reply_markup)
        return DIRECTION_SELECT

    elif choice == 'Поиск по ФИО':
        await update.message.reply_text(
            "Введите ваше ФИО для поиска группы:",
            reply_markup=ReplyKeyboardMarkup([['Назад']], one_time_keyboard=True, resize_keyboard=True)
        )
        return SEARCH_FIO

    elif choice == 'Все расписание':
        df = load_schedule()
        if df is None:
            await update.message.reply_text("Ошибка при чтении файла расписания")
            return await start(update, context)

        response = "📋 Полное расписание:\n\n"
        current_direction = None

        for _, row in df.iterrows():
            if pd.notna(row['Направление']) and row['Направление'] != current_direction:
                current_direction = row['Направление']
                response += f"\n🌟 Направление: {current_direction}\n"
                response += f"📍 Кабинет: {row['Кабинет']}\n"
                response += "────────────────────\n"

            response += f"👥 Группа: {row['Группа']}\n"
            response += f"👨‍🏫 Руководитель: {row['Руководитель']}\n"
            response += f"📅 {row['День недели']} | 🕒 {row['Время']}\n"
            response += "────────────────────\n"

        for i in range(0, len(response), 4000):
            await update.message.reply_text(
                response[i:i + 4000],
                reply_markup=ReplyKeyboardMarkup([['Назад']], one_time_keyboard=True, resize_keyboard=True)
            )

        return await start(update, context)

    elif choice == 'Разработчик':
        return await show_developer_info(update, context)


async def handle_direction_select(update: Update, context: CallbackContext):
    if update.message.text == 'Назад':
        return await start(update, context)

    selected_direction = update.message.text.strip()
    context.user_data['selected_direction'] = selected_direction

    df = load_schedule()
    groups = extract_groups(df, selected_direction)

    keyboard = [groups[i:i + 3] for i in range(0, len(groups), 3)]
    keyboard.append(['Все группы', 'Назад'])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        f"Выбрано направление: {selected_direction}\nВыберите группу:",
        reply_markup=reply_markup
    )
    return GROUP_SELECT


async def handle_group_select(update: Update, context: CallbackContext):
    if update.message.text == 'Назад':
        return await main_menu(update, context)

    selected_group = update.message.text.strip()
    df = load_schedule()

    if selected_group == 'Все группы':
        selected_direction = context.user_data.get('selected_direction')
        group_schedule = df[df['Направление'] == selected_direction]

        response = f"📋 Расписание для направления {selected_direction}:\n\n"

        for _, row in group_schedule.iterrows():
            response += f"👥 Группа: {row['Группа']}\n"
            response += f"👨‍🏫 Руководитель: {row['Руководитель']}\n"
            response += f"📅 {row['День недели']} | 🕒 {row['Время']}\n"
            response += "────────────────────\n"

        await update.message.reply_text(
            response,
            reply_markup=ReplyKeyboardMarkup([['Назад']], one_time_keyboard=True, resize_keyboard=True)
        )
        return await start(update, context)
    else:
        group_schedule = df[df['Группа'] == selected_group]

        if group_schedule.empty:
            await update.message.reply_text(
                f"Для группы {selected_group} занятий не найдено",
                reply_markup=ReplyKeyboardMarkup([['Назад']], one_time_keyboard=True, resize_keyboard=True)
            )
            return await start(update, context)

        group_info = group_schedule.iloc[0]
        response = (
            f"📋 Расписание для группы:\n"
            f"🌟 Направление: {group_info['Направление']}\n"
            f"📍 Кабинет: {group_info['Кабинет']}\n"
            f"👥 Группа: {group_info['Группа']}\n"
            f"👨‍🏫 Руководитель: {group_info['Руководитель']}\n\n"
        )

        for _, row in group_schedule.iterrows():
            response += f"📅 {row['День недели']} | 🕒 {row['Время']}\n"
            response += "────────────────────\n"

        await update.message.reply_text(
            response,
            reply_markup=ReplyKeyboardMarkup([['Назад']], one_time_keyboard=True, resize_keyboard=True)
        )
        return await start(update, context)


def normalize_name(name):
    """Нормализует имя для поиска: удаляет лишние пробелы, приводит к нижнему регистру"""
    return ' '.join(re.sub(r'[^\w\s]', '', name.lower()).split())


def is_name_match(search_name, target_name):
    """Проверяет, соответствует ли поисковый запрос имени"""
    if not search_name or not target_name or pd.isna(target_name):
        return False

    search_parts = normalize_name(search_name).split()
    target_parts = normalize_name(target_name).split()

    # Все части поискового запроса должны быть в имени
    return all(part in ' '.join(target_parts) for part in search_parts)


async def handle_fio_search(update: Update, context: CallbackContext):
    if update.message.text == 'Назад':
        return await start(update, context)

    search_name = update.message.text.strip()
    users_df = load_users()
    schedule_df = load_schedule()

    if users_df.empty or schedule_df is None:
        await update.message.reply_text(
            "Информация о группах не найдена. Обратитесь к администратору.",
            reply_markup=ReplyKeyboardMarkup([['Назад']], one_time_keyboard=True, resize_keyboard=True)
        )
        return SEARCH_FIO

    # Ищем в базе пользователей
    user_groups = []
    for _, row in users_df.iterrows():
        if is_name_match(search_name, row['ФИО']):
            user_groups.append(row['Группа'])

    # Если не нашли, ищем среди руководителей
    if not user_groups:
        for _, row in schedule_df.iterrows():
            if is_name_match(search_name, row['Руководитель']):
                user_groups.append(row['Группа'])

    # Удаляем дубликаты и сортируем
    user_groups = sorted(list(set(user_groups)))

    if not user_groups:
        await update.message.reply_text(
            f"ФИО '{search_name}' не найдено в базе. Попробуйте ввести полное ФИО или обратитесь к администратору.",
            reply_markup=ReplyKeyboardMarkup([['Назад']], one_time_keyboard=True, resize_keyboard=True)
        )
        return SEARCH_FIO

    if len(user_groups) == 1:
        selected_group = user_groups[0]
        group_schedule = schedule_df[schedule_df['Группа'] == selected_group]

        if group_schedule.empty:
            await update.message.reply_text(
                f"Для группы {selected_group} занятий не найдено",
                reply_markup=ReplyKeyboardMarkup([['Назад']], one_time_keyboard=True, resize_keyboard=True)
            )
            return await start(update, context)

        group_info = group_schedule.iloc[0]
        response = (
            f"🔍 Найдена группа по вашему ФИО:\n\n"
            f"🌟 Направление: {group_info['Направление']}\n"
            f"📍 Кабинет: {group_info['Кабинет']}\n"
            f"👥 Группа: {group_info['Группа']}\n"
            f"👨‍🏫 Руководитель: {group_info['Руководитель']}\n\n"
            f"📋 Расписание:\n"
        )

        for _, row in group_schedule.iterrows():
            response += f"\n📅 {row['День недели']} | 🕒 {row['Время']}"

        await update.message.reply_text(
            response,
            reply_markup=ReplyKeyboardMarkup([['Назад']], one_time_keyboard=True, resize_keyboard=True)
        )
        return await start(update, context)
    else:
        keyboard = [[group] for group in user_groups]
        keyboard.append(['Назад'])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            f"Найдено несколько групп для ФИО '{search_name}':\nВыберите вашу группу:",
            reply_markup=reply_markup
        )
        return GROUP_SELECT


def main():
    # Создаем файл users.xlsx, если его нет
    if not os.path.exists("users.xlsx"):
        pd.DataFrame(columns=['ФИО', 'Группа']).to_excel("users.xlsx", index=False)

    app = ApplicationBuilder().token("7595627769:AAHVgyd9_wcKCkhYIXrDw5e7W-OwP3Bmuos").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu)],
            DIRECTION_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_direction_select)],
            GROUP_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_group_select)],
            SEARCH_FIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_fio_search)],
        },
        fallbacks=[CommandHandler("start", start)]
    )

    app.add_handler(conv_handler)
    app.run_polling()


if __name__ == '__main__':
    main()