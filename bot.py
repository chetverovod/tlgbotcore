import os
import asyncio
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

    # Включаем логирование, чтобы не пропустить важные сообщения
    logging.basicConfig(level=logging.INFO, filename=cfg['log_file'],
                        filemode="a")
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


@dp.message(F.text)
async def handle_user_query(message: Message, bot: Bot):
    """Handle user queries."""

    # Получаем текущее время в часовом поясе ПК
    time_begin = datetime.now()
    query = message.text
    info_str = (f"\n{time_begin} bot<{cfg['bot_name']}> - "
                f"user<{message.from_user.username}> - "
                f"user_id<{message.from_user.id}> - "
                f"query<{query}>\n")

    logging.info(info_str)

    model_answer = mio.make_answer(query, args.models_config)
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


async def main():
    """Start bot."""

    global args
    args = parse_args()
    init(args)
    print(f"Bot <{cfg['bot_name']}>  started. See log in <{cfg['log_file']}>.")

    # Запуск процесса поллинга новых апдейтов
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
