from __future__ import annotations

import socketserver
import threading
from contextlib import AbstractContextManager
from dataclasses import dataclass, field


@dataclass
class CapturedSMTPMessage:
    mail_from: str
    rcpt_to: list[str]
    data: bytes


class _SMTPHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        self.server.messages = getattr(self.server, "messages", [])
        self.server.current_mail_from = ""
        self.server.current_rcpt_to = []
        self.wfile.write(b"220 localhost Simple SMTP\r\n")
        while True:
            raw = self.rfile.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace").strip()
            upper = line.upper()
            if upper.startswith("EHLO") or upper.startswith("HELO"):
                self.wfile.write(b"250-localhost\r\n250 OK\r\n")
            elif upper.startswith("MAIL FROM:"):
                self.server.current_mail_from = line.split(":", 1)[1].strip()
                self.wfile.write(b"250 OK\r\n")
            elif upper.startswith("RCPT TO:"):
                self.server.current_rcpt_to.append(line.split(":", 1)[1].strip())
                self.wfile.write(b"250 OK\r\n")
            elif upper == "DATA":
                self.wfile.write(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                data_lines: list[bytes] = []
                while True:
                    data = self.rfile.readline()
                    if data == b".\r\n":
                        break
                    data_lines.append(data)
                self.server.messages.append(
                    CapturedSMTPMessage(
                        mail_from=self.server.current_mail_from,
                        rcpt_to=list(self.server.current_rcpt_to),
                        data=b"".join(data_lines),
                    )
                )
                self.wfile.write(b"250 Queued\r\n")
            elif upper == "QUIT":
                self.wfile.write(b"221 Bye\r\n")
                break
            else:
                self.wfile.write(b"250 OK\r\n")


class _ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


class DummySMTPServer(AbstractContextManager["DummySMTPServer"]):
    def __init__(self) -> None:
        self.server = _ReusableTCPServer(("127.0.0.1", 0), _SMTPHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def host(self) -> str:
        return self.server.server_address[0]

    @property
    def port(self) -> int:
        return int(self.server.server_address[1])

    @property
    def messages(self) -> list[CapturedSMTPMessage]:
        return list(getattr(self.server, "messages", []))

    def __enter__(self) -> "DummySMTPServer":
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
