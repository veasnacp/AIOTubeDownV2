import asyncio
import base64
import json
import logging
import re
import tempfile
from pathlib import Path
from urllib.parse import quote, urlparse

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from loguru import logger


def test_youtube_extractor():
    from .extractor.youtube import YouTubeExtractor

    youtube = YouTubeExtractor()
    youtube.set_test_mode(True)
    # asyncio.run(youtube.test_get_video_info_list())

    info_list = youtube.load_test_data()
    if info_list:
        asyncio.run(youtube.download_all_videos(
            info_list, with_site_name=True, with_channel_name=True, is_test=True))


def test_tiktok_extractor():
    from .extractor.tiktok import TikTokExtractor

    tiktok = TikTokExtractor()
    tiktok.set_test_mode(True)
    # asyncio.run(tiktok.test_get_video_info_list())
    asyncio.run(tiktok.test_get_video_info_list_from_user())

    # info_list = tiktok.load_test_data()
    # if info_list:
    #     asyncio.run(tiktok.download_all_videos(
    #         info_list, with_site_name=True, with_channel_name=True, is_test=True))


def test_douyin_extractor():
    from .extractor.douyin import DouyinExtractor, get_all_videos

    douyin = DouyinExtractor()
    douyin.set_test_mode(True)
    # asyncio.run(douyin.test_get_video_info_list())
    # asyncio.run(douyin.test_get_video_info_list_from_user())

    asyncio.run(get_all_videos())


def test_kuaishou_extractor():
    from .extractor.kuaishou import run_multitasking_scout

    asyncio.run(run_multitasking_scout())


def test_drama_sansekai_extractor():
    from .extractor.test import DramaSansekaiExtractor

    dramasansekai = DramaSansekaiExtractor()
    asyncio.run(dramasansekai.test_get_drama_info())

    # dramasansekai.set_test_mode(True)
    # info = dramasansekai.load_test_data()
    # if info:
    #     asyncio.run(dramasansekai.download_all_episodes(
    #         info, with_site_name=True, is_test=True))


def test_drama_box_extractor():
    from .extractor.drama import DramaBoxExtractor

    dramabox = DramaBoxExtractor()
    # asyncio.run(dramabox.test_get_drama_info())

    # dramabox.set_test_mode(True)
    # info = dramabox.load_test_data()
    # if info:
    #     asyncio.run(dramabox.download_all_episodes(
    #         info, with_site_name=True, is_test=True))


def test_reelshort_extractor():
    from .extractor.drama import ReelShortExtractor

    dramareel = ReelShortExtractor()
    # asyncio.run(dramareel.test_get_drama_info())

    dramareel.set_test_mode(True)
    info = dramareel.load_test_data()
    if info:
        asyncio.run(dramareel.download_all_episodes(
            info, with_site_name=True, is_test=True))


def test_dramabite_extractor():
    from .extractor.drama import DramaBiteExtractor

    dramabite = DramaBiteExtractor()
    # asyncio.run(dramabite.test_get_drama_info())
    dramabite.set_test_mode(True)
    info = dramabite.load_test_data()
    if info:
        asyncio.run(dramabite.download_all_episodes(
            info, with_site_name=True, is_test=True))


def test_shortmovs_extractor():
    from .extractor.drama import ShortMovsExtractor

    shortmovs = ShortMovsExtractor()
    # asyncio.run(shortmovs.test_get_drama_info())
    # asyncio.run(shortmovs.test_download_m3u8())
    # asyncio.run(shortmovs.download_m3u8())
    shortmovs.set_test_mode(True)
    info = shortmovs.load_test_data()
    if info:
        asyncio.run(shortmovs.download_all_episodes(
            info, with_site_name=True, is_test=True))


def test_rushtv_extractor():
    from .extractor.drama import RushTvExtractor

    rushtv = RushTvExtractor()
    # asyncio.run(rushtv.test_get_drama_info())
    rushtv.set_test_mode(True)
    info = rushtv.load_test_data()
    if info:
        asyncio.run(rushtv.download_all_episodes(
            info, with_site_name=True, is_test=True))


