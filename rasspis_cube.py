import pandas as pd
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, MessageHandler, filters, \
    ConversationHandler
import os
import dotenv
import re
import hashlib

# Определяем состояния
AUTH, REGISTER, MAIN_MENU, DIRECTION_SELECT, GROUP_SELECT, SEARCH_FIO = range(6)
dotenv.load_dotenv()


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


def load_auth_data():
    try:
        if os.path.exists("auth_data.xlsx"):
            df = pd.read_excel("auth_data.xlsx")
            return df
        return pd.DataFrame(columns=['user_id', 'username', 'full_name', 'login', 'password_hash'])
    except Exception as e:
        print(f"Ошибка при загрузке данных авторизации: {e}")
        return pd.DataFrame(columns=['user_id', 'username', 'full_name', 'login', 'password_hash'])


def save_auth_data(df):
    try:
        df.to_excel("auth_data.xlsx", index=False)
    except Exception as e:
        print(f"Ошибка при сохранении данных авторизации: {e}")


def save_users(df):
    try:
        df.to_excel("users.xlsx", index=False)
    except Exception as e:
        print(f"Ошибка при сохранении пользователей: {e}")


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


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
        reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
    )
    return MAIN_MENU


async def start(update: Update, context: CallbackContext):
    if not os.path.exists("raspisanie_by_cabinets.xlsx"):
        await update.message.reply_text(
            "Файл расписания не найден. Убедитесь, что файл 'raspisanie_by_cabinets.xlsx' находится в той же папке, что и бот.")
        return ConversationHandler.END

    auth_data = load_auth_data()
    user_id = update.effective_user.id

    if not auth_data.empty and user_id in auth_data['user_id'].values:
        context.user_data['authorized'] = True
        return await show_main_menu(update, context)
    else:
        keyboard = [
            ['🔑 Войти', '📝 Зарегистрироваться'],
            ['ℹ️ О боте']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "🔒 Для использования бота требуется авторизация.\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )
        return AUTH


async def handle_auth_choice(update: Update, context: CallbackContext):
    choice = update.message.text

    if 'Войти' in choice:
        await update.message.reply_text(
            "Введите ваш логин:",
            reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
        )
        context.user_data['auth_step'] = 'login'
        return AUTH
    elif 'Зарегистрироваться' in choice:
        await update.message.reply_text(
            "Придумайте логин для регистрации:",
            reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
        )
        context.user_data['auth_step'] = 'register_login'
        return REGISTER
    elif 'О боте' in choice:
        await update.message.reply_text(
            "🤖 Этот бот помогает узнать расписание занятий в IT-Cube.\n\n"
            "Для начала работы необходимо войти или зарегистрироваться.",
            reply_markup=ReplyKeyboardMarkup([['🔑 Войти', '📝 Зарегистрироваться']],
                                             one_time_keyboard=True, resize_keyboard=True)
        )
        return AUTH
    else:
        return await start(update, context)


async def handle_login(update: Update, context: CallbackContext):
    if update.message.text == '⬅️ Назад':
        return await start(update, context)

    login = update.message.text.strip()
    context.user_data['login'] = login

    await update.message.reply_text(
        "Введите ваш пароль:",
        reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
    )
    context.user_data['auth_step'] = 'password'
    return AUTH


async def handle_password(update: Update, context: CallbackContext):
    if update.message.text == '⬅️ Назад':
        return await start(update, context)

    password = update.message.text.strip()
    auth_data = load_auth_data()
    login = context.user_data.get('login')

    user_record = auth_data[(auth_data['login'] == login) &
                            (auth_data['password_hash'] == hash_password(password))]

    if not user_record.empty:
        user_id = update.effective_user.id
        auth_data.loc[auth_data['login'] == login, ['user_id', 'username', 'full_name']] = [
            user_id,
            update.effective_user.username,
            update.effective_user.full_name
        ]
        save_auth_data(auth_data)

        context.user_data['authorized'] = True
        await update.message.reply_text("✅ Вы успешно авторизовались!")
        return await show_main_menu(update, context)
    else:
        await update.message.reply_text(
            "❌ Неверный логин или пароль. Попробуйте еще раз или зарегистрируйтесь.",
            reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
        )
        return AUTH


async def handle_register_login(update: Update, context: CallbackContext):
    if update.message.text == '⬅️ Назад':
        return await start(update, context)

    login = update.message.text.strip()
    auth_data = load_auth_data()

    if not auth_data.empty and login in auth_data['login'].values:
        await update.message.reply_text(
            "❌ Этот логин уже занят. Пожалуйста, выберите другой:",
            reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
        )
        return REGISTER

    context.user_data['login'] = login
    await update.message.reply_text(
        "Придумайте пароль (минимум 4 символа):",
        reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
    )
    context.user_data['auth_step'] = 'register_password'
    return REGISTER


async def handle_register_password(update: Update, context: CallbackContext):
    if update.message.text == '⬅️ Назад':
        return await start(update, context)

    password = update.message.text.strip()
    if len(password) < 4:
        await update.message.reply_text(
            "❌ Пароль должен содержать минимум 4 символа. Попробуйте еще раз:",
            reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
        )
        return REGISTER

    context.user_data['password'] = password
    await update.message.reply_text(
        "Повторите пароль для подтверждения:",
        reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
    )
    context.user_data['auth_step'] = 'confirm_password'
    return REGISTER


async def handle_confirm_password(update: Update, context: CallbackContext):
    if update.message.text == '⬅️ Назад':
        return await start(update, context)

    confirm_password = update.message.text.strip()
    password = context.user_data.get('password')

    if confirm_password != password:
        await update.message.reply_text(
            "❌ Пароли не совпадают. Попробуйте еще раз:",
            reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
        )
        context.user_data['auth_step'] = 'register_password'
        return REGISTER

    user = update.effective_user
    auth_data = load_auth_data()

    new_user = pd.DataFrame([{
        'user_id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'login': context.user_data['login'],
        'password_hash': hash_password(password)
    }])

    auth_data = pd.concat([auth_data, new_user], ignore_index=True)
    save_auth_data(auth_data)

    context.user_data['authorized'] = True
    await update.message.reply_text("🎉 Регистрация прошла успешно! Вы авторизованы.")
    return await show_main_menu(update, context)


async def show_main_menu(update: Update, context: CallbackContext):
    keyboard = [
        ['📅 Выбрать направление', '🔍 Поиск по ФИО'],
        ['📋 Все расписание', '👨‍💻 Разработчик'],
        ['⚙️ Профиль']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Главное меню. Выберите действие:",
        reply_markup=reply_markup
    )
    return MAIN_MENU


async def main_menu(update: Update, context: CallbackContext):
    if not context.user_data.get('authorized', False):
        return await start(update, context)

    if update.message.text == '⬅️ Назад':
        return await show_main_menu(update, context)

    choice = update.message.text

    if 'Выбрать направление' in choice:
        df = load_schedule()
        if df is None:
            await update.message.reply_text("Ошибка при чтении файла расписания")
            return await show_main_menu(update, context)

        directions = extract_directions(df)
        if not directions:
            await update.message.reply_text("Направления не найдены в расписании")
            return await show_main_menu(update, context)

        keyboard = [directions[i:i + 2] for i in range(0, len(directions), 2)]
        keyboard.append(['⬅️ Назад'])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Выберите направление:", reply_markup=reply_markup)
        return DIRECTION_SELECT

    elif 'Поиск по ФИО' in choice:
        await update.message.reply_text(
            "Введите ваше ФИО для поиска группы:",
            reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
        )
        return SEARCH_FIO

    elif 'Все расписание' in choice:
        df = load_schedule()
        if df is None:
            await update.message.reply_text("Ошибка при чтении файла расписания")
            return await show_main_menu(update, context)

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
                reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
            )

        return await show_main_menu(update, context)

    elif 'Разработчик' in choice:
        return await show_developer_info(update, context)

    elif 'Профиль' in choice:
        auth_data = load_auth_data()
        user_id = update.effective_user.id
        user_data = auth_data[auth_data['user_id'] == user_id].iloc[0]

        await update.message.reply_text(
            f"👤 Ваш профиль:\n\n"
            f"🆔 ID: {user_data['user_id']}\n"
            f"👤 Имя: {user_data['full_name']}\n"
            f"📛 Логин: {user_data['login']}\n\n"
            "Используйте кнопки ниже для навигации:",
            reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
        )
        return MAIN_MENU


