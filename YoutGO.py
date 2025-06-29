import sys
import os
import locale
import threading
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QCheckBox, QFileDialog, QTextEdit,
    QProgressBar, QListWidget, QListWidgetItem, QFrame, QMessageBox
)
from PyQt6.QtGui import QIcon, QPixmap, QAction
from PyQt6.QtCore import Qt, QTimer, QLocale
import qdarktheme as pyqtdarktheme

# Use yt-dlp (pip install yt-dlp)
import yt_dlp

# --- App meta ---
APP_NAME = "YoutGO"
APP_VERSION = "1.2.0"
APP_OWNER = "MJ"
APP_COMPANY = "MineGO Studio"
APP_DATE = "2025/6/29"

# --- Color tokens (Material/Brand) ---
MINEGO_PRIMARY = "#F84D39"    # Red
MINEGO_YELLOW = "#F8B530"     # Yellow
MINEGO_GREEN = "#1CE8A3"      # Green
MINEGO_SURFACE_DARK = "#22232A"
MINEGO_SURFACE_LIGHT = "#FFFFFF"
MINEGO_TEXT_DARK = "#EFEFEF"
MINEGO_TEXT_LIGHT = "#1a1a1a"

# --- Paths ---
def default_download_path():
    home = os.path.expanduser("~")
    path = os.path.join(home, "YoutGO downloads")
    os.makedirs(path, exist_ok=True)
    return path

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".youtgo_settings.json")
HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".youtgo_history.json")

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"download_path": default_download_path()}

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f)

def detect_os_language():
    try:
        lang = QLocale.system().name()
        if lang:
            return lang.split("_")[0]
    except Exception:
        pass
    try:
        lang = locale.getdefaultlocale()[0]
        if lang:
            return lang.split("_")[0]
    except Exception:
        pass
    return "en"

def resource_path(filename):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)

# --- Splash Screen ---
class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(480, 300)
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_path = resource_path("icon_transparent.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(112, 112, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation)
            logo_label = QLabel()
            logo_label.setPixmap(pix)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo_label)

        title = QLabel(f"<b style='font-size:30pt'>{APP_NAME}</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Modern YouTube Downloader\nby MineGO Studio")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size:13pt; color: #666;")
        layout.addWidget(subtitle)
        layout.addSpacing(24)
        loading = QLabel("Loading…")
        loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(loading)
        self.setLayout(layout)

class DownloadItem:
    def __init__(self, url, title=None, status="Waiting", progress=0):
        self.url = url
        self.title = title or url
        self.status = status
        self.progress = progress

