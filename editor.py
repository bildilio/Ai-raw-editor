"""Non-generative RAW photo processing engine."""
from dataclasses import dataclass
from pathlib import Path
import csv
import numpy as np
from PIL import Image, ImageEnhance

EXTENSIONS = {'.cr2', '.cr3', '.nef', '.arw', '.dng', '.raf', '.rw2', '.orf'}
PRESETS = {
    'Natural': (0.00, 1.03, 1.03),
    'Wedding Soft': (0.15, 0.96, 0.96),
    'Moody': (-0.14, 1.12, 0.90),
    'Bright Editorial': (0.25, 1.04, 1.04),
}

@dataclass
class Settings:
    preset: str = 'Natural'
    strength: float = 0.75
    quality: int = 94

def discover(folder):
    return sorted((p for p in Path(folder).rglob('*') if p.is_file() and p.suffix.lower() in EXTENSIONS), key=str)

def decode(path):
    import rawpy
    with rawpy.imread(str(path)) as raw:
        arr = raw.postprocess(use_camera_wb=True, no_auto_bright=True,
                              output_bps=8, output_color=rawpy.ColorSpace.sRGB)
    return Image.fromarray(arr, 'RGB')

def edit(image, settings):
    if settings.preset not in PRESETS:
        raise ValueError('Unknown preset')
    sample = image.copy()
    sample.thumbnail((400, 400))
    a = np.asarray(sample, dtype=np.float32) / 255.0
    luma = a[..., 0] * .2126 + a[..., 1] * .7152 + a[..., 2] * .0722
    median, highlight = np.percentile(luma, [50, 99])
    base_ev, contrast, saturation = PRESETS[settings.preset]
    auto_ev = float(np.clip(np.log2(.46 / max(median, .08)) * .35, -.6, .6))
    if highlight > .97:
        auto_ev = min(auto_ev, .15)
    strength = float(np.clip(settings.strength, 0, 1))
    ev = (auto_ev + base_ev) * strength
    result = ImageEnhance.Brightness(image).enhance(2 ** ev)
    result = ImageEnhance.Contrast(result).enhance(1 + (contrast - 1) * strength)
    result = ImageEnhance.Color(result).enhance(1 + (saturation - 1) * strength)
    return result, {'ev': round(ev, 3), 'contrast': round(1 + (contrast - 1) * strength, 3),
                    'saturation': round(1 + (saturation - 1) * strength, 3)}

def export_batch(source, destination, settings, notify=None, cancelled=None):
    files = discover(source)
    if not files:
        raise ValueError('No supported RAW files found in source folder')
    src = Path(source).resolve()
    out = Path(destination).resolve()
    if out == src:
        raise ValueError('Choose a different output folder')
    out.mkdir(parents=True, exist_ok=True)
    report = []
    for index, path in enumerate(files, 1):
        if cancelled is not None and cancelled.is_set():
            break
        try:
            image = decode(path)
            result, params = edit(image, settings)
            relative = path.relative_to(src).with_suffix('.jpg')
            target = out / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            result.save(target, 'JPEG', quality=settings.quality, subsampling=0)
            report.append({'source': str(path), 'output': str(target), 'status': 'ok', **params})
        except Exception as exc:
            report.append({'source': str(path), 'output': '', 'status': str(exc), 'ev': '',
                           'contrast': '', 'saturation': ''})
        if notify:
            notify(index, len(files), str(path))
    with (out / 'edit_report.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=['source', 'output', 'status', 'ev', 'contrast', 'saturation'])
        writer.writeheader()
        writer.writerows(report)
    return report
