import asyncio
import datetime

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import CommandStart, CommandHelp
from aiogram.types import (Message, InlineKeyboardMarkup, InlineKeyboardButton,
                           CallbackQuery, LabeledPrice, PreCheckoutQuery)
from aiogram.utils.callback_data import CallbackData

import database
import states
from config import tranzzo_token, admin_id
from setup import dp, bot, _, i18n

db = database.DatabaseController()

buy_item = CallbackData("buy", "item_id")

edit_item = CallbackData("edit", "item_id")

delete_item = CallbackData("delete", "item_id")


@dp.message_handler(CommandStart())
async def register_user(message: types.Message):
    chat_id = message.from_user.id
    user = await db.add_new_user()
    id = user.id
    count_users = await db.count_users()

    languages_markup = InlineKeyboardMarkup(
        inline_keyboard=
        [
            [
                InlineKeyboardButton(text="Русский", callback_data="lang_ru")],
            [
                InlineKeyboardButton(text="English", callback_data="lang_en"),
                InlineKeyboardButton(text="Українська", callback_data="lang_uk"),
            ]
        ]
    )

    text = _("Приветствую вас!\n"
             "Сейчас в базе {count_users} человек!\n"
             "Просмотреть товары: /items").format(
        count_users=count_users)
    if message.from_user.id == admin_id:
        text += _("\n"
                  "Добавить новый товар: /add_item")
        text += _("\n"
                  "Разослать сообщение всем подписчикам: /tell_everyone")
    await bot.send_message(chat_id, text, reply_markup=languages_markup)


@dp.callback_query_handler(text_contains="lang")
async def change_language(call: CallbackQuery):
    await call.message.edit_reply_markup()
    lang = call.data[-2:]
    print("NEW LANGUAGE = {}".format(lang))
    await db.set_language(lang)
    await call.message.answer(_("Ваш язык был изменен", locale=lang))


@dp.message_handler(commands=["my_language"])
async def print_language(message: Message, locale):
    await message.reply(_('Your current language: <i>{language}<i>'.format(language=locale)))


@dp.message_handler(commands=["items"])
async def show_items(message: Message):
    all_items = await db.get_items()
    if not all_items:
        await message.answer(_("Товаров нету!"))
    for num, item in enumerate(all_items):
        text = _("<b>Товар</b> \t№{id}: <u>{name}</u>\n"
                 "<b>Описание:</b> {description}\n"
                 "<b>Цена:</b> \t{price:,} {currency}\n")
        if message.from_user.id == admin_id:
            markup = InlineKeyboardMarkup(
                inline_keyboard=
                [
                    [
                        InlineKeyboardButton(text=_("Купить"), callback_data=buy_item.new(item_id=item.id))
                    ],
                    [
                        InlineKeyboardButton(text=_("Изменить товар"), callback_data=edit_item.new(item_id=item.id))
                    ],
                    [
                        InlineKeyboardButton(text=_("Удалить товар"), callback_data=delete_item.new(item_id=item.id))
                    ]
                ]
            )
        else:
            markup = InlineKeyboardMarkup(
                inline_keyboard=
                [
                    [
                        InlineKeyboardButton(text=_("Купить"), callback_data=buy_item.new(item_id=item.id))
                    ],
                ]
            )

        await message.answer_photo(
            photo=item.photo,
            caption=text.format(
                id=item.id,
                name=item.name,
                description=item.description,
                price=item.price / 100,
                currency=item.currency
            ),
            reply_markup=markup
        )

        await asyncio.sleep(0.3)


@dp.callback_query_handler(buy_item.filter())
async def buying_item(call: CallbackQuery, callback_data: dict, state: FSMContext):
    item_id = int(callback_data.get("item_id"))
    await call.message.edit_reply_markup()

    # get info about item from db
    item = await database.Item.get(item_id)
    if not item:
        await call.message.answer(_("Такого товара не существует"))
        return

    text = _("Вы хотите купить товар \"<b>{name}</b>\" по цене: <i>{price:,} {currency}/шт.</i>\n"
             "Введите количество или нажмите /cancel").format(name=item.name,
                                                              price=item.price / 100,
                                                              currency=item.currency)
    await call.message.answer(text)
    await states.Purchase.EnterQuantity.set()

    await state.update_data(
        item=item,
        purchase=database.Purchase(
            item_id=item_id,
            purchase_time=datetime.datetime.now(),
            buyer=call.from_user.id,
            currency=item.currency
        )
    )


