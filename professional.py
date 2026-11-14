"""Conservative, local, non-generative photo adjustments.

This module is intentionally not described as a trained AI model.
"""
import numpy as np
from PIL import Image

def correct(image, strength=0.75, preset="Natural"):
    """Return corrected RGB image and an auditable edit recipe.

    Operations are global white-balance estimation, luminance-based shadow
    recovery, highlight roll-off and conservative chroma adjustment.
    """
    if image.mode != "RGB":
        image = image.convert("RGB")
    strength = float(np.clip(strength, 0.0, 1.0))
    data = np.asarray(image, dtype=np.float32) / 255.0
    if strength == 0:
        return image.copy(), {"strength": 0.0, "white_balance": [1., 1., 1.]}
    small = image.copy()
    small.thumbnail((512, 512))
    sample = np.asarray(small, dtype=np.float32) / 255.
    valid = (sample.min(axis=2) > .07) & (sample.max(axis=2) < .92)
    valid &= (sample.max(axis=2) - sample.min(axis=2) < .22)
    if np.count_nonzero(valid) > 128:
        channel = np.median(sample[valid], axis=0)
        neutral = float(np.mean(channel))
        gains = np.clip(neutral / np.maximum(channel, .02), .90, 1.10)
    else:
        gains = np.ones(3, dtype=np.float32)
    gains = 1.0 + (gains - 1.0) * strength * .65
    data = np.clip(data * gains, 0, 1)
    luma = data @ np.array([.2126, .7152, .0722], dtype=np.float32)
    # Smooth, bounded, luminance-dependent corrections.
    shadow = np.power(1 - luma, 3) * .12 * strength
    highlight = np.power(luma, 5) * .10 * strength
    target = np.clip(luma + shadow - highlight, 0, 1)
    ratio = np.clip(target / np.maximum(luma, .025), .7, 1.45)
    data = np.clip(data * ratio[..., None], 0, 1)
    luma2 = data @ np.array([.2126, .7152, .0722], dtype=np.float32)
    saturation = {"Natural": 1.0, "Wedding Soft": .96, "Moody": .92,
                  "Bright Editorial": 1.04}.get(preset, 1.0)
    saturation = 1 + (saturation - 1) * strength
    data = np.clip(luma2[..., None] + (data - luma2[..., None]) * saturation, 0, 1)
    result = Image.fromarray(np.round(data * 255).astype(np.uint8), "RGB")
    return result, {"strength": round(strength, 3),
                    "white_balance": [round(float(x), 4) for x in gains],
                    "shadow_lift": round(.12 * strength, 3),
                    "highlight_rolloff": round(.10 * strength, 3),
                    "saturation": round(saturation, 3)}
