import sys
from pathlib import Path
# Получаем путь до текущего каталога скрипта
current_dir = Path(__file__).parent.absolute()

# Поднимаемся на одну директорию выше (к родительскому каталогу)
parent_dir = current_dir.parent

# Добавляем путь к родительской директории в sys.path
sys.path.append(str(parent_dir))

import os
import asyncio
from asyncpg_lite import DatabaseManager
#from decouple import config
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram import F
from aiogram.types import Message
from aiogram import html
from aiogram.types.input_file import FSInputFile
from aiogram.types import InputFile
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.utils.chat_action import ChatActionSender
import config
import argparse
import keyboard as kb
import model_io as mio
from model_tools import split_into_parts
import aiosqlite

learning_book = []
learning_is_on = False

admins = []
mentors = []

chat_history = {}

time_begin = datetime.now()

# Диспетчер
dp = Dispatcher()


def init(cli_args: dict):
    """Initial settings for start."""

    # Load settings from configuration file.
    global cfg
    cfg = config.Config(cli_args.bot_config)

    global ADMIN_ID
    ADMIN_ID = cfg['admin_id']
    admins.append(ADMIN_ID)

    global MENTOR_ID
    MENTOR_ID = cfg['mentor_id']
    mentors.append(MENTOR_ID)

    global TETOKEN
    TETOKEN = cfg['tetoken']

    global BOT_TAG
    BOT_TAG = f"bot<{cfg['bot_name']}>"

    # Объект бота
    global bot
    bot = Bot(token=TETOKEN)

    global LINK_TO_REFERENCE_DOCS
    LINK_TO_REFERENCE_DOCS = cfg['link_to_reference_docs']

    global VER
    VER = cfg['ver']

    global HELP_MSG
    HELP_MSG = cfg['help_msg']

    global CONTACTS_MSG
    CONTACTS_MSG = cfg['contacts_msg']

    global START_GREETINGS
    START_GREETINGS = cfg['start_greetings']

    global MAX_MESSAGE_SIZE 
    MAX_MESSAGE_SIZE = 4096 # Ограничение телеграма по величине сообщения.

    global DB_NAME
    DB_NAME = cfg['db_name']
    

    # Включаем логирование, чтобы не пропустить важные сообщения
    logging.basicConfig(level=logging.INFO, filename=cfg['log_file'],
                        filemode="w")
    # Делаем запись в лог о старте бота. Туда же будут
    # помещены запросы и ответы:
    msg = f"{time_begin} {BOT_TAG} - start"
    logging.info(msg)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """ Process /help command."""

    await message.reply(HELP_MSG)


@dp.message(Command("contacts"))
async def cmd_contacts(message: types.Message):
    """ Process /contacts command."""
    info_str = (f"user<{message.from_user.username}> - "
                f"user_id<{message.from_user.id}> - "
                f"Contacts request.")

    logging.info(info_str)
    await message.reply(CONTACTS_MSG)


@dp.message(Command("ver"))
async def cmd_ver(message: types.Message):
    """Process `/ver` command."""

    await message.reply(VER)


@dp.message(Command('keyboard'))
async def process_keyboard_command(message: types.Message):
    """Process /keyboard command."""
    await message.reply("Привет!", reply_markup=kb.greet_kb)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Process `/start` command."""
    await message.answer(START_GREETINGS)

@dp.message(Command('profile'))
@dp.message(F.text.contains('Мой профиль'))
async def get_profile(message: Message):
    async with ChatActionSender.typing(bot=bot, chat_id=message.from_user.id):
        text = (f'👉 Ваш телеграм ID: {message.from_user.id}\n'
                f'🚀 Вот ваша персональная ссылка на приглашение: '
                f'https://t.me/easy_refer_bot?start={message.from_user.id}')
    await message.answer(text, reply_markup=mentor_home_page_kb(message.from_user.id))


@dp.message(F.text.contains("Включить режим обучения"))
async def learning_on(message: Message):
    async with ChatActionSender.typing(bot=bot, chat_id=message.from_user.id):
        text = '📝 Обучение включено.'
        global learning_is_on
        learning_is_on = True
    await message.answer(text, reply_markup=mentor_home_page_kb(message.from_user.id))


@dp.message(F.text.contains("Включить режим общения"))
async def learning_off(message: Message):
    async with ChatActionSender.typing(bot=bot, chat_id=message.from_user.id):
        text = '️🗨️ Общение включено.'
        global learning_is_on
        learning_is_on = False
    await message.answer(text, reply_markup=mentor_home_page_kb(message.from_user.id))


@dp.message(F.text.contains("Очистить историю общения"))
async def conversation_clean_up(message: Message):
    async with ChatActionSender.typing(bot=bot, chat_id=message.from_user.id):
        text = '️🧹 История общения очищена.'
        global chat_history
        chat_history[message.from_user.id] = ""

    await message.answer(text, reply_markup=mentor_home_page_kb(message.from_user.id))


@dp.message(F.text.contains('Назад'))
async def cmd_back(message: Message):
    await message.answer(f'{message.from_user.first_name}, Выходим...',
                         reply_markup=mentor_keyboard(message.from_user.id))


def mentor_home_page_kb(user_telegram_id: int):
    kb_list = [[types.KeyboardButton(text="🔙 Назад")]]
    if user_telegram_id in mentors:
        kb_list.append([types.KeyboardButton(text="⚙️ Панель ментора")])
    return types.ReplyKeyboardMarkup(
        keyboard=kb_list,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Воспользуйтесь меню:"
    )


def admin_keyboard():
    print('Hello admin')
    kb_list = [[types.KeyboardButton(text="👤 Мой профиль")]]
    kb_list.append([types.KeyboardButton(text="⚙️ Панель администратора")])
    return types.ReplyKeyboardMarkup(
                                     keyboard=kb_list,
                                     resize_keyboard=True,
                                     one_time_keyboard=True,
                                     input_field_placeholder="Воспользуйтесь меню:"
                                     )


@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Process `/start` command."""
    if message.from_user.id == ADMIN_ID:
        response_text = "Здравствуйте, админ!"
        await message.answer(text=response_text, reply_markup=admin_keyboard())


