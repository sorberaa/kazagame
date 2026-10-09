import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/kaza.db")
PORT = int(os.getenv("PORT", "10000"))

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
OWNER_ID = 8936384717
if OWNER_ID not in ADMIN_IDS:
    ADMIN_IDS.append(OWNER_ID)
