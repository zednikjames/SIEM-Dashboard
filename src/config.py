from pathlib import Path
import os

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

USER_DATABASE_PATH = PROJECT_ROOT / os.environ["USER_DATABASE_PATH"]
AUDIT_DATABASE_PATH = PROJECT_ROOT / os.environ["AUDIT_DATABASE_PATH"]
ARCHIVE_DATABASE_PATH = PROJECT_ROOT / os.environ["ARCHIVE_DATABASE_PATH"]
SECRET_KEY = os.environ["SECRET_KEY"]
DEFAULT_PORT = os.environ["PORT"]
PROFILE_PICTURE_FOLDER = PROJECT_ROOT / 'src' / 'static' / "profile-pictures"