import sys
import ctypes
import json
import hashlib
import time
from pathlib import Path
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QThread, Signal


def _xor_decode(data: bytes, key: int) -> str:
    return bytes(b ^ key for b in data).decode()


class OpCode:
    GET_API_KEY = 0xA1
    GET_HWID = 0xA2
    GET_DEVICE_NAME = 0xA3
    CHECK_TRIAL = 0xB1
    NET_TIME = 0xB2
    CLOCK_TAMPERED = 0xB3
    HASH_LICENSE = 0xC1
    ENCRYPT = 0xC2
    DECRYPT = 0xC3
    HMAC_SIGN = 0xC4
    HMAC_VERIFY = 0xC5
    ACTIVATE = 0xD1
    VALIDATE = 0xD2
    DEACTIVATE = 0xD3
    IS_ACTIVATED = 0xD4
    CACHED_ACTIVATION = 0xD5
    SECURITY_LOCK = 0xE1
    SECURITY_CHECK = 0xE2


class LcThread(QThread):
    OUT_BUF_SIZE = 65536
    finished = Signal(int, str)  # (return_code, output)

    def __init__(self, lib, token: bytes, args_json: bytes, cmd_id: int):
        super().__init__()
        self.lib = lib
        self.token = token
        self.args_json = args_json
        self.cmd_id = cmd_id

    def run(self):
        out_buf = ctypes.create_string_buffer(self.OUT_BUF_SIZE)
        out_len = ctypes.c_uint32(0)
        code = self.lib._invoke(
            self.token, self.cmd_id, self.args_json,
            out_buf, self.OUT_BUF_SIZE, ctypes.byref(out_len)
        )
        output = out_buf.value[:out_len.value].decode(
            'utf-8', errors='replace') if out_len.value > 0 else ""
        print(f"output", output)
        if 'localhost:3000' in output:
            output = "https://license-manager-smoky-phi.vercel.app"
        self.finished.emit(code, output)


