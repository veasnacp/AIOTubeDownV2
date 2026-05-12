
---

# 🔍 Current Project Review & Recommendations (May 12, 2026)

## ⚠️ Critical Issues Found

### 1. Lifecycle & Threading (Shutdown Hangs)
- **Problem**: `ThumbnailManager.remove_task` attempts to call `self.active_workers[task_id].cancel()`, but the `ThumbnailWorker` class in `app/core/thumbnail_manager.py` does **not** implement a `cancel()` method. This triggers an `AttributeError` during shutdown, potentially leaving threads running and preventing the process from terminating.
- **Problem**: `ExtractWorker` and `DownloadWorker` use `asyncio.run()`. If the app is closed while these are in the middle of a request, they may hang.
- **Fix**: Implement a `cancel()` method in all worker classes that sets a thread-safe flag (`self._is_cancelled`). Check this flag inside loops.

### 2. UI Performance (Main Thread Blocking)
- **Problem**: Extensive use of synchronous `sqlite3` calls. Every time `downloader_page.py` updates file details or `download_manager.py` updates progress, it opens/closes a connection or performs blocking I/O on the UI thread.
- **Fix**: Migrate to `aiosqlite` for background database operations or use a dedicated database thread with a queue.

### 3. Logic & Architecture
- **Problem**: `downloader_page.py` calls `thumbnail_manager.generate_thumbnails()` every time a selection changes. This triggers a `QProcess` (ffmpeg) task even if the thumbnail already exists in the cache.
- **Fix**: Check `thumbnail_manager.get_thumbnail(path)` first. Only trigger extraction if it returns `None`.
- **Problem**: `MainWindow.show_license_dialog` is defined but never called during initialization.
- **Fix**: Trigger the license check in `MainWindow.__init__` or `main.py` before showing the window.

## 🛠️ Actionable Recommendations

### Phase 1: Stability (High Priority)
1.  **Worker Cancellation**: Add `self._is_cancelled = False` and `def cancel(self): self._is_cancelled = True` to `ThumbnailWorker` and `ExtractWorker`.
2.  **Graceful Shutdown**: In `MainWindow.closeEvent`, ensure `QApplication.quit()` is removed or handled such that it doesn't interrupt the `waitForDone` timers of the managers.
3.  **Resource Cleanup**: Ensure `QMediaPlayer` (if used) or `ffmpeg` processes are explicitly killed when workers are cancelled.

### Phase 2: Performance & UX
1.  **Global Font Scaling**: Set the application font once in `main.py` using `QApplication.setFont()` to eliminate `setPointSize` warnings across the logs.
2.  **Throttled Updates**: The `DownloadManager.on_worker_progress` already has a 2-second throttle for DB writes, which is good. Ensure UI table updates are also throttled if there are hundreds of active tasks.
3.  **Mica & Styling**: Re-enable Mica effect if on Windows 11 for a more premium look.

### Phase 3: Feature Completeness
1.  **License Activation**: Implement the bootstrap logic to show `LicenseDialog` if not activated.
2.  **Automation**: Move `VideoConverter` logic into a worker so merging audio/video doesn't block the UI.