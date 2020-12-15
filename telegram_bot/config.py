import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

telegram_id = os.getenv("TELEGRAM_TOKEN")
admin_id = int(os.getenv("ADMIN_ID"))
db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_name = os.getenv("DB_NAME")
tranzzo_token = os.getenv("TRANZZO_TOKEN")
host = os.getenv("DB_HOST")
redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")

I18N_DOMAIN = 'testbot'
BASE_DIR = Path(__file__).parent
LOCALES_DIR = BASE_DIR / 'locales'