def mentor_keyboard():
    print('Hello mentor')
    kb_list = [[types.KeyboardButton(text="👤 Мой профиль")]]
    kb_list.append([types.KeyboardButton(text="📝 Включить режим обучения")])
    kb_list.append([types.KeyboardButton(text="🗨️ Включить режим общения")])
    kb_list.append([types.KeyboardButton(text="🧹 Очистить историю общения")])
    return types.ReplyKeyboardMarkup(
                                     keyboard=kb_list,
                                     resize_keyboard=True,
                                     one_time_keyboard=True,
                                     input_field_placeholder="Воспользуйтесь меню:"
                                     )


@dp.message(F.text.contains("Панель ментора"))
@dp.message(Command("mentor"))
async def cmd_mentor(message: types.Message):
    """Process `/start` command."""
    if message.from_user.id == ADMIN_ID:
        response_text = "Здравствуйте, ментор!"
        await message.answer(text=response_text, reply_markup=mentor_keyboard())


async def get_anonimus_context(book: list):
    res = []
    if book:
        for user_id, username, question, answer in book:
            user_record = {"role": "user", "content": f"{question}"}
            assistant_record = {"role": "assistant", "content": f"{answer}"}
            res.append([user_record, assistant_record])
    return res


@dp.message(F.text)
async def handle_user_query(message: Message, bot: Bot):
    """Handle user queries."""

    # Получаем текущее время в часовом поясе ПК
    time_begin = datetime.now()

    # Подготавливаем книгу с предысторией обучающих диалогов с ментором.
    book = []
    logging.info("Learning book size before (bytes): %s", sys.getsizeof(learning_book))
    book.extend(learning_book)

    # Подготавливаем книгу с предысторией диалогов с данным юзером.
    if message.from_user.id in chat_history.keys():
        prehistory_book = chat_history[message.from_user.id]
    else:
        # Если в словаре chat_history нет записи о чате с этим пользователем,
        # загружаем историю общения с ним из базы данных.
        prehistory = await scan_chats_table(message.from_user.id)
        prehistory_book = await get_anonimus_context(prehistory)
        chat_history[message.from_user.id] = prehistory_book 
    logging.info("Prehistory book size (bytes): %s", sys.getsizeof(prehistory_book))
    book.extend(prehistory_book)

    user_query = message.text
    info_str = (f"\n{time_begin} bot<{cfg['bot_name']}> - "
                f"user<{message.from_user.username}> - "
                f"user_id<{message.from_user.id}> - "
                f"query<{user_query}>\n")

    logging.info(info_str)
    logging.info("book size before (bytes): %s", sys.getsizeof(book))
    await message.answer("пишет...")
    model_answer = mio.get_answer(user_query, args.models_config, book)
    logging.info("book size after (bytes): %s", sys.getsizeof(book))
    time_end = datetime.now()
    time_dif = time_begin - time_end
    seconds_in_day = 24 * 60 * 60
    work_time = divmod(time_dif.days * seconds_in_day + time_dif.seconds, 60)

    logging.info("%s", f'Working time: {abs(work_time[0])}'
                 f' minutes {abs(work_time[1])}'
                 ' seconds.')
    logging.info("%s", f"\n{time_end} bot<{cfg['bot_name']}> - "
                 f"user<{message.from_user.username}> - "
                 f"answer<{model_answer}>\n")

    if len(model_answer) < MAX_MESSAGE_SIZE:
        await message.answer(model_answer)
    else:
        await message.answer("Ответ будет на несколько сообщений:")
        parts = split_into_parts(model_answer, MAX_MESSAGE_SIZE)
        for part in parts:
            await message.answer(part)

    user_record = {"role": "user", "content": f"{user_query}"}
    assistant_record = {"role": "assistant", "content": f"{model_answer}"}
    full_record = [user_record, assistant_record]

    # Заменяем запись в словаре дополненной её версией.
    temp_book = chat_history[message.from_user.id]
    logging.info("book record size in dict (bytes): %s", sys.getsizeof(temp_book))
    if len(temp_book) > 0:
       logging.info("book record[-1] in dict (bytes): %s", temp_book[-1])
    logging.info("Answer full record size  (bytes): %s", sys.getsizeof(full_record))
    temp_book.append(full_record)
    logging.info("book record + full record size in dict (bytes): %s", sys.getsizeof(temp_book))
    chat_history[message.from_user.id] = temp_book

    # Добавляем эту же информацию в базу данных.
    async with aiosqlite.connect(DB_NAME) as db:
        if learning_is_on is True:
            learning_flag = "1"
        else:
            learning_flag = ""
        logging.info("Add record to database %s table <chats>.", DB_NAME)
        await db.execute('INSERT INTO chats VALUES (?, ?, ?, ?, ?)',
                         (message.from_user.id, message.from_user.username,
                          user_query, model_answer, learning_flag))
        await db.commit()

    
