"""Install the pinned upstream assembler for the Clicko API and media worker."""

import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.request import urlretrieve
import venv
from zipfile import ZipFile

# Keep the installation compatible with the provider without importing the API.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.providers.studios.moneyprinterturbo import REVISION, runtime_root  # noqa: E402


def provision():
    root = runtime_root()
    root.mkdir(parents=True, exist_ok=True)
    source = root / f"MoneyPrinterTurbo-{REVISION}"
    if not source.is_dir():
        with TemporaryDirectory(dir=root) as staging:
            staging = Path(staging)
            urlretrieve(f"https://codeload.github.com/harry0703/MoneyPrinterTurbo/zip/{REVISION}", staging / "source.zip")
            with ZipFile(staging / "source.zip") as archive:
                archive.extractall(staging)
            (staging / source.name).replace(source)
    environment = root / "venv"
    executable = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not executable.is_file():
        venv.EnvBuilder(with_pip=True).create(environment)
    subprocess.run(
        [str(executable), "-m", "pip", "install", "moviepy==2.2.1", "imageio-ffmpeg==0.6.0",
         "loguru==0.7.3", "toml==0.10.2", "pydantic>=2,<3", "khatt[video]==0.4.0",
         "requests>=2,<3", "filelock>=4,<5", "pyyaml>=6,<7", "pydub==0.25.1", "pyjwt>=2,<3"],
        check=True,
    )
    environment_vars = {**os.environ, "MPT_HOME": str(root / "runtime")}
    subprocess.run(
        [str(executable), "-I", "-c",
         "import sys; sys.path.insert(0, sys.argv[1]); from app.services.video import concat_video_clips_with_ffmpeg",
         str(source)], env=environment_vars, check=True,
    )
    print(f"MoneyPrinterTurbo {REVISION} instalado em {source}")


if __name__ == "__main__":
    provision()
