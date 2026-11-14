"""Identity-preserving compositing for a manually generated cinematic image.

No face pixels are synthesized. Detection uses OpenCV's bundled Haar cascade;
when no face is detected the operation FAILS CLOSED (no unsafe output).
This is a baseline, not a guarantee of perfect identity preservation.
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

def detect_faces(image):
    import cv2
    arr = cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    if cascade.empty():
        raise RuntimeError("Face detector is unavailable")
    boxes = cascade.detectMultiScale(arr, scaleFactor=1.08, minNeighbors=5, minSize=(28, 28))
    return sorted([tuple(map(int, b)) for b in boxes], key=lambda b: (b[1], b[0]))

def composite(original, generated, max_shift=.08, feather=.16, padding=.18):
    """Blend protected original face regions over generated image.

    Rejects image dimension differences, unmatched faces, or large displacements.
    Minor translations are supported; pose/scale changes are not repaired.
    """
    original = original.convert("RGB")
    generated = generated.convert("RGB")
    if original.size != generated.size:
        raise ValueError("Generated image must have exactly the original dimensions")
    src_boxes, dst_boxes = detect_faces(original), detect_faces(generated)
    if not src_boxes or len(src_boxes) != len(dst_boxes):
        raise ValueError("Face detection mismatch: refusing automatic composite")
    w, h = original.size
    src_arr = np.asarray(original, dtype=np.float32)
    dst_arr = np.asarray(generated, dtype=np.float32)
    canvas = dst_arr.copy()
    used = set()
    report = []
    # Pair each original face to the nearest unmatched destination face.
    for sx, sy, sw, sh in src_boxes:
        cx, cy = sx + sw/2, sy + sh/2
        candidates = [(float(np.hypot(cx-(dx+dw/2), cy-(dy+dh/2))), j)
                      for j,(dx,dy,dw,dh) in enumerate(dst_boxes) if j not in used]
        dist, j = min(candidates)
        dx, dy, dw, dh = dst_boxes[j]
        if dist > max_shift * np.hypot(w, h) or not (.8 <= dw/sw <= 1.25 and .8 <= dh/sh <= 1.25):
            raise ValueError("Face geometry changed too much: refusing automatic composite")
        used.add(j)
        # Shift original pixels toward the generated face position, without resizing.
        shift_x = int(round(dx + dw/2 - cx))
        shift_y = int(round(dy + dh/2 - cy))
        import cv2
        aligned = cv2.warpAffine(src_arr, np.float32([[1,0,shift_x],[0,1,shift_y]]),
                                 (w,h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        # Expanded elliptical mask includes forehead, cheeks and chin; not full hair.
        center_x, center_y = cx + shift_x, cy + shift_y
        rx = max(sw, dw) * (.5 + padding)
        ry = max(sh, dh) * (.5 + padding)
        yy, xx = np.ogrid[:h, :w]
        ellipse = (((xx-center_x)/max(rx,1))**2 + ((yy-center_y)/max(ry,1))**2) <= 1
        mask = Image.fromarray(np.uint8(ellipse)*255, "L")
        mask = mask.filter(ImageFilter.GaussianBlur(max(2, int(min(sw,sh)*feather))))
        alpha = np.asarray(mask, dtype=np.float32)[...,None] / 255.
        # Match overall illumination conservatively; preserve face structure.
        region = alpha[...,0] > .8
        if region.sum() < 20:
            raise ValueError("Face mask is too small")
        src_mean = np.mean(aligned[region], axis=0)
        dst_mean = np.mean(dst_arr[region], axis=0)
        gain = np.clip(dst_mean / np.maximum(src_mean, 8), .80, 1.25)
        adjusted = np.clip(aligned * gain, 0, 255)
        canvas = adjusted * alpha + canvas * (1-alpha)
        report.append({"original_box":[sx,sy,sw,sh], "generated_box":[dx,dy,dw,dh],
                       "shift_px":[shift_x,shift_y], "color_gain":gain.round(3).tolist()})
    return Image.fromarray(np.uint8(np.clip(np.rint(canvas),0,255)), "RGB"), report

def process(original_path, generated_path, output_path):
    with Image.open(original_path) as original, Image.open(generated_path) as generated:
        output, report = composite(original, generated)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        output.save(output_path, quality=96, subsampling=0)
        return report
