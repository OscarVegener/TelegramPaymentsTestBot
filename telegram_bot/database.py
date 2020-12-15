from aiogram import types, Bot
from gino import Gino
from gino.schema import GinoSchemaVisitor
from sqlalchemy import (Column, Integer, BigInteger, String,
                        Sequence, TIMESTAMP, Boolean, JSON)
from sqlalchemy import sql

from config import db_pass, db_user, db_name, host

db = Gino()


class User(db.Model):
    __tablename__ = 'users'
    query: sql.Select

    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    user_id = Column(BigInteger)
    language = Column(String(2))
    full_name = Column(String(100))
    username = Column(String(50))

    def __repr__(self):
        return "<User(id='{}', fullname='{}', username='{}')>".format(
            self.id, self.full_name, self.username)


class Item(db.Model):
    __tablename__ = 'items'
    query: sql.Select

    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    name = Column(String(50))
    photo = Column(String(250))
    price = Column(Integer)  # penny
    currency = Column(String(3))
    description = Column(String(500))

    def __repr__(self):
        return "<Item(id='{}', name='{}', price='{}')>".format(
            self.id, self.name, self.price)


class Purchase(db.Model):
    __tablename__ = 'purchases'
    query: sql.Select

    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    buyer = Column(BigInteger)
    item_id = Column(Integer)
    total_price = Column(Integer)  # penny
    currency = Column(String(3))
    quantity = Column(Integer)
    purchase_time = Column(TIMESTAMP)
    shipping_address = Column(JSON)
    phone_number = Column(String(50))
    email = Column(String(200))
    receiver_name = Column(String(100))
    successful = Column(Boolean, default=False)


class DatabaseController:

    async def get_user(self, user_id):
        user = await User.query.where(User.user_id == user_id).gino.first()
        return user

    async def get_item(self, item_id):
        item = await Item.query.where(Item.id == item_id).gino.first()
        return item

    async def add_new_user(self, referral=None):
        user = types.User.get_current()
        old_user = await self.get_user(user.id)
        if old_user:
            return old_user
        new_user = User()
        new_user.user_id = user.id
        new_user.username = user.username
        new_user.full_name = user.full_name
        await new_user.create()
        return new_user

    async def set_language(self, language):
        user_id = types.User.get_current().id
        user = await self.get_user(user_id)
        await user.update(language=language).apply()

    async def count_users(self) -> int:
        total = await db.func.count(User.id).gino.scalar()
        return total

    async def get_items(self):
        items = await Item.query.gino.all()
        return items


async def create_db():
    await db.set_bind(f'postgresql://{db_user}:{db_pass}@{host}/{db_name}')
    db.gino: GinoSchemaVisitor
    await db.gino.drop_all()
    await db.gino.create_all()


async def reset_db():
    db.gino: GinoSchemaVisitor
    await db.gino.drop_all()
    await db.gino.create_all()
