"""Controlled re-encodes of retained API intermediates; never API admission."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
SOURCE = STUDY / "temporal-matte-native14-balanced-vector-guard-svg-subtract-full"
OUT = STUDY / "temporal-matte-svg-subtract-final-encode-study-v2"


def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def pixels(video):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
                         check=True, capture_output=True, timeout=30).stdout
    assert len(raw) == 16 * 320 * 320 * 3
    return raw


def observed(raw, check):
    frame, x, y = check["frame"], check["x"], check["y"]
    return [sum(raw[(frame * 320 * 320 + (y + dy) * 320 + x + dx) * 3 + c]
                for dx in range(2) for dy in range(2)) / 4 for c in range(3)]


def main():
    assert not OUT.exists(), "Do not overwrite evidence"
    OUT.mkdir()
    version = subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True, text=True).stdout.splitlines()[0]
    records = []
    duration = str(16 / 30)
    graph = (f"color=c=0x000000:s=320x320:r=30.0:d={duration}[base0];"
             f"[0:v]trim=start=0.0:duration={duration},setpts=(PTS-STARTPTS)/1.0,fps=30.0,"
             f"trim=duration={duration},settb=AVTB,setsar=1,format=rgba,"
             "scale=320:320:force_original_aspect_ratio=decrease,pad=320:320:(ow-iw)/2:(oh-ih)/2:color=black@0,"
             "format=rgba,colorchannelmixer=aa=1.0,setpts=PTS+0.0/TB[v0];"
             "[base0][v0]overlay=x='0.0':y='0.0':eof_action=pass:repeatlast=0:"
             f"enable='gte(t,0.0)*lt(t,{duration})'[base1];[base1]format=yuv420p[video]")
    (OUT / "filters.txt").write_text(graph, encoding="utf-8")
    for file in sorted(SOURCE.glob("*/evidence.json")):
        evidence = json.loads(file.read_text(encoding="utf-8"))
        source, final = file.parent / "graphics-intermediate.mp4", file.parent / "matte-exposure.mp4"
        assert sha(final) == evidence["renderResult"]["artifact"]["checksumSha256"]
        for crf in [14, 10, 8]:
            output = OUT / f"{evidence['variant']}-crf{crf}.mp4"
            command = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-filter_complex_threads", "1", "-i", str(source), "-i", str(final),
                       "-filter_complex_script", str(OUT / "filters.txt"), "-map", "[video]", "-map", "1:a:0", "-t", duration,
                       "-r", "30.0", "-c:v", "libx264", "-threads", "2", "-preset", "veryfast", "-crf", str(crf),
                       "-c:a", "copy", "-movflags", "+faststart", str(output)]
            completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
            (OUT / (output.stem + ".log")).write_text(completed.stderr, encoding="utf-8")
            raw = pixels(output)
            checks = []
            for check in evidence["pixelChecks"]:
                rgb = observed(raw, check)
                checks.append({"frame": check["frame"], "x": check["x"], "y": check["y"],
                               "expectedChannel": check["expectedChannel"], "observedRgb": rgb,
                               "maximumChannelError": max(abs(channel - check["expectedChannel"]) for channel in rgb),
                               "differenceFromApiFinal": max(abs(a - b) for a, b in zip(rgb, check["observedRgb"], strict=True))})
            if crf == 14:
                assert all(check["differenceFromApiFinal"] == 0 for check in checks), "encode_control_not_equivalent"
            records.append({"variant": evidence["variant"], "crf": crf, "command": command, "sizeBytes": output.stat().st_size,
                            "sourceVideoSha256": sha(source), "apiVideoSha256": sha(final), "outputSha256": sha(output),
                            "apiEvidenceSha256": sha(file), "maximumChannelError": max(check["maximumChannelError"] for check in checks),
                            "failedProbes": [check for check in checks if check["maximumChannelError"] >= 8], "checks": checks})
    report = {"scope": "research_only_retained_intermediate_reencode", "productionAdmission": "pending",
              "originalOracleChanged": False, "ffmpegVersion": version, "scriptSha256": sha(Path(__file__)),
              "filterGraphSha256": sha(OUT / "filters.txt"),
              "audioScope": "Copied audio from retained API final; no new mixer qualification.",
              "crf14ControlMatchesAllApiProbes": True, "records": records}
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps([{ "variant": record["variant"], "crf": record["crf"], "maximumError": record["maximumChannelError"],
                      "failedProbes": len(record["failedProbes"]), "sizeBytes": record["sizeBytes"]} for record in records]))


if __name__ == "__main__":
    main()
