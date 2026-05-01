import subprocess
import hashlib
import os
import json
from pathlib import Path
from ..config.constants import APP_NAME

class LicenseManager:
    def __init__(self):
        self.license_file = Path(os.getenv("APPDATA")) / APP_NAME / "license.json"
        self.license_file.parent.mkdir(parents=True, exist_ok=True)
        self.hw_id = self._get_hardware_id()

    def _get_hardware_id(self) -> str:
        """Generates a unique hardware ID for the machine."""
        try:
            # Use WMIC to get the machine UUID
            cmd = 'wmic csproduct get uuid'
            uuid = subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()
            if not uuid or 'UUID' in uuid:
                # Fallback to baseboard serial number
                cmd = 'wmic baseboard get serialnumber'
                uuid = subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()

            # Hash it to make it look cleaner and provide some obfuscation
            return hashlib.sha256(uuid.encode()).hexdigest().upper()[:24]
        except Exception:
            # Absolute fallback
            import uuid
            return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest().upper()[:24]

    def is_activated(self) -> bool:
        """Checks if the license is valid and activated for this machine."""
        if not self.license_file.exists():
            return False

        try:
            with open(self.license_file, 'r') as f:
                data = json.load(f)
                key = data.get("key")
                hw_id = data.get("hw_id")

                if hw_id != self.hw_id:
                    return False

                return self.validate_key(key)
        except Exception:
            return False

    def validate_key(self, key: str) -> bool:
        """
        Validates the license key.
        For now, we'll use a simple logic: The key's hash must match a certain pattern
        or we can just check if it's the 'hardware-tied' key.
        In a real app, this would call an API.
        """
        if not key or len(key) < 10:
            return False

        # Simplified validation: key must match the hash of hardware ID + 'VeasNa'
        expected_key = hashlib.sha256((self.hw_id + "VeasNa").encode()).hexdigest().upper()[:16]
        # For this demo/task, let's just accept any key that starts with 'VN-' for now?
        # No, let's make it look real.
        return key == expected_key

    def activate(self, key: str) -> bool:
        """Attempts to activate the license with the given key."""
        if self.validate_key(key):
            try:
                with open(self.license_file, 'w') as f:
                    json.dump({"key": key, "hw_id": self.hw_id}, f)
                return True
            except Exception:
                return False
        return False

# Global instance
license_manager = LicenseManager()
