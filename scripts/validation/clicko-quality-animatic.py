"""Build a local ÓRBITA planning preview from the prepared kit."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main(output):
    materials = output / "materials"
    face = materials / "SpaceGrotesk.ttf"
    poster = materials / "Unbounded.ttf"
    layout = [
        ("O futuro cabe\nnum curta.", "Aproximar a lente. Abrir passagem para os mundos.", "#12172c", "#f6bd68"),
        ("ÓRBITA", "O motivo atravessa planos de escalas diferentes.", "#17263e", "#9edcf2"),
        ("Mostra de curtas de\nficção científica.", "Situar a oferta. O texto permanece em repouso.", "#10192a", "#d0c5fb"),
        ("Confira a\nprogramação.", "Resolver o movimento no convite e liberar a leitura.", "#101822", "#ffd998"),
    ]
    rows = []
    for index, (title, purpose, background, accent) in enumerate(layout):
        image = Image.new("RGB", (360, 640), background)
        draw = ImageDraw.Draw(image)
        radius = [134, 86, 59, 31][index]
        draw.ellipse((180-radius, 233-radius, 180+radius, 233+radius), outline=accent, width=2)
        draw.ellipse((174, 227, 186, 239), fill=accent)
        draw.multiline_text((180, 433), title, fill="#fff5e6", anchor="mm", align="center", spacing=5,
                            font=ImageFont.truetype(str(poster if index == 1 else face), 43 if index == 1 else 34))
        path = output / f"animatic-{index + 1:02d}.png"
        image.save(path)
        rows.append({"file": path.name, "seconds": index * 3, "purpose": purpose,
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    video = output / "orbita-animatic-local.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-framerate", "1/3", "-i", str(output / "animatic-%02d.png"),
                    "-i", str(materials / "01-campo-estelar.wav"), "-t", "12", "-vf", "fps=24",
                    "-c:v", "libx264", "-threads", "1", "-pix_fmt", "yuv420p", "-c:a", "aac", str(video)], check=True)
    receipt = {"stage": "preparation", "apiSpendUsd": 0, "purpose": "Style and pace sketch, optional for the director",
               "frames": rows, "sha256": hashlib.sha256(video.read_bytes()).hexdigest(), "durationSeconds": 12}
    (output / "animatic.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output.resolve())
