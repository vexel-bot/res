"""Sequential RVM ONNX inference, isolated from the API. No network or model download."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time


def offline(*args, **kwargs):
    raise RuntimeError("material_effect_network_disabled")


def main(request):
    print("matte: loading runtime",flush=True)
    socket.socket.connect = offline
    socket.create_connection = offline
    import cv2
    cv2.setNumThreads(2)
    import numpy as np
    import onnxruntime as ort
    from PIL import Image
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from geometry import CameraRegistration, protect_attached_motion
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "models.lock.json").read_text())
    model = root / manifest["rvm"]["file"]
    if hashlib.sha256(model.read_bytes()).hexdigest() != manifest["rvm"]["sha256"]:
        raise ValueError("material_effect_model_checksum_mismatch")
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(model), options, providers=["CPUExecutionProvider"])
    print("matte: model loaded",flush=True)
    source = cv2.VideoCapture(request["source"])
    width, height = int(source.get(cv2.CAP_PROP_FRAME_WIDTH)), int(source.get(cv2.CAP_PROP_FRAME_HEIGHT))
    directory = Path(request["directory"])
    command = [request["ffmpeg"], "-v", "error", "-nostdin", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{width}x{height}",
               "-r", "24", "-i", "pipe:0", "-an", "-c:v", "ffv1", "-level", "3", "-threads", "1", str(directory / "matte.mkv")]
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    states = [np.zeros((1, 1, 1, 1), dtype=np.float32) for _ in range(4)]
    coverage, residuals, resets, frame_count, previous_alpha, previous_gray = [], [], 0, 0, None, None
    started = time.monotonic()
    protected_band = None
    camera = None
    foreground_encoder = None
    previous_full_gray = previous_matrix = None
    edge_pixels = contact_pixels = 0
    transform = request["operation"] != "segment_person"
    if transform:
        foreground_command = command.copy()
        foreground_command[foreground_command.index("-pix_fmt") + 1] = "bgr0"
        foreground_command[-1:] = ["-pix_fmt", "bgr0", str(directory / "foreground.mkv")]
        foreground_encoder = subprocess.Popen(foreground_command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        while True:
            ok, bgr = source.read()
            if not ok:
                break
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            small_gray = cv2.resize(gray, (160, 90))
            if previous_gray is not None and np.mean(np.abs(small_gray.astype(float)-previous_gray.astype(float))) > 65:
                states = [np.zeros((1, 1, 1, 1), dtype=np.float32) for _ in range(4)]
                resets += 1
            outputs = session.run(None, {"src": rgb.transpose(2, 0, 1)[None].astype(np.float32)/255,
                **{f"r{i+1}i": state for i, state in enumerate(states)}, "downsample_ratio": np.array([min(1, 384/max(width,height))], dtype=np.float32)})
            alpha, states = outputs[1][0, 0], outputs[2:]
            if not np.isfinite(alpha).all():
                raise ValueError("material_effect_alpha_nonfinite")
            mask = np.rint(np.clip(alpha, 0, 1)*255).astype(np.uint8)
            coverage.append(float(np.mean(alpha > .5)))
            if previous_alpha is not None:
                # Flow compensates observed motion; this is evidence, not a quality grade.
                flow = cv2.calcOpticalFlowFarneback(small_gray, previous_gray, None, .5, 2, 15, 2, 5, 1.1, 0)
                yy, xx = np.mgrid[:90, :160].astype(np.float32)
                warped = cv2.remap(previous_alpha, xx+flow[:,:,0], yy+flow[:,:,1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
                residuals.append(float(np.mean(np.abs(cv2.resize(alpha,(160,90))-warped))))
            if frame_count == 0:
                Image.fromarray(rgb).save(directory / "reference.png")
                Image.fromarray(mask).save(directory / "first-alpha.png")
                Image.fromarray(np.dstack((rgb, mask))).save(directory / "subject.png")
                dilated = cv2.dilate((mask > 16).astype(np.uint8)*255, np.ones((11,11),np.uint8))
                clean = cv2.inpaint(bgr, dilated, 7, cv2.INPAINT_TELEA)
                Image.fromarray(cv2.cvtColor(clean,cv2.COLOR_BGR2RGB)).save(directory / "clean-plate.png")
            if transform:
                if camera is None:
                    rows=np.nonzero(alpha>.5)[0]
                    if request.get("preserveInteractionArea"):
                        protected_band=float(np.clip(float(np.max(rows))/height-.21,.40,.72)) if rows.size else .65
                    camera = CameraRegistration(width, height, protected_band)
                matrix = camera.update(gray, alpha)
                contact = camera.contact(alpha, matrix)
                if protected_band is not None and matrix is not None and previous_matrix is not None:
                    step = matrix @ np.linalg.inv(previous_matrix)
                    contact = protect_attached_motion(contact, alpha, gray, previous_full_gray, step)
                # The RVM foreground removes old background spill on translucent edges.
                # Keep original color on opaque person and protected contact pixels.
                fgr = np.clip(outputs[0][0].transpose(1,2,0)[:,:,::-1]*255, 0, 255)
                edge = np.minimum(np.clip(alpha/.12,0,1), np.clip((.99-alpha)/.20,0,1)) * (1-contact)
                corrected = np.zeros((height,width,4), dtype=np.uint8)
                corrected[:,:,:3] = np.rint(bgr*(1-edge[:,:,None])+fgr*edge[:,:,None]).astype(np.uint8)
                try:
                    foreground_encoder.stdin.write(corrected.tobytes())
                except BrokenPipeError as error:
                    detail = foreground_encoder.stderr.read().decode(errors="replace")[-400:]
                    raise ValueError("material_effect_foreground_encode_failed:"+detail) from error
                written_alpha=np.rint(np.maximum(alpha,contact)*255).astype(np.uint8)
                edge_pixels += int(np.count_nonzero(edge > .1))
                contact_pixels += int(np.count_nonzero(contact > .99))
                previous_full_gray, previous_matrix = gray, matrix
            else:
                written_alpha=mask
            encoder.stdin.write(written_alpha.tobytes())
            previous_alpha, previous_gray = cv2.resize(alpha,(160,90)), small_gray
            frame_count += 1
            if frame_count > 288:
                raise ValueError("material_effect_frame_limit")
        encoder.stdin.close()
        error = encoder.stderr.read()
        if encoder.wait(timeout=30):
            raise ValueError("material_effect_matte_encode_failed:"+error.decode(errors="replace")[-300:])
        if foreground_encoder is not None:
            foreground_encoder.stdin.close()
            error = foreground_encoder.stderr.read()
            if foreground_encoder.wait(timeout=30):
                raise ValueError("material_effect_foreground_encode_failed:"+error.decode(errors="replace")[-300:])
    finally:
        source.release()
        if encoder.poll() is None:
            encoder.kill()
            encoder.wait()
        if foreground_encoder is not None and foreground_encoder.poll() is None:
            foreground_encoder.kill()
            foreground_encoder.wait()
    if frame_count != request["frames"]:
        raise ValueError("material_effect_frame_count_mismatch")
    if not coverage or not .005 < float(np.median(coverage)) < .985:
        raise ValueError("material_effect_person_not_detected")
    result = {"model": "rvm_mobilenetv3_fp32", "modelSha256": manifest["rvm"]["sha256"], "frames":frame_count,
        "width":width,"height":height,"fps":24,"recurrentStatesReused":True,"sceneCutResets":resets,
        "foregroundCoverageMedian":float(np.median(coverage)),"flowCompensatedAlphaResidualMean":float(np.mean(residuals)) if residuals else 0,
        "protectedInteractionBandStartFraction":protected_band,
        "edgeDecontaminatedPixelFrames":edge_pixels,"opaqueContactPixelFrames":contact_pixels,
        "seconds":round(time.monotonic()-started,3),"networkDisabled":True,"externalCostUsd":0,"reviewRequired":True}
    if camera is not None:
        (directory / "camera.json").write_text(json.dumps(camera.frames))
    (directory / "matte-report.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    print(json.dumps(main(json.loads(Path(sys.argv[1]).read_text()))))