class YoutGOApp(QMainWindow):
    def __init__(self, app, lang='en'):
        super().__init__()
        self.app = app
        self.lang = lang
        self.setWindowTitle(f"{APP_NAME} - YouTube Downloader")
        self.setWindowIcon(QIcon(resource_path("icon.ico")))
        self.setMinimumSize(980, 700)
        self.tray_icon = None
        self.tray_enabled = False

        # State
        self.settings = load_settings()
        self.download_path = self.settings.get("download_path", default_download_path())
        self.queue = []
        self.downloading = False
        self.history = []

        self.tabs = QTabWidget(documentMode=True)
        self.setCentralWidget(self.tabs)

        self.setup_menus()
        self.tabs.addTab(self.home_tab(), self.tr("Home"))
        self.tabs.addTab(self.history_tab(), self.tr("History"))
        self.tabs.addTab(self.about_tab(), self.tr("About"))
        self.tabs.addTab(self.license_tab(), self.tr("License"))
        self.apply_theme("dark")
        self.setup_clipboard_monitor()

    def setup_menus(self):
        menubar = self.menuBar()
        view_menu = menubar.addMenu(self.tr("View"))
        self.toggle_theme_action = QAction(self.tr("Dark Mode"), self, checkable=True)
        self.toggle_theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(self.toggle_theme_action)
        self.toggle_theme_action.setChecked(True)
        edit_menu = menubar.addMenu(self.tr("Edit"))
        browse_action = QAction(self.tr("Change Download Folder"), self)
        browse_action.triggered.connect(self.choose_folder)
        edit_menu.addAction(browse_action)

    def toggle_theme(self, checked):
        self.apply_theme("dark" if checked else "light")

    def apply_theme(self, mode):
        self.current_theme = mode
        pyqtdarktheme.setup_theme(
            mode,
            corner_shape="rounded",
            custom_colors={
                "primary": MINEGO_PRIMARY,
                "background": MINEGO_SURFACE_LIGHT if mode == "light" else MINEGO_SURFACE_DARK,
            }
        )

    # --- Home Tab ---
    def home_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(14)
        # Title
        title = QLabel("YoutGO")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size:20pt; font-weight:700; color:{MINEGO_PRIMARY};")
        layout.addWidget(title)
        # Link input
        hlayout = QHBoxLayout()
        self.link_input = QTextEdit()
        self.link_input.setPlaceholderText(self.tr("Paste YouTube links (one per line)"))
        self.link_input.setMinimumHeight(60)
        hlayout.addWidget(self.link_input)
        add_btn = QPushButton("Add to Queue")
        add_btn.clicked.connect(self.add_links_to_queue)
        hlayout.addWidget(add_btn)
        layout.addLayout(hlayout)
        # Queue list
        self.queue_list = QListWidget()
        layout.addWidget(self.queue_list)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_selected_from_queue)
        layout.addWidget(remove_btn)
        # Download options
        opt_layout = QHBoxLayout()
        opt_layout.addWidget(QLabel("Format:"))
        self.format_box = QComboBox()
        self.format_box.addItems(["mp4", "mp3", "m4a", "wav"])
        opt_layout.addWidget(self.format_box)
        opt_layout.addSpacing(14)
        opt_layout.addWidget(QLabel("Quality:"))
        self.quality_box = QComboBox()
        self.quality_box.addItems(["best", "1080p", "720p", "480p", "360p", "audio only"])
        opt_layout.addWidget(self.quality_box)
        opt_layout.addSpacing(14)
        opt_layout.addWidget(QLabel("Download at the same time:"))
        self.threads_box = QComboBox()
        self.threads_box.addItems([str(i) for i in range(1, 6)])
        self.threads_box.setCurrentText("2")
        opt_layout.addWidget(self.threads_box)
        opt_layout.addSpacing(14)
        self.playlist_box = QCheckBox("Download full playlist if link is playlist")
        opt_layout.addWidget(self.playlist_box)
        layout.addLayout(opt_layout)
        # Output folder display
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Download folder:"))
        self.folder_label = QLabel(self.download_path)
        folder_layout.addWidget(self.folder_label)
        folder_btn = QPushButton("Browse")
        folder_btn.clicked.connect(self.choose_folder)
        folder_layout.addWidget(folder_btn)
        folder_layout.addStretch()
        layout.addLayout(folder_layout)
        # Download button
        self.download_btn = QPushButton("Start Download")
        self.download_btn.clicked.connect(self.start_download_batch)
        layout.addWidget(self.download_btn)
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        layout.addWidget(self.progress)
        # Log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(80)
        layout.addWidget(self.log)
        return w

    def add_links_to_queue(self):
        links = self.link_input.toPlainText().strip().splitlines()
        for link in links:
            link = link.strip()
            if link and link not in [self.queue_list.item(i).text() for i in range(self.queue_list.count())]:
                self.queue_list.addItem(link)
        self.link_input.clear()

    def remove_selected_from_queue(self):
        for item in self.queue_list.selectedItems():
            self.queue_list.takeItem(self.queue_list.row(item))

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder", self.download_path)
        if folder:
            self.download_path = folder
            self.folder_label.setText(folder)
            self.settings['download_path'] = folder
            save_settings(self.settings)

    def start_download_batch(self):
        if self.downloading:
            self.log.append("Already downloading, please wait...")
            return
        urls = [self.queue_list.item(i).text() for i in range(self.queue_list.count())]
        if not urls:
            self.log.append("No links in the queue.")
            return
        fmt = self.format_box.currentText()
        qual = self.quality_box.currentText()
        n_threads = int(self.threads_box.currentText())
        as_playlist = self.playlist_box.isChecked()
        folder = self.download_path
        self.downloading = True
        self.download_btn.setEnabled(False)
        self.progress.setValue(0)
        self.log.clear()

        # Prepare list of DownloadItem
        items = [DownloadItem(url) for url in urls]

        # Threading download for batch
        def download_all():
            completed = 0
            for i, item in enumerate(items):
                # Skip file if exists
                fn_guess = self.guess_filename(item.url, fmt, folder)
                if fn_guess and os.path.exists(fn_guess):
                    self.log.append(f"[SKIP] {fn_guess} already exists.")
                    continue
                result = self.download_one(item.url, fmt, qual, as_playlist, folder)
                self.log.append(result)
                completed += 1
                pct = int((completed / len(items)) * 100)
                QTimer.singleShot(0, lambda v=pct: self.progress.setValue(v))
            self.log.append("Batch done.")
            self.downloading = False
            self.download_btn.setEnabled(True)

        threading.Thread(target=download_all, daemon=True).start()

    def guess_filename(self, url, fmt, folder):
        # Quick guess for filename (for skip)
        try:
            info = yt_dlp.YoutubeDL().extract_info(url, download=False)
            title = info.get('title', 'video')
            ext = fmt if fmt != "audio only" else "mp3"
            filename = f"{title}.{ext}"
            return os.path.join(folder, filename)
        except Exception:
            return None

    def download_one(self, url, fmt, qual, as_playlist, folder):
        ydl_opts = {
            "outtmpl": os.path.join(folder, "%(title)s.%(ext)s"),
            "quiet": True,
            "noplaylist": not as_playlist,
            "format": None
        }
        # Format
        if fmt == "mp3":
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        elif fmt == "wav":
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            }]
        elif fmt == "m4a":
            ydl_opts["format"] = "bestaudio[ext=m4a]"
        else:  # mp4 or default
            if qual == "best":
                ydl_opts["format"] = "bestvideo+bestaudio/best"
            elif qual == "audio only":
                ydl_opts["format"] = "bestaudio/best"
            else:
                height = qual.replace("p", "")
                ydl_opts["format"] = f"bestvideo[height={height}]+bestaudio/best"
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return f"[OK] {url}"
        except Exception as e:
            return f"[ERROR] {url} :: {e}"

    # --- History tab stub ---
    def history_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.addWidget(QLabel("History will be here (Phase 2)."))
        return w

    # --- About/License ---
    def about_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setAlignment(Qt.AlignmentFlag.AlignTop)
        l.addSpacing(30)
        title = QLabel(f"{APP_NAME} — YouTube Downloader")
        title.setStyleSheet(f"font-size:20pt; font-weight:700; color:{MINEGO_PRIMARY};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(title)
        subtitle = QLabel(f"Version {APP_VERSION} | Created {APP_DATE} | by {APP_OWNER} / {APP_COMPANY}")
        subtitle.setStyleSheet("font-size:13pt; color: #888;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(subtitle)
        info = QLabel("YoutGO is a privacy-friendly YouTube downloader for personal use.\nContact: minego.studios@gmail.com | Discord: @mnjaa64")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("font-size:12pt; color:#222;")
        l.addWidget(info)
        return w

    def license_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setAlignment(Qt.AlignmentFlag.AlignTop)
        l.addSpacing(30)
        title = QLabel("License Agreement")
        title.setStyleSheet(f"font-size:17pt; font-weight:700; color:{MINEGO_PRIMARY};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(title)
        try:
            with open(resource_path("LICENSE.txt"), "r", encoding="utf-8") as f:
                text = f.read()
        except:
            text = "License file not found."
        tb = QTextEdit()
        tb.setReadOnly(True)
        tb.setPlainText(text)
        tb.setStyleSheet("font-size:11pt; background:#282a36; border-radius:10px; color: #F8B530;")
        l.addWidget(tb)
        return w

    # --- Clipboard monitor ---
    def setup_clipboard_monitor(self):
        clipboard = self.app.clipboard()
        clipboard.dataChanged.connect(self.check_clipboard_for_url)

    def check_clipboard_for_url(self):
        text = self.app.clipboard().text()
        if text and ("youtube.com" in text or "youtu.be" in text):
            if text not in [self.queue_list.item(i).text() for i in range(self.queue_list.count())]:
                self.queue_list.addItem(text)
                self.log.append(f"[Clipboard] Added {text}")

def main():
    app = QApplication(sys.argv)
    lang = detect_os_language()
    splash = SplashScreen()
    splash.show()

    def start_main():
        global main_window
        splash.close()
        try:
            main_window = YoutGOApp(app, lang=lang)
            main_window.show()
            print("Main window launched successfully!")
        except Exception as e:
            import traceback
            print("=== App crashed! ===")
            traceback.print_exc()
            msg = QMessageBox()
            msg.setWindowTitle("App Startup Error")
            msg.setText(f"YoutGO failed to launch!\n\n{e}")
            msg.setDetailedText(traceback.format_exc())
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.exec()

    QTimer.singleShot(1700, start_main)
    sys.exit(app.exec())



if __name__ == "__main__":
    main()
