import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
DB_PATH = os.getenv("DB_PATH", "bot_database.db")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
FREE_DAILY_LIMIT = int(os.getenv("FREE_DAILY_LIMIT", "10"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Set it in your .env file.")

if not ADMIN_IDS:
    print("⚠️  WARNING: No ADMIN_IDS set. Admin panel will be inaccessible.")
