"""Face-identity compositing using MediaPipe landmark geometry and OpenCV.

Inputs are an original photograph and a separately AI-generated edit. This
module does NOT invoke a generative model or upload photographs anywhere.
The generated image is the base; only localized facial skin/features come
from the original. Large geometry mismatches fail closed.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from itertools import permutations
import math
import urllib.request

import cv2
import numpy as np
from PIL import Image, ImageOps

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
MODEL_PATH = Path(__file__).resolve().parent / "models" / "face_landmarker.task"
# Ordered face perimeter from MediaPipe's standard 478-point Face Landmarker.
FACE_OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323,
             361, 288, 397, 365, 379, 378, 400, 377, 152, 148,
             176, 149, 150, 136, 172, 58, 132, 93, 234, 127,
             162, 21, 54, 103, 67, 109]
ALIGN = [33, 263, 1, 61, 291, 152]  # eyes, nose, mouth corners, chin


class AlignmentError(ValueError):
    """Generated and original face geometry cannot safely be composited."""


@dataclass
class FaceReport:
    face: int
    displacement_fraction: float
    scale: float
    rotation_deg: float
    landmark_error_fraction: float
    face_width_px: float
    warning: str = ""


def load_rgb(path: str | Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(ImageOps.exif_transpose(im).convert("RGB"))


def save_rgb(image: np.ndarray, path: str | Path) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image).save(out, quality=96, subsampling=0)


def ensure_model(path: Path = MODEL_PATH, *, download: bool = False) -> Path:
    if path.is_file() and path.stat().st_size > 1_000_000:
        return path
    if not download:
        raise FileNotFoundError(
            f"Model wajah belum ada: {path}. Klik 'Unduh model' terlebih dahulu."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".part")
    try:
        urllib.request.urlretrieve(MODEL_URL, temp)
        if temp.stat().st_size < 1_000_000:
            raise IOError("Model tidak lengkap")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)
    return path


def find_landmarks(image: np.ndarray, model_path: Path = MODEL_PATH,
                   max_faces: int = 20) -> list[np.ndarray]:
    """Return 478x2 pixel landmarks. Uses current MediaPipe Tasks API."""
    import mediapipe as mp
    opts = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(ensure_model(model_path))),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_faces=max_faces,
        min_face_detection_confidence=0.35,
        min_face_presence_confidence=0.4,
    )
    h, w = image.shape[:2]
    with mp.tasks.vision.FaceLandmarker.create_from_options(opts) as detector:
        mpimg = mp.Image(image_format=mp.ImageFormat.SRGB,
                         data=np.ascontiguousarray(image, dtype=np.uint8))
        faces = detector.detect(mpimg).face_landmarks
    return [np.array([(p.x * w, p.y * h) for p in points], np.float32)
            for points in faces]


def _center_size(pts: np.ndarray) -> tuple[np.ndarray, float]:
    oval = pts[FACE_OVAL]
    return oval.mean(axis=0), float(np.ptp(oval[:, 0]))


def pair_faces(original_faces: list[np.ndarray], generated_faces: list[np.ndarray],
               width: int, height: int) -> list[tuple[int, int]]:
    """Match by position and size, not by identifying people or face recognition."""
    if not original_faces or len(original_faces) != len(generated_faces):
        raise AlignmentError(
            f"Deteksi wajah tidak cocok: asli={len(original_faces)}, "
            f"generatif={len(generated_faces)}. Coba hasil AI dengan pose lebih identik."
        )
    n = len(original_faces)
    d = np.hypot(width, height)
    centers_a = [_center_size(p) for p in original_faces]
    centers_b = [_center_size(p) for p in generated_faces]
    costs = np.zeros((n, n), dtype=np.float32)
    for i, (ca, sa) in enumerate(centers_a):
        for j, (cb, sb) in enumerate(centers_b):
            costs[i, j] = np.linalg.norm(ca - cb)/d + 0.12*abs(np.log((sa+1)/(sb+1)))
    if n <= 7:
        choice = min(permutations(range(n)), key=lambda pp: sum(costs[i, j] for i,j in enumerate(pp)))
        pairs = list(enumerate(choice))
    else:
        # Greedy global assignment, also safe for larger meeting/group photos.
        choices = sorted((float(costs[i, j]), i, j) for i in range(n) for j in range(n))
        chosen_a, chosen_b, pairs = set(), set(), []
        for _, i, j in choices:
            if i not in chosen_a and j not in chosen_b:
                chosen_a.add(i); chosen_b.add(j); pairs.append((i, j))
        pairs.sort()
    for i, j in pairs:
        ca, sa = centers_a[i]; cb, sb = centers_b[j]
        if np.linalg.norm(ca-cb) > .065*d or not (0.72 <= sb/max(sa,1) <= 1.36):
            raise AlignmentError(f"Wajah {i+1} berpindah atau berubah ukuran terlalu jauh")
    return pairs


def align_face(src: np.ndarray, dst: np.ndarray) -> tuple[np.ndarray, float, float, float]:
    """Estimate similarity transform and reject strong pose/expression changes."""
    a, b = src[ALIGN], dst[ALIGN]
    m, inliers = cv2.estimateAffinePartial2D(a, b, method=cv2.LMEDS)
    if m is None or not np.all(np.isfinite(m)):
        raise AlignmentError("Landmark wajah tidak dapat diselaraskan")
    scale = float(np.hypot(m[0,0],m[1,0]))
    angle = math.degrees(math.atan2(m[1,0],m[0,0]))
    predicted = cv2.transform(a[None,:,:],m)[0]
    fw = max(_center_size(dst)[1],1)
    error = float(np.sqrt(np.mean(np.sum((predicted-b)**2,axis=1)))/fw)
    if not (.82 <= scale <= 1.20) or abs(angle) > 13 or error > .115:
        raise AlignmentError(
            f"Geometri wajah tidak kompatibel (scale={scale:.2f}, "
            f"rotasi={angle:.1f}°, error={error:.3f})"
        )
    return m, scale, angle, error


def build_face_mask(points: np.ndarray, h: int, w: int) -> np.ndarray:
    """Skin-only mask, contracted inside landmark face oval; never background."""
    mask = np.zeros((h,w),np.uint8)
    polygon = np.rint(points[FACE_OVAL]).astype(np.int32)
    cv2.fillPoly(mask,[polygon],255)
    width = max(_center_size(points)[1],1.)
    erode = max(1,int(round(width*.018)))
    if erode > 1:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*erode+1,2*erode+1))
        mask = cv2.erode(mask,k)
    sigma = max(1.,width*.013)
    return cv2.GaussianBlur(mask.astype(np.float32)/255.,(0,0),sigma).clip(0,1)


def relight_face(source_rgb: np.ndarray, reference_rgb: np.ndarray,
                 mask: np.ndarray, width: float, strength: float) -> np.ndarray:
    """Transfer broad generated illumination while retaining original microtexture.

    Uses a guided low-frequency Lab adjustment. Never hallucinates facial features.
    """
    src = cv2.cvtColor(source_rgb,cv2.COLOR_RGB2LAB).astype(np.float32)
    ref = cv2.cvtColor(reference_rgb,cv2.COLOR_RGB2LAB).astype(np.float32)
    sigma = max(4.0,width*.23)
    src_l = cv2.GaussianBlur(src[:,:,0],(0,0),sigma)
    ref_l = cv2.GaussianBlur(ref[:,:,0],(0,0),sigma)
    # Match local illumination field (shadows/highlights) without generating detail.
    shift = np.clip(ref_l-src_l,-45.,45.)
    output = src.copy()
    output[:,:,0] = np.clip(src[:,:,0]+strength*shift,0,255)
    valid = mask > .7
    if np.count_nonzero(valid) >= 25:
        for channel, lim in ((1,17.),(2,17.)):
            chroma_shift = float(np.clip(
                np.median(ref[:,:,channel][valid])-np.median(src[:,:,channel][valid]),
                -lim,lim))
            output[:,:,channel] = np.clip(src[:,:,channel]+strength*.9*chroma_shift,0,255)
    return cv2.cvtColor(np.uint8(output),cv2.COLOR_LAB2RGB)


def composite(original: np.ndarray, generated: np.ndarray, *,
              strength: float = .9,
              original_faces: list[np.ndarray] | None = None,
              generated_faces: list[np.ndarray] | None = None,
              model_path: Path = MODEL_PATH) -> tuple[np.ndarray,np.ndarray,list[FaceReport]]:
    """Return (result, diagnostic mask, reports). Refuses unverifiable output."""
    if original.ndim != 3 or original.shape[2] != 3 or generated.ndim != 3 or generated.shape[2] != 3:
        raise ValueError("Input harus gambar RGB")
    if not (0 <= strength <= 1):
        raise ValueError("Kekuatan relighting harus 0–1")
    h,w = original.shape[:2]
    gh,gw = generated.shape[:2]
    if abs(w/h-gw/gh)>0.015:
        raise AlignmentError("Rasio gambar berbeda; crop foto generatif agar sama dengan asli")
    if (w,h) != (gw,gh):
        generated=cv2.resize(generated,(w,h),interpolation=cv2.INTER_LANCZOS4)
    original_faces = original_faces if original_faces is not None else find_landmarks(original,model_path)
    generated_faces = generated_faces if generated_faces is not None else find_landmarks(generated,model_path)
    pairs=pair_faces(original_faces,generated_faces,w,h)
    result=generated.copy().astype(np.float32)
    union_mask=np.zeros((h,w),np.float32)
    report=[]
    for i,j in pairs:
        src_pts,dst_pts=original_faces[i],generated_faces[j]
        transform,scale,angle,error=align_face(src_pts,dst_pts)
        transformed_pts=cv2.transform(src_pts[None,:,:],transform)[0]
        src_mask=build_face_mask(transformed_pts,h,w)
        # Prevent mask crossing destination's skin contour; no background bleed.
        dst_mask=build_face_mask(dst_pts,h,w)
        alpha=np.minimum(src_mask,dst_mask)
        # Reject low overlap; no opaque arbitrary ellipse and no face stretch.
        area=float(np.sum(dst_mask>.5))
        overlap=float(np.sum(alpha>.5)/max(area,1))
        if overlap < .68:
            raise AlignmentError(f"Kontur wajah {i+1} tidak selaras (overlap {overlap:.0%})")
        aligned=cv2.warpAffine(original,transform,(w,h),
                               flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
        width=_center_size(dst_pts)[1]
        adjusted=relight_face(aligned,generated,alpha,width,strength)
        result=result*(1-alpha[:,:,None])+adjusted.astype(np.float32)*alpha[:,:,None]
        union_mask=np.maximum(union_mask,alpha)
        ca,_=_center_size(src_pts);cb,_=_center_size(dst_pts)
        report.append(FaceReport(i+1,float(np.linalg.norm(ca-cb)/np.hypot(w,h)),
                                 scale,angle,error,width))
    output=np.uint8(np.clip(result,0,255))
    return output,union_mask,report


def mask_preview(generated: np.ndarray, mask: np.ndarray) -> np.ndarray:
    preview=generated.astype(np.float32).copy()
    red=np.zeros_like(preview);red[:,:,0]=255
    preview=preview*(1-mask[:,:,None]*.45)+red*(mask[:,:,None]*.45)
    return preview.clip(0,255).astype(np.uint8)
