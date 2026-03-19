import pathlib
import time
from sdk.heartbeat import write_heartbeat

ROOT = pathlib.Path(__file__).resolve().parent
LOG_FILE = ROOT / "logs" / "app.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

while True:
    write_heartbeat(ROOT)
    with LOG_FILE.open("a", encoding="utf-8") as fp:
        fp.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} [INFO] template heartbeat\n")
    print("template heartbeat")
    time.sleep(15)
