import os

from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "netpulse_db")
DEVICES_COLLECTION = os.getenv("DEVICES_COLLECTION", "devices")
ALERTS_COLLECTION = os.getenv("ALERTS_COLLECTION", "alerts")