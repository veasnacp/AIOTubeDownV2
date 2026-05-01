from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class Callback:
    def __init__(self):
        pass

    def on_callback_progress(self, d: dict):
        pass

    def callbackProgress(self, d: dict):
        self.on_callback_progress(d)

    def on_callback_finished(self, d: dict):
        pass

    def callbackFinished(self, d: dict):
        self.on_callback_finished(d)

    def on_callback_retry(self, n: int):
        pass

    def callbackRetry(self, n: int):
        self.on_callback_retry(n)

    def on_callback_error(self, d: dict):
        pass

    def callbackError(self, d: dict):
        self.on_callback_error(d)


class WorkerSignals(QObject):
    # first int for task_id
    progress = Signal(int, dict)
    finished = Signal(int, dict)
    error = Signal(int, dict)
    retry = Signal(int, int)
    cancel = Signal(int)


class DefaultWorker(QRunnable):

    def __init__(self, task_id: int):
        super().__init__()

        self.task_id = task_id
        self.signals = WorkerSignals()
        self.is_paused = False
        self.cancel = False  # Add a flag to check for stop requests
        self.signals.cancel.connect(self.cancel_worker)  # Connect stop signal

    def on_cancel_worker(self, task_id: int):
        pass

    def cancel_worker(self, task_id: int):
        self.cancel = True
        self.on_cancel_worker(task_id)
