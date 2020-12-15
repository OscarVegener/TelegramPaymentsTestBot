from aiogram.dispatcher.filters.state import StatesGroup, State


class Purchase(StatesGroup):
    EnterQuantity = State()
    Approval = State()
    Payment = State()


class NewItem(StatesGroup):
    Name = State()
    Photo = State()
    Description = State()
    Currency = State()
    Price = State()
    Confirm = State()


class EditItem(StatesGroup):
    Name = State()
    Photo = State()
    Description = State()
    Currency = State()
    Price = State()
    Waiting = State()


class DeleteItem(StatesGroup):
    Confirm = State()


class Mailing(StatesGroup):
    Text = State()
    Language = State()
