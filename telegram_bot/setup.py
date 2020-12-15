import asyncio
import logging

from aiogram import Bot
from aiogram import Dispatcher
from aiogram.contrib.fsm_storage.redis import RedisStorage

from config import telegram_id, redis_host, redis_port
from language_middleware import setup_middleware


logging.basicConfig(format=u'%(filename)s [LINE:%(lineno)d] #%(levelname)-8s [%(asctime)s]  %(message)s',
                    level=logging.INFO)

storage = RedisStorage(host=redis_host, port=redis_port, db=5)

bot = Bot(token=telegram_id, parse_mode="HTML")
dp = Dispatcher(bot, storage=storage)

# multi language support
i18n = setup_middleware(dp)
# alias for gettext
_ = i18n.gettext