async def handle_direction_select(update: Update, context: CallbackContext):
    if not context.user_data.get('authorized', False):
        return await start(update, context)

    if update.message.text == '⬅️ Назад':
        return await show_main_menu(update, context)

    selected_direction = update.message.text.strip()
    context.user_data['selected_direction'] = selected_direction

    df = load_schedule()
    groups = extract_groups(df, selected_direction)

    keyboard = [groups[i:i + 3] for i in range(0, len(groups), 3)]
    keyboard.append(['Все группы', '⬅️ Назад'])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        f"Выбрано направление: {selected_direction}\nВыберите группу:",
        reply_markup=reply_markup
    )
    return GROUP_SELECT


async def handle_group_select(update: Update, context: CallbackContext):
    if not context.user_data.get('authorized', False):
        return await start(update, context)

    if update.message.text == '⬅️ Назад':
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
            reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
        )
        return await show_main_menu(update, context)
    else:
        group_schedule = df[df['Группа'] == selected_group]

        if group_schedule.empty:
            await update.message.reply_text(
                f"Для группы {selected_group} занятий не найдено",
                reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
            )
            return await show_main_menu(update, context)

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
            reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
        )
        return await show_main_menu(update, context)


def normalize_name(name):
    """Нормализует имя для поиска: удаляет лишние пробелы, приводит к нижнему регистру"""
    return ' '.join(re.sub(r'[^\w\s]', '', name.lower()).split())


