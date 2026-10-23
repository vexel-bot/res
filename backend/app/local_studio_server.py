"""Owned development server. Its parent closes stdin to request graceful shutdown."""

import sys
import threading

import uvicorn


def main():
    port = int(sys.argv[1])
    server = uvicorn.Server(uvicorn.Config("app.studio_app:app", host="127.0.0.1", port=port))

    def watch_parent():
        # No remotely reachable shutdown endpoint, shell, or process enumeration.
        sys.stdin.buffer.readline()
        server.should_exit = True

    threading.Thread(target=watch_parent, daemon=True).start()
    server.run()


if __name__ == "__main__":
    main()
