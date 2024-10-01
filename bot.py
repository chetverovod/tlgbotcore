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
from io import BytesIO
import config
# from bot_config import TETOKEN
import re
import keyboard as kb
import model_io as mio


# Load settings from configuration file.
cfg = config.Config('bot_settings.cfg')
TETOKEN = cfg['tetoken']
ver = "0.1.1"

help_msg = "Просто напишите вопрос и бот ответит, основываясь только" \
           " на сведениях, указанных в руководстве по эксплуатации."

moto_bikes = ['Suzuki Djebel 200']

link_to_service_manual = 'https://disk.yandex.ru/i/gWonEIVopPJnGA'

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# Объект бота
bot = Bot(token=TETOKEN)

# Диспетчер
dp = Dispatcher()

# Делаем запись в лог о старте бота в этот же лог будут
# помещены запросы и ответы:
with open(cfg['log_file'], 'a') as f:
    time_begin = datetime.now()
    f.write(f"\n{time_begin} Bot<{cfg['bot_name']}> - start\n")

# Хэндлер на команду /help
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.reply(help_msg)


# Хэндлер на команду /ver
@dp.message(Command("ver"))
async def cmd_verp(message: types.Message):
    await message.reply(ver)


@dp.message(Command('terms'))
async def process_terms_command(message: types.Message):
    await message.reply('terms', reply=False)


# Хэндлер на команду /keyboard
@dp.message(Command('keyboard'))
async def process_keyboard_command(message: types.Message):
    await message.reply("Привет!", reply_markup=kb.greet_kb)


# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет!\n Этот бот отвечает на вопросы"
                         + " по обслуживанию мотоциклов"
                         + " пока только одной модели:"
                         + f" {moto_bikes}.\nПока только по первым двум "
                         + "главам руководства"
                         + f" по эксплуатации:{link_to_service_manual}\n"
                         + f"{help_msg}"
                         )


@dp.message(F.text)
async def handle_user_query(message: Message, bot: Bot):
    # Получаем текущее время в часовом поясе ПК

    time_begin = datetime.now()
    query = message.text
    print(f'Query: {query}')
    with open(cfg['log_file'], 'a') as f:
        f.write(f"\n{time_begin} Bot<{cfg['bot_name']}> - query: {query}\n")

    model_answer = mio.make_answer(query)
    time_end = datetime.now()
    time_dif = time_begin - time_end
    seconds_in_day = 24 * 60 * 60
    work_time = divmod(time_dif.days * seconds_in_day + time_dif.seconds, 60)
    print(f'Working time: {abs(work_time[0])} minutes {abs(work_time[1])}'
          + ' seconds.')
    #await message.answer('вопрос:\n' + query + '\nответ:\n' + model_answer)
    with open(cfg['log_file'], 'a') as f:
        f.write(f"\n{time_end} Bot<{cfg['bot_name']}> - answer: {model_answer}\n")
    await message.answer(model_answer)


@dp.message(F.text)
async def echo_with_time(message: Message):

    # Получаем текущее время в часовом поясе ПК
    time_now = datetime.now().strftime('%H:%M')

    # Создаём подчёркнутый текст
    added_text = html.underline(f"Создано в {time_now}")

    # Отправляем новое сообщение с добавленным текстом
    await message.answer(f"{message.text}\n\n{added_text}", parse_mode="HTML")


# Запуск процесса поллинга новых апдейтов
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
