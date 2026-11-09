"""Explicit, verified weight installation. Inference itself is always offline."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import urllib.request


def main():
    root=Path(__file__).resolve().parents[2]/"workers"/"material-effects"
    model=json.loads((root/"models.lock.json").read_text())["rvm"]
    target=root/model["file"]
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest()==model["sha256"]:
        print("RVM already installed and verified.")
        return
    with tempfile.TemporaryDirectory(prefix="clicko-rvm-install-") as directory:
        temporary=Path(directory)/"model.onnx"
        with urllib.request.urlopen(model["source"],timeout=60) as source,temporary.open("wb") as out:
            total=0
            while data:=source.read(1024*1024):
                total+=len(data)
                if total>model["sizeBytes"]:
                    raise ValueError("material_effect_model_size_mismatch")
                out.write(data)
        if temporary.stat().st_size!=model["sizeBytes"] or hashlib.sha256(temporary.read_bytes()).hexdigest()!=model["sha256"]:
            raise ValueError("material_effect_model_checksum_mismatch")
        shutil.copyfile(temporary,target)
    print("Installed RVM from the pinned official release. No media sent and no inference API used.")


if __name__=="__main__":
    main()
