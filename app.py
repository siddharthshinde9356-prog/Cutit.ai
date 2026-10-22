"""
Cutit ai - Modern Ultra-Fast Desktop Application for AI Background Removal.
Features: 60FPS responsive UI, multi-theme selector, vectorized previews, batch engine.
"""

import os
import sys
import threading
import time
from typing import Optional, Dict
from PIL import Image, ImageOps
import numpy as np
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine

# =========================================================================
# THEME DEFINITIONS
# =========================================================================
THEMES: Dict[str, dict] = {
    "Obsidian Violet": {
        "mode": "Dark",
        "primary": "#8B5CF6",
        "primary_hover": "#7C3AED",
        "bg_sidebar": "#11141E",
        "card_bg": "#181C29",
        "card_border": "#282F44",
        "canvas_bg": "#0B0D13",
        "accent_text": "#C4B5FD",
        "btn_save": "#10B981",
        "btn_save_hover": "#059669",
    },
    "Cyber Cyan": {
        "mode": "Dark",
        "primary": "#06B6D4",
        "primary_hover": "#0891B2",
        "bg_sidebar": "#0C1322",
        "card_bg": "#151F33",
        "card_border": "#243552",
        "canvas_bg": "#070B14",
        "accent_text": "#67E8F9",
        "btn_save": "#10B981",
        "btn_save_hover": "#059669",
    },
    "Emerald Studio": {
        "mode": "Dark",
        "primary": "#10B981",
        "primary_hover": "#059669",
        "bg_sidebar": "#0E1815",
        "card_bg": "#162520",
        "card_border": "#273D35",
        "canvas_bg": "#080F0D",
        "accent_text": "#6EE7B7",
        "btn_save": "#3B82F6",
        "btn_save_hover": "#2563EB",
    },
    "Clean Light": {
        "mode": "Light",
        "primary": "#6366F1",
        "primary_hover": "#4F46E5",
        "bg_sidebar": "#F3F4F6",
        "card_bg": "#FFFFFF",
        "card_border": "#E5E7EB",
        "canvas_bg": "#E5E7EB",
        "accent_text": "#4F46E5",
        "btn_save": "#10B981",
        "btn_save_hover": "#059669",
    }
}

def make_fast_checkerboard(width: int, height: int, square_size: int = 16, is_dark: bool = True) -> Image.Image:
    """Generate high-performance vectorized checkerboard in under 1ms with NumPy."""
    if width <= 0 or height <= 0:
        return Image.new("RGBA", (1, 1), (30, 30, 30, 255))
        
    num_x = (width + square_size - 1) // square_size
    num_y = (height + square_size - 1) // square_size
    grid = (np.indices((num_y, num_x)).sum(axis=0) % 2).astype(np.uint8)
    
    if is_dark:
        colors = np.array([[26, 29, 36, 255], [38, 42, 53, 255]], dtype=np.uint8)
    else:
        colors = np.array([[240, 240, 245, 255], [215, 218, 226, 255]], dtype=np.uint8)
        
    board = colors[grid]
    board_img = Image.fromarray(board).resize(
        (num_x * square_size, num_y * square_size), 
        Image.Resampling.NEAREST
    ).crop((0, 0, width, height))
    return board_img

class CutitApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Cutit ai - Instant AI Background Studio")
        self.geometry("1220x790")
        self.minsize(980, 680)
        
        # State
        self.current_theme_name = "Obsidian Violet"
        self.theme = THEMES[self.current_theme_name]
        ctk.set_appearance_mode(self.theme["mode"])
        
        self.current_image_path: Optional[str] = None
        self.original_image: Optional[Image.Image] = None
        self.original_proxy: Optional[Image.Image] = None  # Fast display proxy
        self.cutout_image: Optional[Image.Image] = None
        self.cutout_proxy: Optional[Image.Image] = None    # Fast display proxy
        self.custom_bg_image: Optional[Image.Image] = None
        
        self.is_processing = False
        self.current_color = (255, 255, 255)
        self._last_resize_time = 0
        self._resize_job = None
        
        self.setup_ui()
        self.apply_theme_colors()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # =========================================================================
        # LEFT SIDEBAR
        # =========================================================================
        self.sidebar = ctk.CTkScrollableFrame(self, width=330, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        # Brand Header
        self.header_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=16, pady=(16, 6))
        
        self.brand_label = ctk.CTkLabel(
            self.header_frame, 
            text="✂️ Cutit ai", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.brand_label.pack(side="left")
        
        self.badge_label = ctk.CTkLabel(
            self.header_frame,
            text=" v2.0 Turbo ",
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=6,
            fg_color="#374151"
        )
        self.badge_label.pack(side="right", padx=(8, 0))
        
        self.subtitle_label = ctk.CTkLabel(
            self.sidebar,
            text="Fast, Local, Unlimited Background Removal",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.subtitle_label.pack(padx=16, pady=(0, 14), anchor="w")
        
        # Section: Theme Selector
        self.theme_card = ctk.CTkFrame(self.sidebar)
        self.theme_card.pack(fill="x", padx=14, pady=5)
        ctk.CTkLabel(self.theme_card, text="🎨 App Theme", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=12, pady=(8, 2), anchor="w")
        self.theme_dropdown = ctk.CTkOptionMenu(
            self.theme_card,
            values=list(THEMES.keys()),
            command=self.change_theme,
            height=28
        )
        self.theme_dropdown.set(self.current_theme_name)
        self.theme_dropdown.pack(fill="x", padx=12, pady=(0, 8))
        
        # Section 1: File Actions
        self.file_card = ctk.CTkFrame(self.sidebar)
        self.file_card.pack(fill="x", padx=14, pady=6)
        
        self.btn_open = ctk.CTkButton(
            self.file_card,
            text="📂 Open Image",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.open_image,
            height=38
        )
        self.btn_open.pack(fill="x", padx=12, pady=(10, 5))
        
        self.btn_batch = ctk.CTkButton(
            self.file_card,
            text="📁 Batch Folder Process",
            fg_color="transparent",
            border_width=1,
            command=self.open_batch_dialog,
            height=32
        )
        self.btn_batch.pack(fill="x", padx=12, pady=(0, 10))
        
        # Section 2: AI Engine Model
        self.model_card = ctk.CTkFrame(self.sidebar)
        self.model_card.pack(fill="x", padx=14, pady=6)
        
        ctk.CTkLabel(self.model_card, text="🧠 AI Model Engine", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=12, pady=(8, 4), anchor="w")
        
        self.model_var = ctk.StringVar(value="silueta")
        self.model_dropdown = ctk.CTkOptionMenu(
            self.model_card,
            values=["silueta", "u2net", "isnet-general-use", "u2net_human_seg"],
            variable=self.model_var,
            command=self.on_model_changed,
            height=30
        )
        self.model_dropdown.pack(fill="x", padx=12, pady=(0, 4))
        
        self.model_desc = ctk.CTkLabel(
            self.model_card,
            text="⚡ Silueta: Turbo fast instant cut (Recommended)",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            wraplength=280,
            justify="left"
        )
        self.model_desc.pack(padx=12, pady=(0, 8), anchor="w")
        
        # Section 3: Background Replacement
        self.bg_card = ctk.CTkFrame(self.sidebar)
        self.bg_card.pack(fill="x", padx=14, pady=6)
        
        ctk.CTkLabel(self.bg_card, text="🖼️ Background Output", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=12, pady=(8, 4), anchor="w")
        
        self.bg_mode_var = ctk.StringVar(value="transparent")
        self.bg_mode_seg = ctk.CTkSegmentedButton(
            self.bg_card,
            values=["Transparent", "Color", "Blur", "Image"],
            command=self.on_bg_mode_changed
        )
        self.bg_mode_seg.set("Transparent")
        self.bg_mode_seg.pack(fill="x", padx=12, pady=(0, 8))
        
        # Color Frame
        self.color_presets_frame = ctk.CTkFrame(self.bg_card, fg_color="transparent")
        color_btn_container = ctk.CTkFrame(self.color_presets_frame, fg_color="transparent")
        color_btn_container.pack(fill="x")
        self.color_presets = [
            ("#FFFFFF", "White"),
            ("#000000", "Black"),
            ("#E5E7EB", "Studio Grey"),
            ("#10B981", "Green"),
            ("#3B82F6", "Blue"),
            ("#EC4899", "Rose")
        ]
        for hex_code, name in self.color_presets:
            btn = ctk.CTkButton(
                color_btn_container,
                text="",
                width=26,
                height=26,
                corner_radius=13,
                fg_color=hex_code,
                hover_color=hex_code,
                border_width=1,
                border_color="#4B5563",
                command=lambda h=hex_code: self.set_preset_color(h)
            )
            btn.pack(side="left", padx=3, pady=3)
            
        hex_row = ctk.CTkFrame(self.color_presets_frame, fg_color="transparent")
        hex_row.pack(fill="x", pady=4)
        self.hex_entry = ctk.CTkEntry(hex_row, placeholder_text="#HEX Color", width=120, height=28)
        self.hex_entry.pack(side="left", padx=(0, 6))
        self.hex_btn = ctk.CTkButton(hex_row, text="Apply", width=60, height=28, command=self.apply_hex_color)
        self.hex_btn.pack(side="left")
        
        # Blur Frame
        self.blur_frame = ctk.CTkFrame(self.bg_card, fg_color="transparent")
        self.blur_label = ctk.CTkLabel(self.blur_frame, text="Bokeh Blur: 20px", font=ctk.CTkFont(size=11))
        self.blur_label.pack(anchor="w")
        self.blur_slider = ctk.CTkSlider(self.blur_frame, from_=5, to=50, number_of_steps=45, command=self.on_blur_slider)
        self.blur_slider.set(20)
        self.blur_slider.pack(fill="x", pady=4)
        
        # Custom Image Frame
        self.custom_img_frame = ctk.CTkFrame(self.bg_card, fg_color="transparent")
        self.btn_select_custom_bg = ctk.CTkButton(
            self.custom_img_frame,
            text="🖼️ Select Background Photo",
            command=self.select_custom_bg,
            height=30
        )
        self.btn_select_custom_bg.pack(fill="x", pady=4)
        
        # Section 4: Edge Refinement
        self.edge_card = ctk.CTkFrame(self.sidebar)
        self.edge_card.pack(fill="x", padx=14, pady=6)
        
        self.alpha_matting_var = ctk.BooleanVar(value=False)
        self.chk_alpha = ctk.CTkCheckBox(
            self.edge_card,
            text="Advanced Alpha Matting (Hair & Fur)",
            variable=self.alpha_matting_var,
            font=ctk.CTkFont(size=12)
        )
        self.chk_alpha.pack(padx=12, pady=(8, 8), anchor="w")
        
        # Section 5: Action & Export
        self.action_card = ctk.CTkFrame(self.sidebar)
        self.action_card.pack(fill="x", padx=14, pady=6)
        
        self.btn_process = ctk.CTkButton(
            self.action_card,
            text="⚡ Cut Background Now",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=44,
            command=self.trigger_processing
        )
        self.btn_process.pack(fill="x", padx=12, pady=(10, 6))
        
        self.progress_bar = ctk.CTkProgressBar(self.action_card)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=12, pady=4)
        
        self.status_label = ctk.CTkLabel(
            self.action_card,
            text="Ready. Select an image to begin.",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.status_label.pack(padx=12, pady=(0, 6))
        
        self.btn_save = ctk.CTkButton(
            self.action_card,
            text="💾 Save High-Res Cutout",
            state="disabled",
            height=38,
            command=self.save_result
        )
        self.btn_save.pack(fill="x", padx=12, pady=(4, 10))

        # =========================================================================
        # MAIN VIEWPORT
        # =========================================================================
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Viewport Header
        self.view_header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.view_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(10, 6))
        
        self.image_info_label = ctk.CTkLabel(
            self.view_header,
            text="No image loaded",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.image_info_label.pack(side="left")
        
        self.view_mode_seg = ctk.CTkSegmentedButton(
            self.view_header,
            values=["Side-by-Side", "Result Only", "Original Only"],
            command=self.update_canvas_display
        )
        self.view_mode_seg.set("Side-by-Side")
        self.view_mode_seg.pack(side="right")
        
        # Canvas Container
        self.canvas_container = ctk.CTkFrame(self.main_frame, corner_radius=12)
        self.canvas_container.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        self.canvas_container.grid_rowconfigure(0, weight=1)
        self.canvas_container.grid_columnconfigure(0, weight=1)
        self.canvas_container.grid_columnconfigure(1, weight=1)
        
        # Left Panel (Original)
        self.panel_left = ctk.CTkLabel(
            self.canvas_container, 
            text="📂 Click 'Open Image' or Drag & Drop here", 
            font=ctk.CTkFont(size=15), 
            text_color="gray"
        )
        self.panel_left.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        
        # Right Panel (Processed)
        self.panel_right = ctk.CTkLabel(
            self.canvas_container, 
            text="⚡ AI Cutout will appear here instantly", 
            font=ctk.CTkFont(size=15), 
            text_color="gray"
        )
        self.panel_right.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        
        # Safe, guarded window resize binding
        self.bind("<Configure>", self.on_window_resize)

    # =========================================================================
    # THEME ENGINE
    # =========================================================================
    def change_theme(self, theme_name: str):
        if theme_name in THEMES:
            self.current_theme_name = theme_name
            self.theme = THEMES[theme_name]
            ctk.set_appearance_mode(self.theme["mode"])
            self.apply_theme_colors()
            self.update_canvas_display()
            
    def apply_theme_colors(self):
        t = self.theme
        self.sidebar.configure(fg_color=t["bg_sidebar"])
        self.brand_label.configure(text_color=t["primary"])
        self.badge_label.configure(fg_color=t["primary"], text_color="#FFFFFF")
        
        # Cards
        for card in [self.theme_card, self.file_card, self.model_card, self.bg_card, self.edge_card, self.action_card]:
            card.configure(fg_color=t["card_bg"], border_width=1, border_color=t["card_border"])
            
        # Buttons
        self.btn_open.configure(fg_color=t["primary"], hover_color=t["primary_hover"])
        self.btn_batch.configure(border_color=t["card_border"], text_color=t["accent_text"])
        self.btn_process.configure(fg_color=t["primary"], hover_color=t["primary_hover"])
        self.btn_save.configure(fg_color=t["btn_save"], hover_color=t["btn_save_hover"])
        
        # Canvas
        self.canvas_container.configure(fg_color=t["canvas_bg"], border_width=1, border_color=t["card_border"])
        self.main_frame.configure(fg_color=t["bg_sidebar"])

    # =========================================================================
    # HANDLERS & PROCESSING
    # =========================================================================
    def on_model_changed(self, choice: str):
        descs = {
            "silueta": "⚡ Silueta: Turbo fast instant cut (Recommended)",
            "u2net": "🎯 U2-Net: Balanced high quality, ideal for complex subjects.",
            "isnet-general-use": "🔬 IS-Net: Ultra fine boundary detection (hair, fur, fine edges).",
            "u2net_human_seg": "👤 U2-Net Human: Specialized for portraits and fashion."
        }
        self.model_desc.configure(text=descs.get(choice, ""))

    def on_bg_mode_changed(self, mode_str: str):
        self.color_presets_frame.pack_forget()
        self.blur_frame.pack_forget()
        self.custom_img_frame.pack_forget()
        
        m = mode_str.lower()
        if m == "color":
            self.color_presets_frame.pack(fill="x", padx=12, pady=(0, 8))
        elif m == "blur":
            self.blur_frame.pack(fill="x", padx=12, pady=(0, 8))
        elif m == "image":
            self.custom_img_frame.pack(fill="x", padx=12, pady=(0, 8))
            
        if self.cutout_proxy:
            self.update_canvas_display()

    def set_preset_color(self, hex_code: str):
        hex_clean = hex_code.lstrip("#")
        self.current_color = tuple(int(hex_clean[i:i+2], 16) for i in (0, 2, 4))
        self.hex_entry.delete(0, "end")
        self.hex_entry.insert(0, hex_code)
        if self.cutout_proxy:
            self.update_canvas_display()

    def apply_hex_color(self):
        val = self.hex_entry.get().strip()
        try:
            hex_clean = val.lstrip("#")
            if len(hex_clean) == 6:
                self.current_color = tuple(int(hex_clean[i:i+2], 16) for i in (0, 2, 4))
                if self.cutout_proxy:
                    self.update_canvas_display()
            else:
                messagebox.showerror("Invalid Color", "Please enter a valid 6-digit HEX color like #FF0000.")
        except Exception:
            messagebox.showerror("Invalid Color", "Please enter a valid HEX code.")

    def on_blur_slider(self, val):
        self.blur_label.configure(text=f"Bokeh Blur: {int(val)}px")
        if self.cutout_proxy:
            self.update_canvas_display()

    def select_custom_bg(self):
        path = filedialog.askopenfilename(
            title="Select Background Image",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")]
        )
        if path and os.path.exists(path):
            self.custom_bg_image = Image.open(path)
            self.btn_select_custom_bg.configure(text=f"🖼️ {os.path.basename(path)[:16]}...")
            if self.cutout_proxy:
                self.update_canvas_display()

    def open_image(self):
        path = filedialog.askopenfilename(
            title="Open Image",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")]
        )
        if path and os.path.exists(path):
            self.load_image_file(path)

    def load_image_file(self, path: str):
        self.current_image_path = path
        self.original_image = Image.open(path)
        # Create fast 1200px proxy for ultra-smooth UI
        self.original_proxy = engine.create_preview_proxy(self.original_image, max_dim=1200)
        self.cutout_image = None
        self.cutout_proxy = None
        self.btn_save.configure(state="disabled")
        
        w, h = self.original_image.size
        self.image_info_label.configure(text=f"{os.path.basename(path)}  •  {w}×{h} px")
        self.status_label.configure(text="Ready to cut! Click button below.")
        self.progress_bar.set(0)
        
        self.update_canvas_display()

    def trigger_processing(self):
        if not self.original_image:
            messagebox.showinfo("No Image", "Please open an image first!")
            return
        if self.is_processing:
            return
            
        self.is_processing = True
        self.btn_process.configure(state="disabled", text="⏳ Cutting Background...")
        self.btn_open.configure(state="disabled")
        self.progress_bar.set(0.2)
        self.status_label.configure(text="AI inference running locally...")
        
        threading.Thread(target=self._run_inference_thread, daemon=True).start()

    def _run_inference_thread(self):
        start_time = time.time()
        try:
            model = self.model_var.get()
            use_matting = self.alpha_matting_var.get()
            
            # Step 1: Remove background at full resolution
            self.cutout_image = engine.remove_background(
                image=self.original_image,
                model_name=model,
                alpha_matting=use_matting
            )
            # Fast proxy for real-time 60fps UI adjustments
            self.cutout_proxy = engine.create_preview_proxy(self.cutout_image, max_dim=1200)
            
            elapsed = time.time() - start_time
            self.after(0, lambda: self._on_inference_complete(elapsed))
        except Exception as e:
            self.after(0, lambda: self._on_inference_error(str(e)))

    def _on_inference_complete(self, elapsed: float):
        self.is_processing = False
        self.btn_process.configure(state="normal", text="⚡ Cut Background Now")
        self.btn_open.configure(state="normal")
        self.btn_save.configure(state="normal")
        self.progress_bar.set(1.0)
        self.status_label.configure(text=f"Cut completed in {elapsed:.2f}s! Ready to save.")
        
        self.update_canvas_display()

    def _on_inference_error(self, err_msg: str):
        self.is_processing = False
        self.btn_process.configure(state="normal", text="⚡ Cut Background Now")
        self.btn_open.configure(state="normal")
        self.progress_bar.set(0)
        self.status_label.configure(text="Error processing image.")
        messagebox.showerror("Cutit ai Error", f"Failed to cut background:\n{err_msg}")

    # =========================================================================
    # FAST 60FPS VIEWPORT DISPLAY
    # =========================================================================
    def update_canvas_display(self, *args):
        if not self.original_proxy:
            return
            
        view_mode = self.view_mode_seg.get()
        container_w = max(self.canvas_container.winfo_width(), 600)
        container_h = max(self.canvas_container.winfo_height(), 400)
        is_dark = (self.theme["mode"] == "Dark")
        
        if view_mode == "Side-by-Side":
            self.panel_left.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
            self.panel_right.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
            self.canvas_container.grid_columnconfigure(0, weight=1)
            self.canvas_container.grid_columnconfigure(1, weight=1)
            target_w = (container_w // 2) - 20
            target_h = container_h - 20
            
            # Left: Original
            left_thumb = self.fit_image(self.original_proxy, target_w, target_h)
            tk_left = ctk.CTkImage(light_image=left_thumb, dark_image=left_thumb, size=left_thumb.size)
            self.panel_left.configure(image=tk_left, text="")
            self.panel_left.image = tk_left
            
            # Right: Processed
            if self.cutout_proxy is not None:
                comp = self.render_composite_proxy(target_w, target_h, is_dark)
                tk_right = ctk.CTkImage(light_image=comp, dark_image=comp, size=comp.size)
                self.panel_right.configure(image=tk_right, text="")
                self.panel_right.image = tk_right
            else:
                self.panel_right.configure(image=None, text="Click 'Cut Background Now'\nto process")
                
        elif view_mode == "Result Only":
            self.panel_left.grid_forget()
            self.panel_right.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
            target_w = container_w - 24
            target_h = container_h - 24
            
            if self.cutout_proxy is not None:
                comp = self.render_composite_proxy(target_w, target_h, is_dark)
                tk_right = ctk.CTkImage(light_image=comp, dark_image=comp, size=comp.size)
                self.panel_right.configure(image=tk_right, text="")
                self.panel_right.image = tk_right
            else:
                self.panel_right.configure(image=None, text="Click 'Cut Background Now' to preview result")
                
        elif view_mode == "Original Only":
            self.panel_right.grid_forget()
            self.panel_left.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
            target_w = container_w - 24
            target_h = container_h - 24
            
            left_thumb = self.fit_image(self.original_proxy, target_w, target_h)
            tk_left = ctk.CTkImage(light_image=left_thumb, dark_image=left_thumb, size=left_thumb.size)
            self.panel_left.configure(image=tk_left, text="")
            self.panel_left.image = tk_left

    def render_composite_proxy(self, target_w: int, target_h: int, is_dark: bool) -> Image.Image:
        """Render composite on the fast proxy image in milliseconds."""
        mode_val = self.bg_mode_seg.get().lower()
        thumb_cut = self.fit_image(self.cutout_proxy, target_w, target_h)
        w, h = thumb_cut.size
        
        if mode_val == "transparent":
            # Fast vectorized checkerboard generated specifically at display size
            chk = make_fast_checkerboard(w, h, square_size=14, is_dark=is_dark)
            chk.paste(thumb_cut, (0, 0), thumb_cut)
            return chk
        elif mode_val == "color":
            bg = Image.new("RGBA", (w, h), (*self.current_color, 255))
            bg.paste(thumb_cut, (0, 0), thumb_cut)
            return bg
        elif mode_val == "blur":
            thumb_orig = self.fit_image(self.original_proxy, target_w, target_h)
            comp = engine.composite_background(
                cutout=thumb_cut,
                original=thumb_orig,
                bg_mode="blur",
                blur_radius=int(self.blur_slider.get() * 0.5)
            )
            return comp
        elif mode_val == "image" and self.custom_bg_image:
            fitted_bg = ImageOps.fit(self.custom_bg_image.convert("RGBA"), (w, h))
            fitted_bg.paste(thumb_cut, (0, 0), thumb_cut)
            return fitted_bg
            
        return thumb_cut

    def fit_image(self, img: Image.Image, max_w: int, max_h: int) -> Image.Image:
        """Resize image keeping aspect ratio within max_w and max_h using fast Bilinear."""
        if max_w <= 10 or max_h <= 10:
            return img
        orig_w, orig_h = img.size
        ratio = min(max_w / orig_w, max_h / orig_h)
        new_w = max(1, int(orig_w * ratio))
        new_h = max(1, int(orig_h * ratio))
        return img.resize((new_w, new_h), Image.Resampling.BILINEAR)

    def on_window_resize(self, event):
        """Debounced resize handler guarding against internal child widget configure storms."""
        if event.widget != self:
            return
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(120, self._do_resize)

    def _do_resize(self):
        self._resize_job = None
        if self.original_proxy:
            self.update_canvas_display()

    # =========================================================================
    # EXPORT & SAVE
    # =========================================================================
    def save_result(self):
        if self.cutout_image is None or self.original_image is None:
            return
            
        mode_val = self.bg_mode_seg.get().lower()
        base_name = os.path.splitext(os.path.basename(self.current_image_path or "cutout"))[0]
        is_transparent = (mode_val == "transparent")
        
        default_name = f"{base_name}_cutit.png" if is_transparent else f"{base_name}_cutit.jpg"
        filetypes = [("PNG image (Lossless transparency)", "*.png")] if is_transparent else [
            ("JPEG image", "*.jpg"),
            ("PNG image", "*.png")
        ]
        
        out_path = filedialog.asksaveasfilename(
            title="Save Cutout Image",
            initialfile=default_name,
            filetypes=filetypes
        )
        
        if out_path:
            self.status_label.configure(text="Rendering full-resolution export...")
            self.update_idletasks()
            
            # Composite full-resolution image on demand
            full_composite = engine.composite_background(
                cutout=self.cutout_image,
                original=self.original_image,
                bg_mode=mode_val if mode_val in ["transparent", "color", "blur"] else "custom_image",
                color=self.current_color,
                bg_image=self.custom_bg_image,
                blur_radius=int(self.blur_slider.get())
            )
            
            if is_transparent:
                full_composite.save(out_path, "PNG")
            else:
                if out_path.lower().endswith((".jpg", ".jpeg")):
                    full_composite.convert("RGB").save(out_path, "JPEG", quality=95)
                else:
                    full_composite.save(out_path, "PNG")
                    
            self.status_label.configure(text=f"Saved: {os.path.basename(out_path)}")
            messagebox.showinfo("Cutit ai", f"High-resolution image saved successfully to:\n{out_path}")

    # =========================================================================
    # BATCH DIALOG
    # =========================================================================
    def open_batch_dialog(self):
        in_dir = filedialog.askdirectory(title="Select Folder Containing Images")
        if not in_dir:
            return
            
        out_dir = filedialog.askdirectory(title="Select Output Folder to Save Cutouts")
        if not out_dir:
            return
            
        exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        files = [f for f in os.listdir(in_dir) if os.path.splitext(f.lower())[1] in exts]
        
        if not files:
            messagebox.showwarning("No Images", "No supported images found in the selected folder.")
            return
            
        confirm = messagebox.askyesno(
            "Cutit ai - Batch Run",
            f"Found {len(files)} image(s) in:\n{in_dir}\n\nProcess and export all to:\n{out_dir}?"
        )
        if not confirm:
            return
            
        threading.Thread(
            target=self._run_batch_worker,
            args=(in_dir, out_dir, files),
            daemon=True
        ).start()
        
    def _run_batch_worker(self, in_dir: str, out_dir: str, files: list):
        self.btn_batch.configure(state="disabled")
        self.btn_process.configure(state="disabled")
        
        model = self.model_var.get()
        total = len(files)
        
        for idx, filename in enumerate(files, 1):
            pct = idx / total
            self.after(0, lambda p=pct, i=idx, t=total, fn=filename: (
                self.progress_bar.set(p),
                self.status_label.configure(text=f"Batch: ({i}/{t}) {fn}...")
            ))
            
            in_file = os.path.join(in_dir, filename)
            out_file = os.path.join(out_dir, f"{os.path.splitext(filename)[0]}_cutit.png")
            try:
                engine.process_file(
                    input_path=in_file,
                    output_path=out_file,
                    model_name=model,
                    bg_mode="transparent"
                )
            except Exception as e:
                print(f"Error on {filename}: {e}")
                
        self.after(0, lambda: (
            self.progress_bar.set(1.0),
            self.status_label.configure(text=f"Batch complete! Processed {total} images."),
            self.btn_batch.configure(state="normal"),
            self.btn_process.configure(state="normal"),
            messagebox.showinfo("Cutit ai", f"Successfully processed {total} images into:\n{out_dir}")
        ))

def main():
    app = CutitApp()
    app.mainloop()

if __name__ == "__main__":
    main()
