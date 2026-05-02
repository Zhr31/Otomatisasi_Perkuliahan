"""
config.py — Memuat semua konfigurasi dari file .env
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# ============================================
# Edlink
# ============================================
EDLINK_EMAIL = os.getenv("EDLINK_EMAIL", "")
EDLINK_PASSWORD = os.getenv("EDLINK_PASSWORD", "")
EDLINK_BASE_URL = "https://edlink.id"

# ============================================
# TickTick
# ============================================
TICKTICK_CLIENT_ID = os.getenv("TICKTICK_CLIENT_ID", "")
TICKTICK_CLIENT_SECRET = os.getenv("TICKTICK_CLIENT_SECRET", "")
TICKTICK_ACCESS_TOKEN = os.getenv("TICKTICK_ACCESS_TOKEN", "")
TICKTICK_API_URL = "https://api.ticktick.com/open/v1"

# Priority mapping: Edlink content type → TickTick priority
# TickTick: 0=None, 1=Low, 3=Medium, 5=High
PRIORITY_MAP = {
    "P1": 5,  # Ujian, Vicon, Quiz → High
    "P2": 3,  # Video YouTube → Medium
    "P3": 1,  # Materi PDF/Word/PPT → Low
    "P4": 0,  # Absensi Komentar → None
}

# ============================================
# Gemini AI
# ============================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

# ============================================
# Google Drive
# ============================================
GDRIVE_ROOT_FOLDER_ID = os.getenv("GDRIVE_ROOT_FOLDER_ID", "")
GDRIVE_CREDENTIALS_FILE = ROOT_DIR / "credentials.json"
GDRIVE_TOKEN_FILE = ROOT_DIR / "token.json"

# ============================================
# Paths
# ============================================
DATA_DIR = ROOT_DIR / "data"
DOWNLOADS_DIR = DATA_DIR / "downloads"
STATE_FILE = DATA_DIR / "state.json"

# Buat folder jika belum ada
DATA_DIR.mkdir(exist_ok=True)
DOWNLOADS_DIR.mkdir(exist_ok=True)