# cancel purchase

@dp.callback_query_handler(text_contains="cancel", state=states.Purchase)
async def approval(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    await call.message.answer(_("Вы отменили эту покупку"))
    await state.reset_state()


@dp.message_handler(commands=["cancel"], state=states.Purchase)
async def cancel_purchase(message: types.Message, state: FSMContext):
    await message.answer(_("Вы отменили эту покупку"))
    await state.reset_state()


# correct quantity
@dp.message_handler(regexp=r"^(\d+)$", state=states.Purchase.EnterQuantity)
async def enter_quantity(message: Message, state: FSMContext):
    quantity = int(message.text)
    async with state.proxy() as data:
        data["purchase"].quantity = quantity
        item = data["item"]
        amount = item.price * quantity
        data["purchase"].total_price = amount

    agree_button = InlineKeyboardButton(
        text=_("Согласен"),
        callback_data="agree"
    )
    change_button = InlineKeyboardButton(
        text=_("Ввести количество заново"),
        callback_data="change"
    )
    cancel_button = InlineKeyboardButton(
        text=_("Отменить покупку"),
        callback_data="cancel"
    )

    markup = InlineKeyboardMarkup(
        inline_keyboard=
        [
            [agree_button],
            [change_button],
            [cancel_button]
        ]
    )
    await message.answer(
        _("Хорошо, вы хотите купить <i>{quantity}</i> {name} по цене <b>{price:,} {currency}/шт.</b>\n\n"
          "Получится <b>{amount:,}</b>. Подтверждаете?").format(
            quantity=quantity,
            name=item.name,
            amount=amount / 100,
            price=item.price / 100,
            currency=item.currency
        ),
        reply_markup=markup)
    await states.Purchase.Approval.set()


# incorrect quantity
@dp.message_handler(state=states.Purchase.EnterQuantity)
async def not_quantity(message: Message):
    await message.answer(_("Неверное значение, введите число"))


# edit purchase
@dp.callback_query_handler(text_contains="change", state=states.Purchase.Approval)
async def approval(call: CallbackQuery):
    await call.message.edit_reply_markup()  # Убираем кнопки
    await call.message.answer(_("Введите количество товара заново."))
    await states.Purchase.EnterQuantity.set()


# proceed with purchase
@dp.callback_query_handler(text_contains="agree", state=states.Purchase.Approval)
async def approval(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()

    data = await state.get_data()
    purchase: database.Purchase = data.get("purchase")
    item: database.Item = data.get("item")

    # create purchase in db
    await purchase.create()

    await bot.send_message(chat_id=call.from_user.id,
                           text=_("Хорошо. Оплатите <b>{amount:,} {currency}</b> по методу указанному ниже и нажмите "
                                  "на кнопку ниже").format(amount=purchase.total_price, currency=item.currency))

    # data for provider
    currency = item.currency
    need_name = True
    need_phone_number = False
    need_email = False
    need_shipping_address = True

    await bot.send_invoice(chat_id=call.from_user.id,
                           title=item.name,
                           description=item.name,
                           payload=str(purchase.id),
                           start_parameter=str(purchase.id),
                           currency=currency,
                           prices=[
                               LabeledPrice(label=item.name, amount=purchase.total_price)
                           ],
                           provider_token=tranzzo_token,
                           need_name=need_name,
                           need_phone_number=need_phone_number,
                           need_email=need_email,
                           need_shipping_address=need_shipping_address
                           )
    await state.update_data(purchase=purchase)
    await states.Purchase.Payment.set()


@dp.pre_checkout_query_handler(state=states.Purchase.Payment)
async def checkout(query: PreCheckoutQuery, state: FSMContext):
    await bot.answer_pre_checkout_query(query.id, True)
    data = await state.get_data()
    purchase: database.Purchase = data.get("purchase")
    success = await check_payment(purchase)

    if success:
        await purchase.update(
            successful=True,
            shipping_address=query.order_info.shipping_address.to_python()
            if query.order_info.shipping_address
            else None,
            phone_number=query.order_info.phone_number,
            receiver=query.order_info.name,
            email=query.order_info.email
        ).apply()
        await state.reset_state()
        await bot.send_message(query.from_user.id, _("Спасибо за покупку"))
    else:
        await bot.send_message(query.from_user.id, _("Покупка не была подтверждена, попробуйте позже..."))


async def check_payment(purchase: database.Purchase):
    return True


# editing item

@dp.message_handler(user_id=admin_id, commands="continue", state=states.EditItem.Waiting)
async def continue_editing(message: types.Message, state: FSMContext):
    # reset state and restore state data in order to continue editing
    data = await state.get_data()
    item = data.get("item")
    await state.reset_state()
    await state.update_data(item=item)

    markup = InlineKeyboardMarkup(
        inline_keyboard=
        [
            [
                InlineKeyboardButton(text=_("Название"), callback_data="editing_name")
            ],
            [
                InlineKeyboardButton(text=_("Фото"), callback_data="editing_photo")
            ],
            [
                InlineKeyboardButton(text=_("Описание"), callback_data="editing_description")
            ],
            [
                InlineKeyboardButton(text=_("Валюта"), callback_data="editing_currency")
            ],
            [
                InlineKeyboardButton(text=_("Цена"), callback_data="editing_price")
            ]
        ]
    )
    await message.answer(_("Выберите что вы хотите изменить."), reply_markup=markup)


@dp.message_handler(user_id=admin_id, commands=["cancel"], state=states.EditItem)
async def cancel_editing(message: types.Message, state: FSMContext):
    await message.answer(_("Редактирования товара отменено."))
    await state.reset_state()


@dp.callback_query_handler(edit_item.filter(), user_id=admin_id)
async def editing_item(call: CallbackQuery, callback_data: dict, state: FSMContext):
    await call.message.edit_reply_markup()
    item_id = int(callback_data.get("item_id"))
    item = await db.get_item(item_id)
    await state.update_data(item=item)
    markup = InlineKeyboardMarkup(
        inline_keyboard=
        [
            [
                InlineKeyboardButton(text=_("Название"), callback_data="editing_name")
            ],
            [
                InlineKeyboardButton(text=_("Фото"), callback_data="editing_photo")
            ],
            [
                InlineKeyboardButton(text=_("Описание"), callback_data="editing_description")
            ],
            [
                InlineKeyboardButton(text=_("Валюта"), callback_data="editing_currency")
            ],
            [
                InlineKeyboardButton(text=_("Цена"), callback_data="editing_price")
            ]
        ]
    )
    await call.message.answer(_("Выберите что вы хотите изменить."), reply_markup=markup)


@dp.callback_query_handler(text_contains="editing_name")
async def edit_name(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    await states.EditItem.Name.set()
    await call.message.answer(_("Введите новое название."))


@dp.message_handler(user_id=admin_id, state=states.EditItem.Name, content_types=types.ContentTypes.TEXT)
async def edit_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    item: db.Item = data.get("item")
    item.name = message.text
    await message.answer(_("Имя товара было изменено на {name}, чтобы продолжить редактирование введите /continue или"
                           " /finish чтобы закончить.".format(name=item.name)))
    await state.update_data(item=item)
    await states.EditItem.Waiting.set()


@dp.callback_query_handler(text_contains="editing_photo")
async def edit_photo(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    await states.EditItem.Photo.set()
    await call.message.answer(_("Пришлите новую фотографию товара(не документ)."))


@dp.message_handler(user_id=admin_id, state=states.EditItem.Photo, content_types=types.ContentTypes.PHOTO)
async def edit_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1].file_id
    data = await state.get_data()
    item: db.Item = data.get("item")
    item.photo = photo
    await message.answer(_("Фото было изменено, чтобы продолжить редактирование введите /continue или"
                           " /finish чтобы закончить."))
    await state.update_data(item=item)
    await states.EditItem.Waiting.set()


@dp.callback_query_handler(text_contains="editing_description")
async def edit_description(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    await states.EditItem.Description.set()
    await call.message.answer(_("Введите новое описание."))


@dp.message_handler(user_id=admin_id, state=states.EditItem.Description, content_types=types.ContentTypes.TEXT)
async def edit_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    item: db.Item = data.get("item")
    item.description = message.text
    await message.answer(_("Описание было изменено, чтобы продолжить редактирование введите /continue или"
                           " /finish чтобы закончить."))
    await state.update_data(item=item)
    await states.EditItem.Waiting.set()


@dp.callback_query_handler(text_contains="editing_currency")
async def edit_currency(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    await states.EditItem.Currency.set()
    markup = InlineKeyboardMarkup(
        inline_keyboard=
        [
            [InlineKeyboardButton(text="RUB", callback_data="RUB")],
            [InlineKeyboardButton(text="UAH", callback_data="UAH")],
            [InlineKeyboardButton(text="USD", callback_data="USD")],
        ]
    )
    await call.message.answer(_("Выберите новую валюту."), reply_markup=markup)


@dp.callback_query_handler(state=states.EditItem.Currency)
async def edit_currency(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    item = data.get("item")
    item.currency = call.data
    await call.message.answer(
        _("Валюта была изменена на {currency}, чтобы продолжить редактирование введите /continue или"
          " /finish чтобы закончить.").format(currency=item.currency))
    await state.update_data(item=item)
    await states.EditItem.Waiting.set()


@dp.callback_query_handler(text_contains="editing_price")
async def edit_price(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    await states.EditItem.Price.set()
    await call.message.answer(_("Введите новую цену в копейках."))


@dp.message_handler(user_id=admin_id, state=states.EditItem.Price, regexp=r"^(\d+)$")
async def edit_price(message: types.Message, state: FSMContext):
    data = await state.get_data()
    item = data.get("item")
    item.price = int(message.text)
    await message.answer(
        _("Цена была изменена, новая цена: {price}\nЧтобы продолжить редактирование введите /continue или"
          " /finish чтобы закончить.").format(price=(item.price / 100)))
    await state.update_data(item=item)
    await states.EditItem.Waiting.set()


@dp.message_handler(user_id=admin_id, state=states.EditItem.Price)
async def edit_price(message: types.Message, state: FSMContext):
    await message.answer(_("Цена введена неверно!"))


@dp.message_handler(user_id=admin_id, commands="finish", state=states.EditItem.Waiting)
async def finish_editing(message: types.Message, state: FSMContext):
    data = await state.get_data()
    edited_item = data.get("item")
    item = await db.get_item(edited_item.id)
    update_request = item.update(name=edited_item.name,
                                 photo=edited_item.photo,
                                 price=edited_item.price,
                                 currency=edited_item.currency,
                                 description=edited_item.description)
    await update_request.apply()
    await state.reset_state()


# deleting item


@dp.message_handler(user_id=admin_id, commands=["cancel"], state=states.DeleteItem)
async def cancel_deleting(message: types.Message, state: FSMContext):
    await message.answer(_("Удаление товара отменено."))
    await state.reset_state()


@dp.callback_query_handler(delete_item.filter(), user_id=admin_id)
async def deleting_item(call: CallbackQuery, callback_data: dict, state: FSMContext):
    await call.message.edit_reply_markup()
    item_id = int(callback_data.get("item_id"))
    item = await db.get_item(item_id)
    await state.update_data(item=item)
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=_("Да"), callback_data="deleting_confirm")
            ],
            [
                InlineKeyboardButton(text=_("Нет"), callback_data="deleting_cancel")
            ]
        ]
    )
    await call.message.answer(_("Подтверждаете ли вы удаление товара {name}").format(name=item.name),
                              reply_markup=markup)
    await states.DeleteItem.Confirm.set()


@dp.callback_query_handler(text_contains="deleting_confirm", state=states.DeleteItem.Confirm)
async def delete_item_confirm(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    data = await state.get_data()
    item_to_delete: db.Item = data.get("item")
    item = await db.get_item(item_to_delete.id)
    await item.delete()
    await call.message.answer(_("Товар был удалён!"))
    await state.reset_state()


@dp.callback_query_handler(text_contains="deleting_cancel", state=states.DeleteItem.Confirm)
async def delete_item_cancel(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    await call.message.answer(_("Удаление отменено."))
    await state.reset_state()


# help


@dp.message_handler(CommandHelp())
async def show_help(message: types.Message):
    chat_id = message.from_user.id

    languages_markup = InlineKeyboardMarkup(
        inline_keyboard=
        [
            [
                InlineKeyboardButton(text="Русский", callback_data="lang_ru")],
            [
                InlineKeyboardButton(text="English", callback_data="lang_en"),
                InlineKeyboardButton(text="Українська", callback_data="lang_uk"),
            ]
        ]
    )

    text = _("Просмотреть товары: /items")
    if message.from_user.id == admin_id:
        text += _("\n"
                  "Добавить новый товар: /add_item")
        text += _("\n"
                  "Разослать сообщение всем подписчикам: /tell_everyone")
    await bot.send_message(chat_id, text, reply_markup=languages_markup)
