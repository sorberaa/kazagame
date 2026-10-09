import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/kaza.db")
PORT = int(os.getenv("PORT", "10000"))

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
SUPER_ADMINS = [8653358704, 8936384717]
for sa in SUPER_ADMINS:
    if sa not in ADMIN_IDS:
        ADMIN_IDS.append(sa)
OWNER_ID = 8653358704

