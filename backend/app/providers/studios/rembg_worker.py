"""Process entry point kept separate from the API and render workers."""

import hashlib
import os
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 5:
        raise SystemExit(2)
    source = Path(sys.argv[1])
    destination = Path(sys.argv[2])
    model = Path(sys.argv[3])
    expected = sys.argv[4]
    if model.name != "u2netp.onnx" or hashlib.sha256(model.read_bytes()).hexdigest() != expected:
        raise SystemExit(3)
    os.environ["U2NET_HOME"] = str(model.parent)
    os.environ["HF_HUB_OFFLINE"] = "1"
    from rembg import new_session, remove

    session = new_session("u2netp", providers=["CPUExecutionProvider"])
    destination.write_bytes(remove(source.read_bytes(), session=session, force_return_bytes=True))


if __name__ == "__main__":
    main()