def is_name_match(search_name, target_name):
    """Проверяет, соответствует ли поисковый запрос имени"""
    if not search_name or not target_name or pd.isna(target_name):
        return False

    search_parts = normalize_name(search_name).split()
    target_parts = normalize_name(target_name).split()

    return all(part in ' '.join(target_parts) for part in search_parts)


async def handle_fio_search(update: Update, context: CallbackContext):
    if not context.user_data.get('authorized', False):
        return await start(update, context)

    if update.message.text == '⬅️ Назад':
        return await show_main_menu(update, context)

    search_name = update.message.text.strip()
    users_df = load_users()
    schedule_df = load_schedule()

    if users_df.empty or schedule_df is None:
        await update.message.reply_text(
            "Информация о группах не найдена. Обратитесь к администратору.",
            reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
        )
        return SEARCH_FIO

    user_groups = []
    for _, row in users_df.iterrows():
        if is_name_match(search_name, row['ФИО']):
            user_groups.append(row['Группа'])

    if not user_groups:
        for _, row in schedule_df.iterrows():
            if is_name_match(search_name, row['Руководитель']):
                user_groups.append(row['Группа'])

    user_groups = sorted(list(set(user_groups)))

    if not user_groups:
        await update.message.reply_text(
            f"ФИО '{search_name}' не найдено в базе. Попробуйте ввести полное ФИО или обратитесь к администратору.",
            reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
        )
        return SEARCH_FIO

    if len(user_groups) == 1:
        selected_group = user_groups[0]
        group_schedule = schedule_df[schedule_df['Группа'] == selected_group]

        if group_schedule.empty:
            await update.message.reply_text(
                f"Для группы {selected_group} занятий не найдено",
                reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
            )
            return await show_main_menu(update, context)

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
            reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], one_time_keyboard=True, resize_keyboard=True)
        )
        return await show_main_menu(update, context)
    else:
        keyboard = [[group] for group in user_groups]
        keyboard.append(['⬅️ Назад'])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            f"Найдено несколько групп для ФИО '{search_name}':\nВыберите вашу группу:",
            reply_markup=reply_markup
        )
        return GROUP_SELECT


def main():
    if not os.path.exists("users.xlsx"):
        pd.DataFrame(columns=['ФИО', 'Группа']).to_excel("users.xlsx", index=False)

    if not os.path.exists("auth_data.xlsx"):
        pd.DataFrame(columns=['user_id', 'username', 'full_name', 'login', 'password_hash']).to_excel("auth_data.xlsx",
                                                                                                      index=False)

    app = ApplicationBuilder().token(os.getenv('token', 'No token')).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AUTH: [
                MessageHandler(filters.Regex(r'^(🔑 Войти|📝 Зарегистрироваться|ℹ️ О боте)$'), handle_auth_choice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_login)
            ],
            REGISTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_register_login)],
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