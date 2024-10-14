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
import config
import argparse
import keyboard as kb
import model_io as mio
from model_tools import split_into_parts
import aiosqlite


chat_history = {}


time_begin = datetime.now()


# Диспетчер
dp = Dispatcher()


def init(cli_args: dict):
    """Initial settings for start."""

    # Load settings from configuration file.
    global cfg
    cfg = config.Config(cli_args.bot_config)

    global TETOKEN
    TETOKEN = cfg['tetoken']

    global BOT_TAG
    BOT_TAG = f"bot<{cfg['bot_name']}>"

    # Объект бота
    global bot
    bot = Bot(token=TETOKEN)

    global MOTO_BIKES
    MOTO_BIKES = ['Suzuki Djebel 200']

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
    MAX_MESSAGE_SIZE = 4096

    global DB_NAME
    DB_NAME = cfg['db_name']
    


    # Включаем логирование, чтобы не пропустить важные сообщения
    logging.basicConfig(level=logging.INFO, filename=cfg['log_file'],
                        filemode="a")
    # Делаем запись в лог о старте бота. Туда же будут
    # помещены запросы и ответы:
    msg = f"{time_begin} {BOT_TAG} - start"
    logging.info(msg)

async def record_user_query(text):
    # Record user queries and answers.
    query = text
    user_record = f'{"role": "user", "content": "{query}"\n}\n'
    asistant_record = "no"
    # asistant_record = f'{"role": "assistant", "content": "{model_answer}"\n}\n'
    full_reocord = f'{user_record}{asistant_record}'
    print('full_reocord', full_reocord)
    #with open(cfg['chat_log_file']//f"{message.from_user.id}.txt", 'a') as f:
    #with open(cfg['chat_log_file'], 'a', encoding="utf-8") as f:
    #    f.write(f'{full_reocord}')

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


@dp.message(F.text)
async def handle_user_query(message: Message, bot: Bot):
    """Handle user queries."""

    # Получаем текущее время в часовом поясе ПК
    time_begin = datetime.now()

    # Подготавливаем книгу с предысторией диалогов с текущим юзером.
    book = []
    if message.from_user.id in chat_history.keys():
        book = chat_history[message.from_user.id]
    else:
        prehistory = await scan_chats_table(message.from_user.id)
        print('prehistory', prehistory)
        prehistory_book = []
        if prehistory:
            for user_id, username, question, answer in prehistory:
                user_record = f'{{"role": "user", "content": "{question}"}}'
                asistant_record = f'{{"role": "assistant", "content": "{answer}"}}'
                prehistory_book.append(f'{user_record},\n{asistant_record}')
            print('prehistory_book', prehistory_book)
            book = prehistory_book

    query = message.text
    info_str = (f"\n{time_begin} bot<{cfg['bot_name']}> - "
                f"user<{message.from_user.username}> - "
                f"user_id<{message.from_user.id}> - "
                f"query<{query}>\n")

    logging.info(info_str)

    model_answer = mio.make_answer(query, args.models_config, book)
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
    #await message.answer( model_answer, parse_mode=ParseMode.MARKDOWN_V2)

    # await record_user_query(query)
    #print('query', query)
    user_record = f'{{"role": "user", "content": "{query}"}}'
    asistant_record = f'{{"role": "assistant", "content": "{model_answer}"}}'
    full_record = f'{user_record},\n{asistant_record}'
    print('full_reocord', full_record)
    
    book.append(full_record)

    # Добавляем эту же информацию в базу данных
    async with aiosqlite.connect(DB_NAME) as db:
        print(f"Add record to database {DB_NAME} table chats.")
        await db.execute('INSERT INTO chats VALUES (?, ?, ?, ?)',
                         (message.from_user.id, message.from_user.username, query, model_answer))
        res = await db.commit()
        print(res)

    if len(model_answer) < MAX_MESSAGE_SIZE:
        await message.answer(model_answer)
    else:
        await message.answer("Ответ будет на несколько сообщений:")
        parts = split_into_parts(model_answer, MAX_MESSAGE_SIZE)
        for part in parts:
            await message.answer(part)


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
        print(f"Create table <chats> in database {DB_NAME}.")
        res = await cursor.execute('CREATE TABLE IF NOT EXISTS chats '
                               '(user_id integer, user_name text,'
                               ' question text, answer text)')
        print(res)
        res = await cursor.commit()
        print(res)


async def scan_chats_table(user_id: int = 0):
    """SQLite Read database table chats."""
    res = ''
    async with aiosqlite.connect(DB_NAME) as cursor:
        print(f"Scan table <chats> by user id {user_id}.")
        answer = await cursor.execute('SELECT * '
                                      'FROM chats') # WHERE user_id = ?',
        #                               str(user_id))
        res = await answer.fetchall()
    print(res)
    return res


async def main():
    """Start bot."""
    global args
    args = parse_args()
    init(args)
    await create_chats_table()  # Создание таблицы в базе данных

    # exit()
    print(f"Bot <{cfg['bot_name']}>  started. See log in <{cfg['log_file']}>.")

    # Запуск процесса поллинга новых апдейтов
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
