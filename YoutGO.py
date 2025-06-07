import sys
import os
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText
from tkinter import filedialog, PhotoImage, ttk, Toplevel, StringVar, BooleanVar
import threading
import yt_dlp
import logging

# --- App meta ---
APP_NAME = "YoutGO"
APP_VERSION = "1.1.3"
APP_OWNER = "MJ"
APP_COMPANY = "MineGO Studio"
APP_DATE = "2025/6/6"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def center_window(win, width, height):
    win.update_idletasks()
    screen_width = win.winfo_screenwidth()
    screen_height = win.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")

logging.basicConfig(filename='ytdl_app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

try:
    with open(resource_path("LICENSE.txt"), "r", encoding="utf-8") as f:
        LICENSE_TEXT = f.read()
except Exception:
    LICENSE_TEXT = "License file not found."

ABOUT_TEXT = (
    f"{APP_NAME} — YouTube Downloader\n"
    f"Version {APP_VERSION}\n"
    f"Created: {APP_DATE}\n"
    f"By {APP_OWNER} / {APP_COMPANY}\n\n"
    "YoutGO is a privacy-friendly, personal-use YouTube downloader built for speed, reliability, "
    "and a premium user experience. Redistribution and reverse engineering are prohibited.\n"
    "See License tab for full terms."
)

class YoutGOApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} - YouTube Downloader")
        self.root.geometry("930x770")
        self.root.resizable(False, False)
        try:
            self.root.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass

        self.download_path = tb.StringVar(value=os.path.expanduser("~"))
        self.style = tb.Style(theme="flatly")  # Trusted, light, harmonious

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=0, pady=0)

        # -------- Home Tab --------
        home_frame = tb.Frame(notebook, bootstyle=SECONDARY)
        notebook.add(home_frame, text="  Home  ")

        # --- Header with Card Style and Logo ---
        header_frame = tb.Frame(home_frame, bootstyle=LIGHT)
        header_frame.pack(pady=(8, 0), padx=0, fill="x")
        try:
            logo_img_raw = PhotoImage(file=resource_path("icon_transparent.png"))
            # Scale the logo to about 32px high (emoji: ~26–32px), keeping aspect ratio
            logo_h = logo_img_raw.height()
            scale = max(1, int(logo_h / 128))  # integer scaling
            logo_img = logo_img_raw.subsample(scale)
            icon_label = tb.Label(header_frame, image=logo_img, bootstyle=INFO)
            icon_label.image = logo_img  # Prevent garbage collection
            icon_label.pack(side="left", padx=(15, 12), pady=4)
        except Exception:
            icon_label = tb.Label(header_frame, text="🎬", font=("Segoe UI Emoji", 26), bootstyle=PRIMARY)
            icon_label.pack(side="left", padx=(15, 12), pady=4)
        title_label = tb.Label(header_frame, text="YoutGO", font=("Segoe UI", 20, "bold"), bootstyle=PRIMARY)
        title_label.pack(side="left", padx=(0, 4), pady=4)
        subtitle = tb.Label(header_frame, text="Safe & Fast YouTube Downloads — by MineGO Studio",
                            font=("Segoe UI", 11), bootstyle=INFO)
        subtitle.pack(side="left", padx=18, pady=4)


        # --- Input + Controls (No Overflow, Large and Clear) ---
        input_frame = tb.LabelFrame(home_frame, text=" Paste Links Below ", bootstyle=PRIMARY)
        input_frame.pack(padx=18, pady=(18, 10), fill="x")
        self.links_text = ScrolledText(input_frame, width=100, height=5, font=("Segoe UI", 10), bootstyle=INFO)
        self.links_text.pack(padx=8, pady=10, fill="x")

        controls_frame = tb.LabelFrame(home_frame, text=" Choose Options ", bootstyle=PRIMARY)
        controls_frame.pack(padx=18, pady=4, fill="x")

        # Output format selector
        self.format_var = tb.StringVar(value="mp4")
        tb.Label(controls_frame, text="Format:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, padx=(8, 3), pady=8, sticky="w")
        self.format_box = ttk.Combobox(controls_frame, values=["mp4", "mp3", "m4a", "wav"], textvariable=self.format_var, width=8, state="readonly")
        self.format_box.grid(row=0, column=1, padx=(0, 15), pady=8, sticky="w")
        self.format_box.set("mp4")

        # Quality selector
        self.quality_var = tb.StringVar(value="best")
        tb.Label(controls_frame, text="Quality:", font=("Segoe UI", 10, "bold")).grid(row=0, column=2, padx=(8, 3), pady=8, sticky="w")
        self.quality_box = ttk.Combobox(controls_frame, values=["best", "1080p", "720p", "480p", "360p", "audio only"], textvariable=self.quality_var, width=12, state="readonly")
        self.quality_box.grid(row=0, column=3, padx=(0, 15), pady=8, sticky="w")
        self.quality_box.set("best")

        # Max threads
        tb.Label(controls_frame, text="Parallel:", font=("Segoe UI", 10, "bold")).grid(row=0, column=4, padx=(8, 3), pady=8, sticky="w")
        self.max_threads_var = tb.IntVar(value=2)
        self.threads_box = ttk.Combobox(controls_frame, values=[1, 2, 3, 4, 5], textvariable=self.max_threads_var, width=3, state="readonly")
        self.threads_box.grid(row=0, column=5, padx=(0, 8), pady=8, sticky="w")
        self.threads_box.set("2")

        # Playlist
        self.playlist_var = BooleanVar(value=False)
        tb.Checkbutton(
            controls_frame,
            text="Download all videos from playlist links",
            variable=self.playlist_var,
            bootstyle=INFO
        ).grid(row=0, column=6, padx=(10, 4), pady=8, sticky="w")

        # Output path
        path_frame = tb.LabelFrame(home_frame, text=" Save To ", bootstyle=PRIMARY)
        path_frame.pack(padx=18, pady=(10, 8), fill="x")
        tb.Label(path_frame, text="Folder:", font=("Segoe UI", 10)).pack(side="left", padx=(12, 3), pady=6)
        self.path_label = tb.Label(path_frame, textvariable=self.download_path, font=("Consolas", 10), bootstyle=INFO)
        self.path_label.pack(side="left", padx=8)
        tb.Button(path_frame, text="Browse", bootstyle=SECONDARY, command=self.browse_path).pack(side="left", padx=8)

        # Download button (big and inviting)
        self.download_btn = tb.Button(
            home_frame,
            text="⬇ Download All",
            bootstyle=SUCCESS,
            command=self.start_batch_download,
            width=25,
            padding=8
        )
        self.download_btn.pack(pady=(10, 2))

        # Progress Bar (wider, no overflow)
        progress_frame = tb.Frame(home_frame, bootstyle=SECONDARY)
        progress_frame.pack(pady=(3, 0))
        self.progress_var = tb.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=600, mode="determinate", variable=self.progress_var)
        self.progress_bar.pack(side="left", padx=(25, 8))
        self.percent_var = StringVar(value="0%")
        self.percent_label = tb.Label(progress_frame, textvariable=self.percent_var, font=("Segoe UI", 10, "bold"), bootstyle=INFO)
        self.percent_label.pack(side="left", padx=2)

        # Status/Log (spacious, readable)
        log_frame = tb.LabelFrame(home_frame, text=" Status & Log ", bootstyle=INFO)
        log_frame.pack(padx=18, pady=(12, 7), fill="both", expand=True)
        self.status_text = ScrolledText(log_frame, width=107, height=7, font=("Consolas", 10), bootstyle=LIGHT)
        self.status_text.pack(padx=8, pady=8, fill="both", expand=True)
        self.status_text.text.config(state="disabled")

        # --- About Tab ---
        about_frame = tb.Frame(notebook)
        notebook.add(about_frame, text="  About  ")
        about_card = tb.Frame(about_frame, bootstyle=LIGHT)
        about_card.pack(pady=35, padx=22, fill="both", expand=True)
        tb.Label(
            about_card, text=APP_NAME, font=("Segoe UI", 21, "bold"), bootstyle=PRIMARY
        ).pack(pady=(0, 8))
        tb.Label(
            about_card, text=f"Version: {APP_VERSION}    Created: {APP_DATE}", font=("Segoe UI", 11, "italic"), bootstyle=INFO
        ).pack(pady=(0, 16))
        tb.Label(
            about_card,
            text="YoutGO is a privacy-friendly, modern YouTube downloader for personal use.\nDeveloped by MJ (MineGO Studio).",
            font=("Segoe UI", 12),
            bootstyle=SECONDARY,
            justify="center"
        ).pack(pady=(0, 16))
        tb.Label(
            about_card,
            text="Contact: coming soon  |  https://minego.studio/",
            font=("Segoe UI", 10, "underline"),
            bootstyle=INFO
        ).pack(pady=(0, 8))

        # --- License Tab ---
        license_frame = tb.Frame(notebook)
        notebook.add(license_frame, text="  License  ")
        license_card = tb.Frame(license_frame, bootstyle=LIGHT)
        license_card.pack(padx=18, pady=18, fill="both", expand=True)
        tb.Label(
            license_card,
            text="License Agreement",
            font=("Segoe UI", 15, "bold"),
            bootstyle=PRIMARY,
        ).pack(pady=(0, 12))
        license_text = ScrolledText(license_card, width=94, height=18, font=("Consolas", 9), bootstyle=INFO)
        license_text.pack(padx=4, pady=4, fill="both", expand=True)
        license_text.text.insert("1.0", LICENSE_TEXT)
        license_text.text.config(state="disabled")

        tb.Label(
            root,
            text=f"© {APP_DATE[:4]} {APP_OWNER} / {APP_COMPANY} | Personal use only | Do not redistribute or decompile",
            font=("Segoe UI", 8),
            bootstyle=SECONDARY
        ).pack(side="bottom", pady=4)

    def browse_path(self):
        folder = filedialog.askdirectory()
        if folder:
            self.download_path.set(folder)

    def start_batch_download(self):
        links = self.links_text.get("1.0", "end").strip()
        link_list = [l.strip() for l in links.splitlines() if l.strip()]
        if not link_list:
            tb.dialogs.messagebox.show_error("Input Error", "Please enter at least one valid YouTube link.")
            return
        self.download_btn.config(state="disabled")
        self.progress_var.set(0)
        self.percent_var.set("0%")
        self.status_text.text.config(state="normal")
        self.status_text.text.delete("1.0", "end")
        self.status_text.text.insert("end", f"🚀 Downloading {len(link_list)} link(s) (up to {self.max_threads_var.get()} at once)...\n")
        self.status_text.text.config(state="disabled")
        download_as_playlist = self.playlist_var.get()
        format_choice = self.format_var.get()
        quality_choice = self.quality_var.get()
        max_threads = self.max_threads_var.get()
        download_path = self.download_path.get()

        def download_worker(url):
            self.progress_var.set(0)
            self.percent_var.set("0%")
            self.download_video(
                url, format_choice, download_path,
                as_playlist=download_as_playlist, quality=quality_choice)

        def batch_threader():
            threads = []
            for link in link_list:
                while True:
                    threads = [t for t in threads if t.is_alive()]
                    if len(threads) < max_threads:
                        t = threading.Thread(target=download_worker, args=(link,), daemon=True)
                        t.start()
                        threads.append(t)
                        break
                    else:
                        import time; time.sleep(0.1)
            for t in threads:
                t.join()
            self.download_btn.config(state="normal")
        threading.Thread(target=batch_threader, daemon=True).start()

    def download_video(self, url, format_choice, path, as_playlist=False, quality="best"):
        if not url.startswith("http"):
            self.update_status(url, "❌ Skipped: Invalid URL.\n", "danger")
            return
        ydl_opts = {
            "outtmpl": os.path.join(path, "%(title)s.%(ext)s"),
            "quiet": True,
            "progress_hooks": [lambda d: self.hook(d, url)],
            "geo_bypass": True,
        }
        ydl_opts["noplaylist"] = not as_playlist
        if format_choice == "mp3":
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]
            })
        elif format_choice == "wav":
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    "preferredquality": "0",
                }]
            })
        elif format_choice == "m4a":
            ydl_opts.update({
                "format": "bestaudio[ext=m4a]",
            })
        else:
            format_str = None
            if quality == "best":
                format_str = "bestvideo+bestaudio/best"
            elif quality == "audio only":
                format_str = "bestaudio/best"
            else:
                format_str = f'bestvideo[height={quality.replace("p","")}]'+\
                    '+bestaudio/best'
            ydl_opts.update({
                "format": format_str,
                "merge_output_format": "mp4" if format_choice == "mp4" else format_choice
            })
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.update_status(url, "✅ Download completed.\n", "success")
            logging.info(f"Download successful: {url} as {format_choice} ({quality})")
        except Exception as e:
            self.update_status(url, f"❌ Download failed: {str(e)}\n", "danger")
            logging.error(f"Error downloading {url}: {e}")
        self.progress_var.set(0)
        self.percent_var.set("0%")

    def hook(self, d, url):
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes', d.get('total_bytes_estimate', 0))
            if total:
                percent = min(max(downloaded / total * 100, 0), 100)
                self.progress_var.set(percent)
                self.percent_var.set(f"{int(percent)}%")
                self.progress_bar.update_idletasks()
        elif d['status'] == 'finished':
            self.progress_var.set(100)
            self.percent_var.set("100%")
            self.progress_bar.update_idletasks()
            self.update_status(url, "🛠️ Processing...\n", "warning")

    def update_status(self, url, msg, style, replace_last=False):
        self.status_text.text.config(state="normal")
        color = {"success": "#30e36b", "danger": "#ff4848", "info": "#007bff", "warning": "#ffb347"}
        tag = style
        if tag not in self.status_text.text.tag_names():
            self.status_text.text.tag_configure(tag, foreground=color[style])
        if replace_last:
            content = self.status_text.text.get("1.0", "end")
            lines = content.strip().split('\n')
            if lines:
                lines[-1] = f"[{url[:40]}...] {msg.strip()}"
                self.status_text.text.delete("1.0", "end")
                for ln in lines:
                    self.status_text.text.insert("end", ln + "\n", tag)
            else:
                self.status_text.text.insert("end", f"[{url[:40]}...] {msg}", tag)
        else:
            self.status_text.text.insert("end", f"[{url[:40]}...] {msg}", tag)
        self.status_text.text.see("end")
        self.status_text.text.config(state="disabled")

def show_splash_and_start():
    root = tb.Window(themename="flatly")
    root.withdraw()
    splash = Toplevel(root)
    splash.overrideredirect(True)
    center_window(splash, 500, 300)
    try:
        splash_img = PhotoImage(file=resource_path("splash.png"))
        splash_label = tb.Label(splash, image=splash_img)
        splash_label.image = splash_img
        splash_label.pack(fill="both", expand=True)
    except Exception:
        splash_label = tb.Label(splash, text=APP_NAME, font=("Segoe UI", 30, "bold"), bootstyle=PRIMARY)
        splash_label.pack(fill="both", expand=True)
    tb.Label(
        splash,
        text=f"Powered by {APP_OWNER} | {APP_NAME}\nPlease wait...",
        font=("Segoe UI", 12),
        bootstyle=SECONDARY
    ).pack(side="bottom", pady=8)

    def start_main_app():
        splash.destroy()
        root.deiconify()
        YoutGOApp(root)
    splash.after(2000, start_main_app)
    root.mainloop()

if __name__ == "__main__":
    show_splash_and_start()
