"""Encode a camera-registered plate with transparent, feathered margins."""
import json
from pathlib import Path
import subprocess
import sys

import cv2
import numpy as np


def main(request):
    cv2.setNumThreads(2)
    directory = Path(request["directory"])
    matrices = json.loads((directory / "camera.json").read_text())
    valid = [np.array(matrix) for matrix in matrices if matrix is not None]
    width, height = request["width"], request["height"]
    center = np.array([width/2, height/2, 1])
    corners = np.array([[0, 0, 1], [width, 0, 1], [width, height, 1], [0, height, 1]])
    displacement = max((np.linalg.norm((m @ center)[:2]-center[:2]) for m in valid), default=0.)
    max_shift = max((np.max(np.linalg.norm((corners @ m.T - corners)[:, :2], axis=1)) for m in valid), default=0.)
    viewport = corners[:, :2].astype(np.float32)
    visible_fraction = min((
        cv2.intersectConvexConvex(viewport, (corners @ matrix.T)[:, :2].astype(np.float32))[0] / (width * height)
        for matrix in valid
    ), default=0.)
    scales = [np.linalg.norm(matrix[:2, 0]) for matrix in valid]
    applied = (len(valid) == request["frames"] and visible_fraction >= .68
               and .72 <= min(scales, default=0.) <= max(scales, default=0.) <= 1.65
               and displacement < .24 * max(width, height))
    if applied and not request.get("checkOnly"):
        plate = cv2.imread(str(directory / "generated.png"), cv2.IMREAD_UNCHANGED)
        if plate.shape[2] == 3:
            plate = cv2.cvtColor(plate, cv2.COLOR_BGR2BGRA)
        plate = cv2.resize(plate, (width,height)).astype(np.float32)/255
        edge = np.minimum.outer(np.minimum(np.arange(height), np.arange(height)[::-1]),
                                np.minimum(np.arange(width), np.arange(width)[::-1]))
        plate[:, :, 3] *= np.clip(edge/10,0,1)
        plate[:, :, :3] *= plate[:, :, 3:]
        command = [request["ffmpeg"], "-v", "error", "-nostdin", "-y", "-f", "rawvideo", "-pix_fmt", "bgra",
                   "-s", f"{width}x{height}", "-r", "24", "-i", "pipe:0", "-an", "-c:v", "ffv1",
                   "-pix_fmt", "bgra", "-threads", "1", str(directory / "generated-moving.mkv")]
        with subprocess.Popen(command, stdin=subprocess.PIPE, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)) as encoder:
            for matrix in valid:
                warped = cv2.warpAffine(plate, matrix[:2], (width, height))
                np.divide(warped[:, :, :3], warped[:, :, 3:], out=warped[:, :, :3], where=warped[:, :, 3:] > 0)
                encoder.stdin.write(np.rint(np.clip(warped,0,1)*255).astype(np.uint8).tobytes())
            encoder.stdin.close()
            if encoder.wait(timeout=30):
                raise ValueError("material_effect_registered_plate_encode_failed")
    report = {"method":"background-feature-similarity", "trackedFrames":len(valid), "applied":bool(applied),
              "maxCenterShiftPixels":round(float(displacement),3), "maxCornerShiftPixels":round(float(max_shift),3),
              "minVisiblePlateFraction":round(float(visible_fraction),3),
              "scaleRange":[round(float(min(scales, default=0.)),3),round(float(max(scales, default=0.)),3)],
              "fallback":None if applied else "original_video"}
    (directory / "camera-report.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main(json.loads(Path(sys.argv[1]).read_text()))