def parse_args():
    """CLI options parsing."""

    prog_name = os.path.basename(__file__).split(".")[0]

    parser = argparse.ArgumentParser(
        prog=prog_name,
        description="Telegram bot.",
        epilog="Text at the bottom of help",
    )
    parser.add_argument("-c", dest="bot_config", help="Bot configuration file path.")
    parser.add_argument("-m", dest="models_config", help="Model configuration file path.")
    return parser.parse_args()


async def create_table_users(manager, table_name='users_reg'):
    """PostgreSQL Create database table."""
    async with manager:
        columns = ['user_id INT8 PRIMARY KEY', 'gender VARCHAR(50)', 'age INT',
                   'full_name VARCHAR(255)', 'user_login VARCHAR(255) UNIQUE',
                   'photo TEXT', 'about TEXT', 'date_reg TIMESTAMP DEFAULT CURRENT_TIMESTAMP']
        await manager.create_table(table_name=table_name, columns=columns)


async def create_chats_table():
    """SQLite Create database table chats."""

    async with aiosqlite.connect(DB_NAME) as cursor:
        logging.info("Create table <chats> in database %s.", DB_NAME)
        await cursor.execute('CREATE TABLE IF NOT EXISTS chats '
                             '(user_id integer, user_name text, learning text, '
                             'question text, answer text)')
        await cursor.commit()


async def scan_lerning_book():
    """SQLite Read lerning book from  database table chats."""
    res = ''
    async with aiosqlite.connect(DB_NAME) as cursor:
        logging.info("Scan table <chats> by user id %s", MENTOR_ID)
        answer = await cursor.execute('SELECT user_id, user_name, question, answer '
                                      'FROM chats WHERE user_id = ? AND learning = "1"',
                                      (MENTOR_ID,))

        res = await answer.fetchall()
    return res


async def scan_chats_table(user_id: int = 0):
    """SQLite Read database table chats."""
    res = ''
    async with aiosqlite.connect(DB_NAME) as cursor:
        logging.info("Scan table <chats> by user id %s", user_id)
        answer = await cursor.execute('SELECT user_id, user_name, question, answer '
                                      'FROM chats WHERE user_id = ? AND learning = ""',
                                      (user_id,))
        res = await answer.fetchall()
        #logging.info(res)
    return res


async def set_commands():
    commands = [BotCommand(command='start', description='Старт'),
                BotCommand(command='admin', description='Администирование'),
                BotCommand(command='mentor', description='Обучение'),
                BotCommand(command='profile', description='Мой профиль')]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


async def start_bot():
    """ Функция, которая выполнится когда бот запустится. """
    
    await set_commands()


async def main():
    """Start bot."""
    dp.startup.register(start_bot)
    global args
    args = parse_args()
    init(args)
    await create_chats_table()  # Создание таблицы в базе данных
    global learning_book
    res = await scan_lerning_book()
    learning_book = await get_anonimus_context(res)
    text_book = []
    for question, answer in learning_book:
        text_book.append(f"Вопрос: {question['content']}\n")
        text_book.append(f"Ответ: {answer['content']}\n\n")

    logging.info('learning_book in main %s', learning_book)
    with open("learning_book.txt", "w", encoding="utf-8") as out:
        out.write(''.join(text_book))
    print(f"Bot <{cfg['bot_name']}>  started. See log in <{cfg['log_file']}>.")

    # Запуск процесса поллинга новых апдейтов
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
