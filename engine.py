"""
Cutit ai - Core background removal and image composition engine.
Optimized for high-throughput ONNX Runtime inference and real-time compositing.
"""

from typing import Optional, Tuple, Callable
import os
import multiprocessing
from PIL import Image, ImageFilter, ImageOps
import rembg
import numpy as np

# Cache for active model sessions to avoid reloading model weights on every image
_SESSIONS = {}

SUPPORTED_MODELS = {
    "silueta": "⚡ Silueta (Turbo Fast - Instant Preview)",
    "u2net": "🎯 U2-Net (High Quality - Default)",
    "isnet-general-use": "🔬 IS-Net (Ultra-Fine Edges & Hair)",
    "u2net_human_seg": "👤 U2-Net Human (Portraits & Fashion)"
}

def get_session(model_name: str = "u2net"):
    """Retrieve or initialize a cached rembg model session with optimized threadpool."""
    if model_name not in _SESSIONS:
        # Use logical cores for parallel inference
        cpu_threads = max(2, multiprocessing.cpu_count())
        try:
            # rembg session with CPUExecutionProvider
            _SESSIONS[model_name] = rembg.new_session(
                model_name=model_name,
                providers=["CPUExecutionProvider"]
            )
        except Exception:
            # Fallback to standard initialization
            _SESSIONS[model_name] = rembg.new_session(model_name)
    return _SESSIONS[model_name]

def create_preview_proxy(image: Image.Image, max_dim: int = 1200) -> Image.Image:
    """Generate a lightweight proxy for ultra-smooth 60fps UI adjustments."""
    w, h = image.size
    if max(w, h) <= max_dim:
        return image.copy()
    ratio = max_dim / max(w, h)
    new_w = max(1, int(w * ratio))
    new_h = max(1, int(h * ratio))
    return image.resize((new_w, new_h), Image.Resampling.BILINEAR)

def remove_background(
    image: Image.Image,
    model_name: str = "u2net",
    alpha_matting: bool = False,
    alpha_matting_foreground_threshold: int = 240,
    alpha_matting_background_threshold: int = 10,
    alpha_matting_erode_size: int = 10,
    post_process_mask: bool = True,
) -> Image.Image:
    """
    Remove background from PIL image and return RGBA image with transparency.
    """
    # Ensure RGB input
    if image.mode != "RGB":
        image = image.convert("RGB")
        
    session = get_session(model_name)
    
    output_image = rembg.remove(
        image,
        session=session,
        alpha_matting=alpha_matting,
        alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
        alpha_matting_background_threshold=alpha_matting_background_threshold,
        alpha_matting_erode_size=alpha_matting_erode_size,
        post_process_mask=post_process_mask
    )
    
    return output_image

def composite_background(
    cutout: Image.Image,
    original: Image.Image,
    bg_mode: str = "transparent",
    color: Tuple[int, int, int] = (255, 255, 255),
    bg_image: Optional[Image.Image] = None,
    blur_radius: int = 15
) -> Image.Image:
    """
    Composite cutout onto a transparent, solid color, blurred, or custom background.
    Fast and vectorized for instant live updates.
    """
    if cutout.mode != "RGBA":
        cutout = cutout.convert("RGBA")
        
    width, height = cutout.size
    
    if bg_mode == "transparent":
        return cutout
        
    elif bg_mode == "color":
        bg = Image.new("RGBA", (width, height), (*color, 255))
        bg.paste(cutout, (0, 0), cutout)
        return bg
        
    elif bg_mode == "blur":
        # Match dimensions if needed
        if original.size != (width, height):
            orig_resized = original.resize((width, height), Image.Resampling.BILINEAR)
        else:
            orig_resized = original
            
        blurred_bg = orig_resized.convert("RGBA").filter(ImageFilter.GaussianBlur(radius=blur_radius))
        blurred_bg.paste(cutout, (0, 0), cutout)
        return blurred_bg
        
    elif bg_mode == "custom_image" and bg_image is not None:
        fitted_bg = ImageOps.fit(bg_image.convert("RGBA"), (width, height), method=Image.Resampling.BILINEAR)
        fitted_bg.paste(cutout, (0, 0), cutout)
        return fitted_bg
        
    return cutout

def process_file(
    input_path: str,
    output_path: str,
    model_name: str = "u2net",
    bg_mode: str = "transparent",
    color: Tuple[int, int, int] = (255, 255, 255),
    bg_image_path: Optional[str] = None,
    blur_radius: int = 15,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> str:
    """
    Full pipeline: load, remove background, composite, and save.
    """
    if progress_callback:
        progress_callback(0.1, f"Loading {os.path.basename(input_path)}...")
        
    orig = Image.open(input_path)
    
    if progress_callback:
        progress_callback(0.3, "Extracting subject with Cutit ai...")
        
    cutout = remove_background(orig, model_name=model_name)
    
    if progress_callback:
        progress_callback(0.7, "Compositing background...")
        
    custom_bg = Image.open(bg_image_path) if (bg_mode == "custom_image" and bg_image_path) else None
    result = composite_background(
        cutout=cutout,
        original=orig,
        bg_mode=bg_mode,
        color=color,
        bg_image=custom_bg,
        blur_radius=blur_radius
    )
    
    if progress_callback:
        progress_callback(0.9, f"Saving to {os.path.basename(output_path)}...")
        
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    if bg_mode == "transparent":
        result.save(output_path, "PNG")
    else:
        if output_path.lower().endswith((".jpg", ".jpeg")):
            result.convert("RGB").save(output_path, "JPEG", quality=95)
        else:
            result.save(output_path, "PNG")
            
    if progress_callback:
        progress_callback(1.0, "Complete!")
        
    return output_path
