import os
import sqlite3

from loguru import logger

from ..config.constants import DB_NAME, DIRS


class Database:
    def __init__(self):
        db_dir = str(DIRS.user_data_dir)
        os.makedirs(db_dir, exist_ok=True)
        self.db_path = os.path.join(db_dir, DB_NAME)
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Table of download tasks
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                filename TEXT,
                save_path TEXT,
                category TEXT,
                size_total INTEGER DEFAULT 0,
                size_downloaded INTEGER DEFAULT 0,
                status TEXT,
                speed REAL DEFAULT 0,
                eta TEXT,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_completed TIMESTAMP,
                error_msg TEXT,
                segments INTEGER DEFAULT 1,
                priority TEXT DEFAULT 'Normal',
                metadata_json TEXT
            )
        ''')

        # Logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                download_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT,
                message TEXT,
                FOREIGN KEY (download_id) REFERENCES downloads(id)
            )
        ''')

        conn.commit()
        conn.close()
        logger.debug(f"Database initialized at {self.db_path}")

    def add_task(self, url, filename, save_path, category="Other", status="Queued", segments=1, priority="Normal", metadata_json=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO downloads (url, filename, save_path, category, status, segments, priority, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (url or 'unknown', filename, save_path, category, status, segments, priority, metadata_json))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    def update_task(self, task_id, **kwargs):
        if not kwargs:
            return
        conn = self.get_connection()
        cursor = conn.cursor()
        keys = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values())
        values.append(task_id)
        cursor.execute(f"UPDATE downloads SET {keys} WHERE id = ?", values)
        conn.commit()
        conn.close()

    def get_all_tasks(self):
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM downloads ORDER BY date_added ASC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def remove_task(self, task_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM downloads WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()


db = Database()
