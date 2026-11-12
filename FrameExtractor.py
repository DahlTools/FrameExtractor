import os
import sys
import json
import shutil
import subprocess
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Optional drag-and-drop hook
try:
    import windnd
    HAS_WINDND = True
except ImportError:
    HAS_WINDND = False

# Optional OpenCV fallback if ffmpeg is missing
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


def find_binary(name):
    """Find binary in PATH or adjacent directories."""
    path = shutil.which(name)
    if path:
        return path
    # Check current directory
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{name}.exe")
    if os.path.exists(local):
        return local
    return None


FFMPEG_PATH = find_binary("ffmpeg")
FFPROBE_PATH = find_binary("ffprobe")


def get_video_info(video_path):
    """Probe video details: width, height, fps, duration, nb_frames."""
    info = {
        "width": None,
        "height": None,
        "fps": 30.0,
        "duration": 0.0,
        "frames": 0,
    }

    if FFPROBE_PATH:
        try:
            cmd = [
                FFPROBE_PATH,
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate,nb_frames,duration",
                "-of", "json",
                video_path
            ]
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            res = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
            data = json.loads(res.stdout)
            streams = data.get("streams", [])
            if streams:
                s = streams[0]
                info["width"] = s.get("width")
                info["height"] = s.get("height")
                # Parse r_frame_rate
                fps_str = s.get("r_frame_rate", "30/1")
                if "/" in fps_str:
                    num, den = fps_str.split("/")
                    info["fps"] = float(num) / float(den) if float(den) != 0 else 30.0
                else:
                    info["fps"] = float(fps_str)
                info["duration"] = float(s.get("duration", 0.0) or 0.0)
                if s.get("nb_frames") and s.get("nb_frames") != "N/A":
                    info["frames"] = int(s["nb_frames"])
                elif info["duration"] > 0:
                    info["frames"] = int(info["duration"] * info["fps"])
                return info
        except Exception:
            pass

    # Fallback to OpenCV
    if HAS_CV2:
        try:
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                info["width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                info["height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                info["fps"] = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
                info["frames"] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                if info["fps"] > 0:
                    info["duration"] = info["frames"] / info["fps"]
                cap.release()
                return info
        except Exception:
            pass

    return info


__version__ = "1.0.0"


class FrameExtractorApp(tk.Tk):
    def __init__(self, initial_video=None):
        super().__init__()
        self.title(f"Frame Extractor v{__version__} - Full Resolution")
        self.geometry("640x560")
        self.minsize(580, 520)

        # Set window icon if present
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.video_path = None
        self.output_dir = None
        self.video_info = None
        self.is_extracting = False
        self.cancel_requested = False
        self.current_process = None

        self._build_ui()

        # Enable native drag-and-drop onto the window
        if HAS_WINDND:
            windnd.hook_dropfiles(self, func=self._on_windnd_drop)

        # If a video file was passed via command line (e.g. dropped onto exe/script icon)
        if initial_video and os.path.isfile(initial_video):
            self.after(200, lambda: self.load_video(initial_video))

    def _build_ui(self):
        # Apply modern ttk theme
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except Exception:
            pass

        padding = {"padx": 16, "pady": 8}

        # Header Title
        header_frame = tk.Frame(self, bg="#1e293b")
        header_frame.pack(fill=tk.X)

        title_container = tk.Frame(header_frame, bg="#1e293b")
        title_container.pack(side=tk.LEFT, padx=16, pady=10)

        header_title = tk.Label(
            title_container,
            text=f"Frame Extractor v{__version__}",
            font=("Segoe UI", 16, "bold"),
            fg="#f8fafc",
            bg="#1e293b"
        )
        header_title.pack(anchor="w")
        header_sub = tk.Label(
            title_container,
            text="Lossless 100% native resolution frame extractor",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#1e293b"
        )
        header_sub.pack(anchor="w")

        # Buy Me a Coffee button in header
        bmac_btn = tk.Button(
            header_frame,
            text="☕ Buy me a coffee",
            font=("Segoe UI", 9, "bold"),
            bg="#FFDD00",
            fg="#000000",
            activebackground="#FACC15",
            activeforeground="#000000",
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.open_buymeacoffee
        )
        bmac_btn.pack(side=tk.RIGHT, padx=16, pady=12)

        main_content = ttk.Frame(self, padding="14")
        main_content.pack(fill=tk.BOTH, expand=True)

        # Drag & Drop Zone
        self.drop_frame = tk.Frame(
            main_content,
            bg="#f1f5f9",
            bd=2,
            relief="groove",
            cursor="hand2"
        )
        self.drop_frame.pack(fill=tk.X, pady=(0, 10), ipady=12)
        self.drop_frame.bind("<Button-1>", lambda e: self.browse_video())

        self.drop_label_icon = tk.Label(
            self.drop_frame,
            text="📁",
            font=("Segoe UI", 24),
            bg="#f1f5f9",
            fg="#475569"
        )
        self.drop_label_icon.pack()
        self.drop_label_icon.bind("<Button-1>", lambda e: self.browse_video())

        self.drop_label_text = tk.Label(
            self.drop_frame,
            text="Drag & Drop video file here\nor click to browse",
            font=("Segoe UI", 10, "bold"),
            bg="#f1f5f9",
            fg="#334155"
        )
        self.drop_label_text.pack(pady=(4, 0))
        self.drop_label_text.bind("<Button-1>", lambda e: self.browse_video())

        # Video Info Panel
        info_frame = ttk.LabelFrame(main_content, text="Video Details", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.lbl_file = ttk.Label(info_frame, text="File: No video selected", font=("Segoe UI", 9))
        self.lbl_file.pack(anchor="w")

        self.lbl_res = ttk.Label(
            info_frame,
            text="Resolution: -- (100% Native Quality Retained)",
            font=("Segoe UI", 9, "bold"),
            foreground="#0369a1"
        )
        self.lbl_res.pack(anchor="w", pady=(3, 0))

        self.lbl_stats = ttk.Label(info_frame, text="Duration: -- | FPS: -- | Total Frames: --", font=("Segoe UI", 9))
        self.lbl_stats.pack(anchor="w", pady=(3, 0))

        # Settings
        settings_frame = ttk.LabelFrame(main_content, text="Extraction Options", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # Extraction mode
        mode_row = ttk.Frame(settings_frame)
        mode_row.pack(fill=tk.X, pady=2)
        ttk.Label(mode_row, text="Frames to Extract:").pack(side=tk.LEFT)

        self.extract_mode = tk.StringVar(value="all")
        ttk.Radiobutton(mode_row, text="Every Frame", variable=self.extract_mode, value="all", command=self._update_opts).pack(side=tk.LEFT, padx=(10, 8))
        ttk.Radiobutton(mode_row, text="1 per Second", variable=self.extract_mode, value="1fps", command=self._update_opts).pack(side=tk.LEFT, padx=8)
        ttk.Radiobutton(mode_row, text="Every N Frames", variable=self.extract_mode, value="step", command=self._update_opts).pack(side=tk.LEFT, padx=8)

        self.step_var = tk.IntVar(value=5)
        self.step_spin = ttk.Spinbox(mode_row, from_=2, to=1000, width=5, textvariable=self.step_var)
        self.step_spin.pack(side=tk.LEFT, padx=4)
        self.step_spin.configure(state="disabled")

        # Output format
        fmt_row = ttk.Frame(settings_frame)
        fmt_row.pack(fill=tk.X, pady=4)
        ttk.Label(fmt_row, text="Image Format:").pack(side=tk.LEFT)
        self.fmt_var = tk.StringVar(value="png")
        ttk.Radiobutton(fmt_row, text="PNG (Lossless / Exact Pixel Quality)", variable=self.fmt_var, value="png").pack(side=tk.LEFT, padx=(10, 8))
        ttk.Radiobutton(fmt_row, text="JPG (High Quality)", variable=self.fmt_var, value="jpg").pack(side=tk.LEFT, padx=8)

        # Output folder
        out_row = ttk.Frame(settings_frame)
        out_row.pack(fill=tk.X, pady=4)
        ttk.Label(out_row, text="Save To:").pack(side=tk.LEFT)
        self.out_entry = ttk.Entry(out_row)
        self.out_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        ttk.Button(out_row, text="Browse...", command=self.browse_output).pack(side=tk.LEFT)

        # Progress Section
        progress_frame = ttk.Frame(main_content)
        progress_frame.pack(fill=tk.X, pady=(6, 0))

        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 4))

        self.status_lbl = ttk.Label(progress_frame, text="Ready. Drag and drop a video to begin.", font=("Segoe UI", 9))
        self.status_lbl.pack(anchor="w")

        # Action Buttons
        btn_frame = ttk.Frame(main_content)
        btn_frame.pack(fill=tk.X, pady=(12, 0))

        self.btn_extract = ttk.Button(
            btn_frame,
            text="Extract Frames",
            command=self.start_extraction,
            state="disabled"
        )
        self.btn_extract.pack(side=tk.LEFT, padx=(0, 8), ipadx=8, ipady=3)

        self.btn_open_folder = ttk.Button(
            btn_frame,
            text="Open Output Folder",
            command=self.open_output_folder,
            state="disabled"
        )
        self.btn_open_folder.pack(side=tk.LEFT, ipadx=8, ipady=3)

        # Footer
        footer_frame = tk.Frame(main_content)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(12, 0))
        footer_lbl = tk.Label(
            footer_frame,
            text="Free & Open Source by DahlTools • Support development on Buy Me a Coffee ☕",
            font=("Segoe UI", 8),
            fg="#64748b",
            cursor="hand2"
        )
        footer_lbl.pack()
        footer_lbl.bind("<Button-1>", lambda e: self.open_buymeacoffee())

    def open_buymeacoffee(self):
        webbrowser.open("https://buymeacoffee.com/dahltools")

    def _update_opts(self):
        if self.extract_mode.get() == "step":
            self.step_spin.configure(state="normal")
        else:
            self.step_spin.configure(state="disabled")

    def _on_windnd_drop(self, files):
        if not files:
            return
        # file might be bytes in python
        first = files[0]
        if isinstance(first, bytes):
            first = first.decode("utf-8", errors="ignore")
        self.load_video(first)

    def browse_video(self):
        types = [
            ("Video Files", "*.mp4 *.mov *.avi *.mkv *.webm *.flv *.wmv *.m4v *.ts"),
            ("All Files", "*.*")
        ]
        path = filedialog.askopenfilename(title="Select Video File", filetypes=types)
        if path:
            self.load_video(path)

    def browse_output(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_dir = folder
            self.out_entry.delete(0, tk.END)
            self.out_entry.insert(0, folder)

    def load_video(self, video_path):
        if not os.path.isfile(video_path):
            messagebox.showerror("Error", f"File does not exist:\n{video_path}")
            return

        self.video_path = video_path
        base_name = os.path.basename(video_path)
        dir_name = os.path.dirname(video_path)
        name_only = os.path.splitext(base_name)[0]

        # Default output folder next to video
        self.output_dir = os.path.join(dir_name, f"{name_only}_frames")
        self.out_entry.delete(0, tk.END)
        self.out_entry.insert(0, self.output_dir)

        # Visual indicator in drop frame
        self.drop_label_icon.config(text="🎬")
        self.drop_label_text.config(text=f"Loaded: {base_name}\n(Click to choose another)")
        self.lbl_file.config(text=f"File: {video_path}")
        self.status_lbl.config(text="Analyzing video properties...")
        self.update_idletasks()

        # Probe video
        info = get_video_info(video_path)
        self.video_info = info

        if info["width"] and info["height"]:
            self.lbl_res.config(
                text=f"Resolution: {info['width']} x {info['height']} (100% Native Quality Retained)"
            )
        else:
            self.lbl_res.config(text="Resolution: Native Video Resolution (Preserved)")

        dur_str = f"{info['duration']:.1f}s" if info["duration"] else "Unknown"
        fps_str = f"{info['fps']:.2f}" if info["fps"] else "Unknown"
        frames_str = f"~{info['frames']}" if info["frames"] else "Unknown"
        self.lbl_stats.config(text=f"Duration: {dur_str} | FPS: {fps_str} | Est. Total Frames: {frames_str}")

        self.status_lbl.config(text="Ready to extract. Choose options and click 'Extract Frames'.")
        self.btn_extract.configure(state="normal")
        self.btn_open_folder.configure(state="disabled")

    def open_output_folder(self):
        folder = self.out_entry.get().strip()
        if folder and os.path.exists(folder):
            if sys.platform == "win32":
                os.startfile(folder)
            else:
                subprocess.Popen(["xdg-open", folder])
        else:
            messagebox.showinfo("Folder", "Output folder has not been created yet.")

    def start_extraction(self):
        if self.is_extracting:
            # Handle Cancel
            self.cancel_requested = True
            self.status_lbl.config(text="Cancelling extraction...")
            if self.current_process:
                try:
                    self.current_process.terminate()
                except Exception:
                    pass
            return

        if not self.video_path or not os.path.exists(self.video_path):
            messagebox.showwarning("Warning", "Please select a valid video file first.")
            return

        output_dir = self.out_entry.get().strip()
        if not output_dir:
            messagebox.showwarning("Warning", "Please specify an output folder.")
            return

        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        self.is_extracting = True
        self.cancel_requested = False
        self.btn_extract.config(text="Cancel Extraction")
        self.btn_open_folder.configure(state="disabled")
        self.progress_bar.config(mode="indeterminate")
        self.progress_bar.start(10)
        self.status_lbl.config(text="Extracting frames at full resolution...")

        t = threading.Thread(target=self._run_extraction_thread, daemon=True)
        t.start()

    def _run_extraction_thread(self):
        fmt = self.fmt_var.get()
        mode = self.extract_mode.get()
        step = self.step_var.get()

        success = False
        count = 0
        error_msg = None

        if FFMPEG_PATH:
            success, count, error_msg = self._extract_ffmpeg(fmt, mode, step)
        elif HAS_CV2:
            success, count, error_msg = self._extract_cv2(fmt, mode, step)
        else:
            error_msg = "Neither FFmpeg nor OpenCV is available on this system."

        self.after(0, lambda: self._on_extraction_complete(success, count, error_msg))

    def _extract_ffmpeg(self, fmt, mode, step):
        ext = "png" if fmt == "png" else "jpg"
        out_pattern = os.path.join(self.output_dir, f"frame_%05d.{ext}")

        cmd = [FFMPEG_PATH, "-y", "-i", self.video_path]

        # Filtering based on extraction mode
        if mode == "1fps":
            cmd.extend(["-vf", "fps=1"])
        elif mode == "step":
            # Select every Nth frame
            cmd.extend(["-vf", f"select=not(mod(n\\,{step}))", "-vsync", "0"])
        else:
            # All frames, exact original native
            cmd.extend(["-vsync", "0"])

        if fmt == "png":
            # Lossless PNG, full quality
            cmd.extend(["-c:v", "png"])
        else:
            # High-quality JPEG
            cmd.extend(["-q:v", "1"])

        cmd.append(out_pattern)

        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startupinfo
            )
            _, stderr = self.current_process.communicate()

            if self.cancel_requested:
                return False, 0, "Extraction cancelled by user."

            if self.current_process.returncode != 0:
                return False, 0, stderr or "FFmpeg process returned an error."

            # Count generated files
            files = [f for f in os.listdir(self.output_dir) if f.startswith("frame_") and f.endswith(f".{ext}")]
            return True, len(files), None

        except Exception as e:
            return False, 0, str(e)
        finally:
            self.current_process = None

    def _extract_cv2(self, fmt, mode, step):
        ext = "png" if fmt == "png" else "jpg"
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            return False, 0, "Could not open video file."

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_idx = 0
        saved_count = 0

        while True:
            if self.cancel_requested:
                cap.release()
                return False, saved_count, "Extraction cancelled by user."

            ret, frame = cap.read()
            if not ret:
                break

            should_save = False
            if mode == "all":
                should_save = True
            elif mode == "1fps":
                if frame_idx % max(1, int(fps)) == 0:
                    should_save = True
            elif mode == "step":
                if frame_idx % step == 0:
                    should_save = True

            if should_save:
                saved_count += 1
                out_path = os.path.join(self.output_dir, f"frame_{saved_count:05d}.{ext}")
                cv2.imwrite(out_path, frame)

            frame_idx += 1

        cap.release()
        return True, saved_count, None

    def _on_extraction_complete(self, success, count, error_msg):
        self.is_extracting = False
        self.progress_bar.stop()
        self.progress_bar.config(mode="determinate", value=100 if success else 0)
        self.btn_extract.config(text="Extract Frames")

        if success:
            res_str = ""
            if self.video_info and self.video_info.get("width"):
                res_str = f" at {self.video_info['width']}x{self.video_info['height']} resolution"
            self.status_lbl.config(
                text=f"✓ Done! Extracted {count} frames{res_str}."
            )
            self.btn_open_folder.configure(state="normal")
            messagebox.showinfo(
                "Complete",
                f"Successfully extracted {count} frames{res_str}!\n\nSaved to:\n{self.output_dir}"
            )
        else:
            self.status_lbl.config(text=f"Error: {error_msg}")
            messagebox.showerror("Extraction Failed", f"Extraction error:\n{error_msg}")


def main():
    initial_video = None
    if len(sys.argv) > 1:
        initial_video = sys.argv[1]

    app = FrameExtractorApp(initial_video=initial_video)
    app.mainloop()


if __name__ == "__main__":
    main()