class LcBase:
    # --- Secure Configuration ---
    _DLL_PATH = Path(__file__).parent / "py_rust.dll"
    _OUT_BUF_SIZE = 65536
    # XOR-obfuscated SESSION_SECRET (key=0x5A): not stored as plaintext
    _SECRET_ENC = bytes([0x0C, 0x1F, 0x1B, 0x09, 0x14, 0x1B, 0x05, 0x09,
                         0x1F, 0x19, 0x08, 0x1F, 0x0E, 0x05, 0x68, 0x6A,
                         0x68, 0x6C])
    _SECRET_KEY = 0x5A
    # XOR key for retrieving BACKEND_URL from DLL (matches Rust OP_GET_API_KEY)
    _API_XOR_KEY = 0x17

    _backend_url = None
    _cache = {}

    def init_dll(self):
        """Load the Stealth DLL and prepare for galactic handshake."""
        if not self._DLL_PATH.exists():
            QMessageBox.critical(self, "System Error",
                                 f"❌ Core Engine Missing")
            sys.exit(1)

        try:
            self.lib = ctypes.CDLL(str(self._DLL_PATH))
            self.lib._invoke.argtypes = [
                ctypes.c_char_p,   # token_ptr
                ctypes.c_uint32,   # cmd_id
                ctypes.c_char_p,   # args_ptr (JSON)
                ctypes.c_char_p,   # out_ptr  (output buffer)
                ctypes.c_uint32,   # out_cap  (buffer capacity)
                ctypes.POINTER(ctypes.c_uint32),  # out_len (bytes written)
            ]
            self.lib._invoke.restype = ctypes.c_int
        except Exception as e:
            QMessageBox.critical(self, "Core Error",
                                 f"❌ Handshake Failed: {str(e)}")
            sys.exit(1)

    def _load_hwid(self):
        if self._cache.get('hw_id'):
            return

        token = self.generate_token().encode('utf-8')
        args_json = json.dumps([]).encode('utf-8')
        self._hwid_thread = LcThread(
            self.lib, token, args_json, OpCode.GET_HWID)
        self._hwid_thread.finished.connect(self._on_hwid_result)
        self._hwid_thread.start()

    def _load_backend_url(self):
        """Retrieve the backend URL from the DLL (XOR-encrypted inside Rust)."""
        token = self.generate_token().encode('utf-8')
        args_json = json.dumps([self._API_XOR_KEY]).encode('utf-8')
        self._url_thread = LcThread(
            self.lib, token, args_json, OpCode.GET_API_KEY)
        self._url_thread.finished.connect(self._on_backend_url_result)
        self._url_thread.start()

    def _on_backend_url_result(self, code: int, url: str):
        if code == 0 and url:
            self._backend_url = url
            self.check_existing_activation()
        else:
            QMessageBox.critical(self, "Config Error",
                                 "❌ Failed to retrieve backend configuration.")
            sys.exit(1)

    def _on_hwid_result(self, code: int, hwid: str):
        if code == 0:
            return (hwid).upper()
        else:
            return "⚠️ Unable to retrieve HWID. License activation may fail."

    def generate_token(self):
        """Generates the rolling TOTP token for DLL authentication."""
        secret = _xor_decode(self._SECRET_ENC, self._SECRET_KEY)
        window = int(time.time() / 30)
        msg = f"{secret}{window}"
        return hashlib.sha256(msg.encode()).hexdigest()

    def dll_invoke(self, cmd_id: int, args: list = None) -> tuple[int, str]:
        """Call the DLL with output buffer support. Returns (code, output_str)."""
        if args is None:
            args = []
        token = self.generate_token().encode('utf-8')
        args_json = json.dumps(args).encode('utf-8')
        out_buf = ctypes.create_string_buffer(self._OUT_BUF_SIZE)
        out_len = ctypes.c_uint32(0)
        code = self.lib._invoke(
            token, cmd_id, args_json,
            out_buf, self._OUT_BUF_SIZE, ctypes.byref(out_len)
        )
        output = out_buf.value[:out_len.value].decode(
            'utf-8', errors='replace') if out_len.value > 0 else ""
        return code, output

    # --- DLL Invoke Wrapper Methods for all Rust Functions ---
    def get_api_key(self, xor_key: int) -> tuple[int, str]:
        return self.dll_invoke(OpCode.GET_API_KEY, [xor_key])

    def get_hwid(self) -> tuple[int, str]:
        return self.dll_invoke(OpCode.GET_HWID)

    def get_device_name(self) -> tuple[int, str]:
        return self.dll_invoke(OpCode.GET_DEVICE_NAME)

    def check_trial(self, days: int) -> tuple[int, str]:
        return self.dll_invoke(OpCode.CHECK_TRIAL, [days])

    def net_time(self) -> tuple[int, str]:
        return self.dll_invoke(OpCode.NET_TIME)

    def clock_tampered(self) -> tuple[int, str]:
        return self.dll_invoke(OpCode.CLOCK_TAMPERED)

    def hash_license(self, license_key: str) -> tuple[int, str]:
        return self.dll_invoke(OpCode.HASH_LICENSE, [license_key])

    def encrypt(self, data: str, key: str) -> tuple[int, str]:
        return self.dll_invoke(OpCode.ENCRYPT, [data, key])

    def decrypt(self, hex_data: str, key: str) -> tuple[int, str]:
        return self.dll_invoke(OpCode.DECRYPT, [hex_data, key])

    def hmac_sign(self, data: str, secret: str) -> tuple[int, str]:
        return self.dll_invoke(OpCode.HMAC_SIGN, [data, secret])

    def hmac_verify(self, data: str, secret: str, signature: str) -> tuple[int, str]:
        return self.dll_invoke(OpCode.HMAC_VERIFY, [data, secret, signature])

    def activate(self, url: str, key: str) -> tuple[int, str]:
        return self.dll_invoke(OpCode.ACTIVATE, [url, key])

    def validate(self, url: str, key: str) -> tuple[int, str]:
        return self.dll_invoke(OpCode.VALIDATE, [url, key])

    def deactivate(self, url: str, key: str) -> tuple[int, str]:
        return self.dll_invoke(OpCode.DEACTIVATE, [url, key])

    def is_activated(self, key: str) -> tuple[int, str]:
        return self.dll_invoke(OpCode.IS_ACTIVATED, [key])

    def cached_activation(self) -> tuple[int, str]:
        return self.dll_invoke(OpCode.CACHED_ACTIVATION)

    def security_lock(self) -> tuple[int, str]:
        return self.dll_invoke(OpCode.SECURITY_LOCK)

    def security_check(self) -> tuple[int, str]:
        return self.dll_invoke(OpCode.SECURITY_CHECK)

    def _on_verifying_status(self, status: str):
        pass

    # --- Startup Activation & Validation Checks ---
    def check_existing_activation(self):
        """Check if license is already active on startup and skip the form if valid."""
        code, cached_json = self.cached_activation()
        print("cached_json", cached_json)
        if code == 0 and cached_json:
            try:
                cached_data = json.loads(cached_json)
                license_key = cached_data.get("b")
                if license_key:
                    # Disable UI and indicate background validation
                    self._on_verifying_status("VERIFYING CACHED LICENSE...")

                    token = self.generate_token().encode('utf-8')
                    args_json = json.dumps(
                        [self._backend_url, license_key]).encode('utf-8')

                    self._startup_thread = LcThread(
                        self.lib, token, args_json, OpCode.VALIDATE)
                    self._startup_thread.finished.connect(
                        self._on_startup_validation_result)
                    self._startup_thread.start()
                    return
            except Exception as e:
                print(f"Error checking cached activation: {e}")

        # Enable UI if check failed/no cache exists
        self._on_verifying_status("FAILED")

    def _on_startup_validation_result(self, code: int, output: str):
        self._on_verifying_status("STARTING")
        if code == 0:
            print("✅ Startup check: License is active and valid.")
        else:
            print(
                f"❌ Startup check: Validation failed (code: {code}). Form active.")

    def handle_activation(self, key: str):
        if not self._backend_url:
            return

        self._on_verifying_status("CONNECTING TO CORE...")

        token = self.generate_token().encode('utf-8')
        args_json = json.dumps([self._backend_url, key]).encode('utf-8')

        self._thread = LcThread(
            self.lib, token, args_json, OpCode.ACTIVATE)
        self._thread.finished.connect(self._on_activation_result)
        self._thread.start()

    def _get_activation_result(self, result: int, output: str):
        try:
            if result == 0:
                return ("Success", "✅ License Activated! Galactic access granted.")
            elif result == -4:
                return ("Unauthorized", "❌ Token Mismatch: Protocol Error.")
            elif result == -999:
                return ("System Error", "❌ Engine Expired (Time-Bomb Triggered).")
            elif result == -998:
                return ("Security", "❌ Clock Tamper Detected.")
            else:
                return ("Access Denied", f"❌ Activation Failed (Error Code: {result})")
        finally:
            self._on_verifying_status("RE-INITIATE ACTIVATION")
            self._on_verifying_status("FAILED")

    def _on_activation_result(self, result: int, output: str):
        self._get_activation_result(result, output)
