import pathlib
import time

from sdk.heartbeat import write_heartbeat


ROOT = pathlib.Path(__file__).resolve().parent
LOG_FILE = ROOT / "logs" / "app.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    while True:
        write_heartbeat(ROOT, extra={"script": "my-python-task"})
        message = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} [INFO] my-python-task alive\n"
        with LOG_FILE.open("a", encoding="utf-8") as fp:
            fp.write(message)
        print(message.strip())
        time.sleep(15)


if __name__ == "__main__":
    main()
