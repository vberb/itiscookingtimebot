import logging

import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

from datetime import datetime


logging.basicConfig(level=logging.INFO)


bot = Bot(token='<TOKEN>')
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# States
class Form(StatesGroup):
    boil_time = State()
    boil = State()


# Configure ReplyKeyboardMarkup's
markupGoCancel = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
markupGoCancel.add("Go", "Cancel")

markupTimeCancel = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
markupTimeCancel.add("8", "10", "12")
markupTimeCancel.add("Cancel")

markupCancel = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
markupCancel.add("Cancel")


# --- CANCEL ---
@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Cancelling state %r', current_state)
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Cancelled.', reply_markup=types.ReplyKeyboardRemove())


# --- STATUS ---
@dp.message_handler(state='*', commands='status')
@dp.message_handler(Text(equals='status', ignore_case=True), state='*')
async def status_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    status = f'current_state: {current_state}'

    async with state.proxy() as data:
        for key in data:
            status += f', {key}: {data[key]}'

    logging.info('Getting status: %r', status)
    await message.reply(f'{status}')


# --- START ---
@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    logging.info('Entering state Boil Time')
    await Form.boil_time.set()
    await message.reply("How many minutes to boil? Choose option from below or enter your own.",
                        reply_markup=markupTimeCancel)


# --- BOIL TIME ---
@dp.message_handler(lambda message: message.text.isdigit(), state=Form.boil_time)
async def boil_time(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        boil_time = int(message.text)
        if boil_time > 15:  # egg is already hard boiled in 12 minutes
            await message.reply("This is too long.")
            return
        data['boil_time'] = boil_time
    logging.info('Entering state Boil')
    await Form.next()
    await message.reply("When water is boiling push <Go>.", reply_markup=markupGoCancel)


# --- BOIL ---
@dp.message_handler(Text(equals='go', ignore_case=True), state=Form.boil)
async def boil_begin(message: types.Message, state: FSMContext):
    timestamp = datetime.now()
    async with state.proxy() as data:
        data['boil'] = timestamp
    await message.reply(f"Boiling for {data['boil_time']} minutes. I`ll text you, when ready ;)",
                        reply_markup=markupCancel)
    # BOILING!!!
    logging.info('Begin boil')
    await asyncio.sleep(data['boil_time'] * 60)  # 60 = seconds in a minute
    logging.info('End boil')
    async with state.proxy() as data:
        if data['boil'] and data['boil'] != timestamp:
            return  # we are in an other iteration, do noting more
    # READY!
    # check if we are not in a ghost handler
    if await state.get_state() is not None:
        await message.reply("Egg is ready!", reply_markup=types.ReplyKeyboardRemove())

    # Finish conversation
    logging.info('Finishing')
    await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
