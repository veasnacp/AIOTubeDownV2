You are an expert Python developer. Build a full-featured Internet Download Manager (IDM) clone application using:

- **GUI**: PySide6 + qfluentwidgets (https://github.com/zhiyiYo/PyQt-Fluent-Widgets)
- **Download engine**: yt-dlp (for video/audio URLs) + aiohttp + curl_cffi (for direct file downloads)
- **Threading**: QThreadPool + QRunnable (never block the main UI thread)
- **Database**: SQLite via aiosqlite or sqlite3 (for persistent download history/queue)
- **Other utilities**: humanize, psutil, validators, filetype, tqdm (internal), platformdirs, keyring

---

## 🏗️ Project Structure

Organize the project as:

AIOTubeDown/
├── main.py                      # App entry point (bootstrap)
├── generate_resource.py         # QRC resource generator
├── app/
│   ├── main.py                  # Core app initialization
│   ├── __init__.py
│   ├── common/
│   │   ├── resource.qrc         # Qt resources
│   │   ├── resource_rc.py       # Compiled resources
│   │   └── images/              # Assets (logos, brand icons, drama logos)
│   ├── components/              # Custom reusable widgets
│   │   ├── icons.py             # Icon management
│   │   ├── icon_card.py         # Custom cards
│   │   ├── override.py          # QFluentWidgets overrides
│   │   └── __init__.py
│   ├── core/                    # Background logic & Workers
│   │   ├── download_manager.py  # Central manager
│   │   ├── download_worker.py   # Download execution
│   │   ├── extract_manager.py   # Extraction orchestration
│   │   ├── convert_worker.py    # Format conversion
│   │   ├── license_manager.py   # HWID license check
│   │   └── _worker.py           # Base worker class
│   ├── db/
│   │   └── database.py          # SQLite database logic
│   ├── extractor/               # Platform-specific scraping
│   │   ├── douyin.py, tiktok.py, youtube.py, etc.
│   │   ├── drama.py             # Drama-specific extraction logic
│   │   ├── _request.py          # Base request handler
│   │   └── _utils.py            # Extraction utilities
│   ├── theme/                   # Dynamic design system
│   │   ├── colors.py            # Color palette tokens
│   │   ├── theme.py             # Theme manager
│   │   └── theme_provider.py    # QSS generator
│   ├── ui/                      # Fluent UI Pages & Dialogs
│   │   ├── main_window.py       # MainWindow shell
│   │   ├── downloader_page.py   # Standard downloader interface
│   │   ├── drama_downloader_page.py # Drama tabbed interface
│   │   ├── download_table.py    # Custom table implementation
│   │   ├── add_url_dialog.py    # URL ingestion
│   │   ├── settings_page.py     # App settings
│   │   └── sidebar.py           # Navigation logic
│   ├── utils/
│   │   └── path.py              # Path resolution utilities
│   └── config/
│       ├── settings.py          # QSettings wrapper
│       └── constants.py         # Global constants
├── requirements.txt
└── README.md

---

## 📦 Core Features to Implement

### 1. Download Table (deep clone of IDM's table)
Use QFluentWidgets `TableWidget` or a custom `QTableView` with a `QAbstractTableModel`.

Columns:
- [ ] # (row number)
- [ ] Filename (with file type icon)
- [ ] Size (auto-formatted: KB/MB/GB)
- [ ] Status (badge: Downloading / Paused / Complete / Error / Queued)
- [ ] Time Left
- [ ] Transfer Rate (rolling average)
- [ ] Progress (inline QProgressBar widget, per row)

Features inside the table:
- Right-click context menu per row: Open File, Open Folder, Copy URL, Retry, Remove, Properties
- Double-click row → open TaskDetailDialog
- Sortable columns (click header)
- Drag-to-reorder queued tasks
- Color-coded rows: green=complete, yellow=paused, red=error, blue=downloading
- Batch select with Ctrl+A, Shift+Click
- Inline progress bar that shows segment chunks visually (like IDM's segmented bar)

### 2. Add URL Dialog
- Single URL input with real-time URL validation
- Auto-analyze URL on paste:
  - Detect if YouTube/Vimeo/etc. → show format selector (via yt-dlp info_dict)
  - Detect if direct file → show filename, estimated size, file type icon
  - Detect playlist → offer "Download All" or select specific items
- Fields: URL, Filename (editable), Save-to folder (browse), Category, Priority (Low/Normal/High)
- "Start immediately" toggle
- Batch URL input tab (paste multiple URLs)
- Authentication fields (username/password or cookie file for yt-dlp)
- Referrer / custom headers (advanced toggle)

### 3. Download Worker (QRunnable — NEVER freeze UI)
Implement `DownloadWorker(QRunnable)`:
- Emit signals via a `WorkerSignals(QObject)` helper:
  - `progress(task_id, bytes_downloaded, total_bytes, speed, eta)`
  - `status_changed(task_id, new_status)`
  - `finished(task_id, filepath)`
  - `error(task_id, error_message)`
  - `log(task_id, message)`

For direct HTTP downloads:
- Use `curl_cffi` with streaming + `asyncio` (run in thread via `asyncio.run()` or `QThread`)
- Support multi-segment (split file into N chunks, download in parallel, merge)
- Resume support via `Range` headers + `.part` temp file
- Auto-retry on failure (configurable: 1–10 retries with backoff)

For video/audio URLs:
- Use `yt-dlp` subprocess or Python API
- Capture `yt-dlp` progress hook and forward to WorkerSignals
- Support format selection (best, 1080p, 720p, audio-only, mp3, etc.)

### 4. Download Manager (Central Controller)
`DownloadManager(QObject)` is the app brain:
- Maintains a dict of `task_id → DownloadTask`
- Manages `QThreadPool` with configurable `maxThreadCount` (default: 3)
- Queues excess tasks and starts them when slots free up
- Methods: `add_task()`, `pause_task()`, `resume_task()`, `cancel_task()`, `retry_task()`, `remove_task()`
- Emits model-level signals to update UI table
- Saves/loads all tasks from SQLite on start/exit
- Graceful shutdown: pauses all active downloads, saves state

### 5. Settings Dialog (full IDM-style)
Tabs:
- **General**: Default download folder, auto-start on launch, start minimized, language
- **Connection**: Max simultaneous downloads (1–16), max segments per download (1–32), speed limit (KB/s global cap), retry count, timeout
- **File Types**: Associate file extensions → auto-download (zip, mp4, mp3, pdf, exe, etc.)
- **Video/Audio**: Default yt-dlp format, subtitle language, embed thumbnail, prefer ffmpeg path
- **Notifications**: Desktop toast on complete, sound alert, system tray behavior
- **Scheduler**: Schedule downloads in a time window (e.g., 2am–6am)
- **Proxy**: HTTP/SOCKS5 proxy settings (passed to curl_cffi + yt-dlp)
- **Security**: Virus scan on complete (launch external scanner), warn on .exe, HTTPS-only mode
- **Appearance**: Theme (Light/Dark/Auto via qfluentwidgets), accent color, font size, table density (compact/normal/comfortable)
- **Advanced**: Temp folder, log level, clear history button, export/import settings (JSON)

All settings persist via `QSettings` (INI or Registry on Windows).

### 6. Sidebar Navigation
Using `qfluentwidgets.NavigationPanel` or `FluentWindow`:
- 📥 All Downloads (count badge)
- ⬇️ Downloading (live count)
- ✅ Completed
- ⏸ Paused
- ❌ Failed
- 🗂 Categories: Video, Audio, Documents, Archives, Programs, Other
- Each category filters the table view

### 7. Toolbar
Using `qfluentwidgets` `ToolBar` or custom:
- ➕ Add URL
- ⏸ Pause Selected
- ▶ Resume Selected
- ⏹ Stop All
- 🗑 Delete Selected
- 🗑 Delete All Completed
- 🔍 Search bar (filters table by filename)
- View toggle: Table / List

### 8. Clipboard Watcher
- `ClipboardWatcher` using `QClipboard.dataChanged` signal
- Detect valid URLs (http/https) automatically
- Show a floating "Add Download?" toast popup (non-intrusive)
- Configurable ON/OFF in settings

### 9. Speed Chart
- Embed a live-updating speed graph in the status bar or sidebar
- Use `pyqtgraph` `PlotWidget` or `QChart` (from PySide6.QtCharts)
- Shows last 60 seconds of combined download speed
- Updates every 1 second via `QTimer`

### 10. System Tray
- Tray icon with tooltip showing active downloads count + total speed
- Right-click menu: Show Window, Pause All, Resume All, Open Downloads Folder, Settings, Exit
- Minimize to tray on close (configurable)

### 11. Task Detail Dialog
When user double-clicks a row:
- Show full task info: URL, filename, save path, size, progress, speed, ETA, status, date started, date completed
- Log viewer: scrollable text area with yt-dlp / curl_cffi output
- Segmented progress bar showing each chunk's download status
- Buttons: Open File, Open Folder, Copy URL, Retry, Close

### 12. Database Schema (SQLite)

Tables:
- `downloads`: id, url, filename, save_path, category, size_total, size_downloaded, status, speed, eta, date_added, date_completed, error_msg, segments, priority, retries, metadata_json
- `settings`: key, value (flat key-value store)
- `categories`: id, name, color, icon, filter_extensions
- `logs`: id, download_id, timestamp, level, message

Use migrations for schema versioning.

---

## ⚡ Performance & Anti-Freeze Rules

- **NEVER** call blocking I/O or yt-dlp in the main thread
- All downloads run in `QThreadPool` via `QRunnable`
- Use `WorkerSignals` (QObject with pyqtSignal) to send updates back to UI
- `QTimer` at 500ms interval refreshes the table model (batch updates, not per-byte)
- Use `QAbstractTableModel` with `dataChanged` signals instead of rebuilding rows
- Debounce rapid signal emissions (e.g., 100ms throttle on progress updates)
- Database writes happen in a background thread, not UI thread
- Speed calculation uses a sliding window average (last 5 seconds)

---

## 🔒 Security Requirements

- Validate all URLs before processing (use `validators` library)
- Sanitize filenames (strip `../`, null bytes, reserved names on Windows)
- Never execute downloaded files automatically
- Warn user before downloading .exe, .bat, .sh, .msi files
- Support HTTPS-only mode (reject http:// URLs if enabled)
- Store credentials (if any) via `keyring` library, never plaintext
- Respect `Content-Disposition` headers but validate against path traversal
- Optional: compute SHA256 hash of completed files for integrity verification

---

## 📋 requirements.txt

PySide6
PyQt-Fluent-Widgets[full]
yt-dlp
curl_cffi
aiofiles
aiosqlite
validators
humanize
psutil
filetype
pyqtgraph
platformdirs
keyring
loguru
ffmpeg-python

---

## 🎨 UI/UX Guidelines

- Use `qfluentwidgets.FluentWindow` as the base (built-in nav + fluent design)
- Use `qfluentwidgets.TableWidget` for the download table with custom delegates
- Use `qfluentwidgets.ProgressBar` inside table cells via `QTableWidget.setCellWidget()`
- Use `qfluentwidgets.InfoBar` for toast notifications (success, warning, error)
- Use `qfluentwidgets.Dialog` for all modal dialogs
- Use `qfluentwidgets.SettingCard` / `SettingCardGroup` for the settings page
- Use `qfluentwidgets.FluentIcon` for all icons
- Support Light / Dark / Auto theme via `qfluentwidgets.setTheme()`
- Accent color matches system accent on Windows 11 via `qfluentwidgets.setThemeColor()`
- Status badges: use `qfluentwidgets.Tag` or colored `QLabel` with rounded stylesheet

---

## 🚀 Startup Behavior

1. Initialize SQLite DB (create tables if not exists)
2. Load all incomplete/paused tasks from DB → restore to queue
3. Load settings from QSettings
4. Start clipboard watcher
5. Show main window (or tray-only if "start minimized" is set)
6. Auto-resume tasks that were active before last close (if setting enabled)

---

## 🛑 Graceful Shutdown

On app close:
1. Pause all active downloads (send stop signal to workers)
2. Save current progress of each task to DB
3. Cancel QThreadPool workers
4. Stop clipboard watcher
5. Hide to tray OR quit (per setting)

---

Build this as a complete, production-quality Python application. Each file should be fully implemented — no placeholder code or `pass` stubs. Use `loguru` for logging throughout. Follow PEP8 and add type hints everywhere. The app should feel as fast and smooth as the real IDM.