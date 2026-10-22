"""
Cutit ai - Command-Line Interface (CLI) for Batch and Single Background Removal.
Usage:
  python cli.py photo.jpg -o cutout.png
  python cli.py photo.jpg -o photo_white.jpg --bg color --hex "#FFFFFF"
  python cli.py input_folder/ -o output_folder/ --model silueta
"""

import argparse
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine

def main():
    parser = argparse.ArgumentParser(description="Cutit ai - 100% Local AI Background Remover CLI")
    parser.add_argument("input", help="Path to input image file or directory")
    parser.add_argument("-o", "--output", required=True, help="Path to output file or output directory")
    parser.add_argument(
        "--model", 
        default="silueta", 
        choices=list(engine.SUPPORTED_MODELS.keys()),
        help="AI Model architecture (default: silueta for ultra-fast, u2net for standard)"
    )
    parser.add_argument(
        "--bg", 
        default="transparent", 
        choices=["transparent", "color", "blur", "image"],
        help="Background replacement mode"
    )
    parser.add_argument("--hex", default="#FFFFFF", help="Hex color code when --bg color is chosen (default: #FFFFFF)")
    parser.add_argument("--bg-image", default=None, help="Background image path when --bg image is chosen")
    parser.add_argument("--blur-radius", type=int, default=20, help="Blur radius when --bg blur is chosen")
    
    args = parser.parse_args()
    
    hex_clean = args.hex.lstrip("#")
    color_rgb = tuple(int(hex_clean[i:i+2], 16) for i in (0, 2, 4)) if len(hex_clean) == 6 else (255, 255, 255)
    
    if os.path.isdir(args.input):
        exts = ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp")
        files = []
        for ext in exts:
            files.extend(glob.glob(os.path.join(args.input, ext)))
            files.extend(glob.glob(os.path.join(args.input, ext.upper())))
            
        if not files:
            print(f"No image files found in {args.input}")
            sys.exit(1)
            
        os.makedirs(args.output, exist_ok=True)
        print(f"✂️ Cutit ai: Processing {len(files)} files with model '{args.model}'...")
        
        for idx, file_path in enumerate(files, 1):
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            out_ext = ".png" if args.bg == "transparent" else ".jpg"
            out_file = os.path.join(args.output, f"{base_name}_cutit{out_ext}")
            
            print(f"[{idx}/{len(files)}] Cutting {os.path.basename(file_path)}...")
            engine.process_file(
                input_path=file_path,
                output_path=out_file,
                model_name=args.model,
                bg_mode="custom_image" if args.bg == "image" else args.bg,
                color=color_rgb,
                bg_image_path=args.bg_image,
                blur_radius=args.blur_radius
            )
        print(f"✨ Completed! Results saved to: {args.output}")
        
    elif os.path.isfile(args.input):
        print(f"✂️ Cutit ai: Processing {args.input} using model '{args.model}'...")
        engine.process_file(
            input_path=args.input,
            output_path=args.output,
            model_name=args.model,
            bg_mode="custom_image" if args.bg == "image" else args.bg,
            color=color_rgb,
            bg_image_path=args.bg_image,
            blur_radius=args.blur_radius,
            progress_callback=lambda p, msg: print(f"  [{int(p*100)}%] {msg}")
        )
        print(f"✨ Saved to: {args.output}")
    else:
        print(f"Input path does not exist: {args.input}")
        sys.exit(1)

if __name__ == "__main__":
    main()
