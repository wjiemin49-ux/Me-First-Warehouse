import pathlib
import sys
import time
from sdk.heartbeat import write_heartbeat

ROOT = pathlib.Path(__file__).resolve().parent
LOG_FILE = ROOT / "logs" / "app.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

for index in range(3):
    write_heartbeat(ROOT, extra={"iteration": index})
    with LOG_FILE.open("a", encoding="utf-8") as fp:
        fp.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} [ERROR] flaky demo step {index}\n")
    print(f"flaky demo step {index}")
    time.sleep(4)

print("flaky demo crashing now")
sys.exit(13)
