from asyncio import sleep

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import admin_id
from setup import dp, _, bot
from states import NewItem, Mailing
from database import Item, User


@dp.message_handler(user_id=admin_id, commands=["cancel"], state=NewItem)
async def cancel(message: types.Message, state: FSMContext):
    await message.answer(_("Вы отменили создание товара"))
    await state.reset_state()


@dp.message_handler(user_id=admin_id, commands=["add_item"])
async def add_item(message: types.Message):
    await message.answer(_("Введите название товара или нажмите /cancel"))
    await NewItem.Name.set()


@dp.message_handler(user_id=admin_id, state=NewItem.Name, content_types=types.ContentTypes.TEXT)
async def enter_name(message: types.Message, state: FSMContext):
    name = message.text
    item = Item()
    item.name = name

    await message.answer(_("Название: {name}"
                           "\nПришлите мне фотографию товара (не документ) или нажмите /cancel").format(name=name))

    await NewItem.Photo.set()
    await state.update_data(item=item)


@dp.message_handler(user_id=admin_id, state=NewItem.Photo, content_types=types.ContentType.PHOTO)
async def add_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1].file_id
    data = await state.get_data()
    item: Item = data.get("item")
    item.photo = photo
    await message.answer_photo(
        photo=photo,
        caption=_("Название: {name}"
                  "\nВведите описание или нажмите /cancel для отмены").format(name=item.name))
    await NewItem.Description.set()
    await state.update_data(item=item)


@dp.message_handler(user_id=admin_id, state=NewItem.Description, content_types=types.ContentTypes.TEXT)
async def enter_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    item: Item = data.get("item")
    item.description = message.text
    markup = InlineKeyboardMarkup(
        inline_keyboard=
        [
            [InlineKeyboardButton(text="RUB", callback_data="RUB")],
            [InlineKeyboardButton(text="UAH", callback_data="UAH")],
            [InlineKeyboardButton(text="USD", callback_data="USD")],
        ]
    )
    await message.answer(_("Выберите валюту для цены на товар."),
                         reply_markup=markup)

    await NewItem.Currency.set()
    await state.update_data(item=item)


@dp.callback_query_handler(user_id=admin_id, state=NewItem.Currency)
async def enter_currency(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    data = await state.get_data()
    item: Item = data.get("item")
    item.currency = call.data

    await call.message.answer(_("Пришлите мне цену товара в копейках или нажмите /cancel для отмены"))
    await NewItem.Price.set()
    await state.update_data(item=item)


@dp.message_handler(user_id=admin_id, state=NewItem.Price, regexp=r"^(\d+)$")
async def enter_price(message: types.Message, state: FSMContext):
    data = await state.get_data()
    item: Item = data.get("item")
    item.price = int(message.text)

    markup = InlineKeyboardMarkup(
        inline_keyboard=
        [
            [InlineKeyboardButton(text=_("Да"), callback_data="confirm")],
            [InlineKeyboardButton(text=_("Ввести заново"), callback_data="change")],
        ]
    )
    await message.answer(_("Цена: {price:,}\n"
                           "Подтверждаете? Нажмите /cancel чтобы отменить").format(price=item.price / 100),
                         reply_markup=markup)
    await NewItem.Confirm.set()
    await state.update_data(item=item)


@dp.message_handler(user_id=admin_id, state=NewItem.Price)
async def reenter_price(message: types.Message, state: FSMContext):
    await message.answer(_("Цена введена неверно!"))


@dp.callback_query_handler(user_id=admin_id, text_contains="change", state=NewItem.Confirm)
async def enter_price(call: types.CallbackQuery):
    await call.message.edit_reply_markup()
    await call.message.answer(_("Введите заново цену товара в копейках"))
    await NewItem.Price.set()


@dp.callback_query_handler(user_id=admin_id, text_contains="confirm", state=NewItem.Confirm)
async def enter_price(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    data = await state.get_data()
    item: Item = data.get("item")
    await item.create()
    await call.message.answer(_("Товар удачно создан."))
    await state.reset_state()


# send messages for users with specified locale

@dp.message_handler(user_id=admin_id, commands=["cancel"], state=Mailing)
async def cancel(message: types.Message, state: FSMContext):
    await message.answer(_("Вы отменили создание рассылки."))
    await state.reset_state()


@dp.message_handler(user_id=admin_id, commands=["tell_everyone"])
async def mailing(message: types.Message):
    await message.answer(_("Пришлите текст рассылки"))
    await Mailing.Text.set()


@dp.message_handler(user_id=admin_id, state=Mailing.Text)
async def mailing(message: types.Message, state: FSMContext):
    text = message.text
    await state.update_data(text=text)
    markup = InlineKeyboardMarkup(
        inline_keyboard=
        [
            [InlineKeyboardButton(text="Русский", callback_data="ru")],
            [InlineKeyboardButton(text="English", callback_data="en")],
            [InlineKeyboardButton(text="Україньска", callback_data="uk")],
        ]
    )
    await message.answer(_("Пользователям на каком языке разослать это сообщение?\n\n"
                           "Текст:\n"
                           "{text}").format(text=text),
                         reply_markup=markup)
    await Mailing.Language.set()


@dp.callback_query_handler(user_id=admin_id, state=Mailing.Language)
async def mailing_start(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get("text")
    await state.reset_state()
    await call.message.edit_reply_markup()

    users = await User.query.where(User.language == call.data).gino.all()
    for user in users:
        try:
            await bot.send_message(chat_id=user.user_id,
                                   text=text)
            await sleep(0.3)
        except Exception:
            pass
    await call.message.answer(_("Рассылка выполнена."))

