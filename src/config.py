from pathlib import Path
import os

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DATABASE_PATH = PROJECT_ROOT / os.environ["DATABASE_PATH"]
SECRET_KEY = os.environ["SECRET_KEY"]
DEFAULT_PORT = os.environ["PORT"]
PROFILE_PICTURE_FOLDER = PROJECT_ROOT / 'src' / 'static' / "profile-pictures"