def test_stardusttv_extractor():
    from .extractor.drama import StardustTvExtractor

    stardust = StardustTvExtractor()
    asyncio.run(stardust.test_get_drama_info())
    # stardust.set_test_mode(True)
    # info = stardust.load_test_data()
    # if info:
    #     asyncio.run(stardust.download_all_episodes(
    #         info, with_site_name=True, is_test=True))


def _stardust_decrypt_payload(enc_b64):
    _STARDUST_AES_KEY_HEX = "1a7ce951829164550b49e7896be06150386d5cfb34f4533cd23a623414454d1e"
    raw = base64.b64decode(str(enc_b64 or ""))
    if len(raw) <= 16:
        return ""
    iv = raw[:16]
    ct = raw[16:]
    cipher = AES.new(bytes.fromhex(_STARDUST_AES_KEY_HEX), AES.MODE_CBC, iv)
    data = cipher.decrypt(ct)
    pad = data[-1]
    if 1 <= pad <= 16:
        data = data[:-pad]
    return data.decode("utf-8", errors="replace")


class ShortTvCrypto:
    def __init__(self, secret_key="shortwebapiaesen", wrap_in_object=False):
        self.secret_key = secret_key.encode('utf-8')
        self.iv = secret_key.encode('utf-8')  # IV matches key per your TS code
        self.wrap_in_object = wrap_in_object

    def encrypt_data(self, data):
        """Encrypts data using AES/CBC/PKCS7."""
        try:
            # Convert to JSON string if data is a dict or list
            plain_text = json.dumps(data) if isinstance(
                data, (dict, list)) else str(data)

            cipher = AES.new(self.secret_key, AES.MODE_CBC, self.iv)

            # Add PKCS7 padding and encrypt
            encrypted_bytes = cipher.encrypt(
                pad(plain_text.encode('utf-8'), AES.block_size))

            return base64.b64encode(encrypted_bytes).decode('utf-8')
        except Exception as e:
            print(f"Encryption failed: {e}")
            raise Exception("Data encryption failed")

    def decrypt_data(self, encrypted_data):
        """Decrypts a Base64 string using AES/CBC/PKCS7."""
        try:
            raw_data = base64.b64decode(encrypted_data)
            cipher = AES.new(self.secret_key, AES.MODE_CBC, self.iv)

            # Decrypt and remove PKCS7 padding
            decrypted_bytes = unpad(cipher.decrypt(raw_data), AES.block_size)
            decrypted_str = decrypted_bytes.decode('utf-8')

            if not decrypted_str:
                raise Exception("Decryption resulted in empty string")

            try:
                return json.loads(decrypted_str)
            except (json.JSONDecodeError, TypeError):
                return decrypted_str
        except Exception as e:
            print(f"Decryption failed: {e}")
            raise Exception(f"Data decryption failed: {e}")

    def encrypt_request_params(self, params, wrap_in_object=None):
        """Encrypts request parameters and wraps them in an object if required."""
        should_wrap = wrap_in_object if wrap_in_object is not None else self.wrap_in_object
        encrypted = self.encrypt_data(params)
        return {"data": encrypted} if should_wrap else encrypted

    def decrypt_response_data(self, response):
        """Decrypts API response data based on its format."""
        if not response:
            return response

        # Case 1: Response is a direct encrypted string
        if isinstance(response, str):
            return self.decrypt_data(response)

        # Case 2: Response is a dict containing an encrypted 'data' field
        if isinstance(response, dict) and isinstance(response.get("data"), str):
            try:
                decrypted_content = self.decrypt_data(response["data"])
                return {**response, "data": decrypted_content}
            except Exception as e:
                print(f"Failed to decrypt response field: {e}")
                raise Exception(f"Decryption of response data failed: {e}")

        return response

# Example usage:
# crypto = CryptoService()
# encrypted = crypto.encrypt_request_params({"id": 123})


def test_all():
    logger.info("Testing Extractor:")
    # test_youtube_extractor()
    # test_tiktok_extractor()
    test_douyin_extractor()
    # test_kuaishou_extractor()
    # test_drama_sansekai_extractor()
    # test_drama_box_extractor()
    # test_reelshort_extractor()
    # test_dramabite_extractor()
    # test_shortmovs_extractor()
    # test_rushtv_extractor()
    # test_stardusttv_extractor()
