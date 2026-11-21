import win32evtlog
import configparser
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    app_folder = Path(sys.executable).resolve().parent
else:
    app_folder = Path(__file__).resolve().parent

config_path = app_folder / "config.ini"

config = configparser.ConfigParser()

if not config.read(config_path):
    raise FileNotFoundError(f"Could not read {config_path}")

host = config["server"]["host"]
port = config.getint("server", "port")

if not 1 <= port <= 65535:
    raise ValueError("Port must be between 1 and 65535")

server_url = f"http://{host}:{port}"
print(server_url)

