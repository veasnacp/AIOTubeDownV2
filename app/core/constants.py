from typing import Optional, TypeAlias, Union
import re
from urllib.parse import urlparse


from ..extractor.douyin import DouyinExtractor

from ..extractor.facebook import FacebookExtractor
from ..extractor.kuaishou import KuaishouExtractor
from ..extractor.tiktok import TikTokExtractor
from ..extractor.youtube import YouTubeExtractor
# from ..extractor.instagram import InstagramExtractor


TYPE_EXTRACTOR: TypeAlias = Union[
    'YouTubeExtractor', 'TikTokExtractor',
    'FacebookExtractor',
    # 'InstagramExtractor',
    'KuaishouExtractor', 'DouyinExtractor'
]

BASE_DOMAIN = {
    "instagram": "instagram.com",
    "tiktok": "tiktok.com",
    "tiktok_redirect": "vt.tiktok.com",
    "youtube": "youtube.com",
    "youtube_short": "youtu.be",
    "facebook": "facebook.com",
    "kuaishou": "kuaishou.com",
    "kuaishou_redirect": "v.kuaishou.com",
    "douyin": "douyin.com",
    "douyin_redirect": "v.douyin.com"
}

BASE_EXTRACTORS = {
    # "instagram": InstagramExtractor,
    "tiktok": TikTokExtractor,
    "youtube": YouTubeExtractor,
    "facebook": FacebookExtractor,
    "kuaishou": KuaishouExtractor,
    "douyin": DouyinExtractor,
}


def extract_url_list(url_list: list[str]):
    # hostRedirectPattern = "vt.tiktok.com|v.douyin.com|v.kuaishou.com"

    other_list: list[str] = []
    generic_list: list[str] = []

    tiktok_video_list: list[str] = []
    tiktok_profile_list: list[str] = []
    youtube_video_list: list[str] = []
    youtube_profile_list: list[str] = []
    facebook_video_list: list[str] = []
    facebook_profile_list: list[str] = []
    douyin_video_list: list[str] = []
    douyin_profile_list: list[str] = []
    kuaishou_video_list: list[str] = []
    kuaishou_profile_list: list[str] = []
    instagram_video_list: list[str] = []
    instagram_profile_list: list[str] = []

    for link in url_list:
        _parsed_url = urlparse(link)
        _path = _parsed_url.path
        _query = _parsed_url.query
        _netloc = _parsed_url.netloc
        is_generic = "&download_with_info_dict=" in _query

        if is_generic:
            generic_list.append(link)
            continue

        if not any(value in _netloc for value in BASE_DOMAIN.values()):
            other_list.append(link)
            continue

        if BASE_DOMAIN["instagram"] in _netloc:
            if re.search(r"/(p|reel|reels)/", _path):
                instagram_video_list.append(link)
                continue

            instagram_profile_list.append(link)
            continue

        if BASE_DOMAIN["tiktok"] in _netloc or BASE_DOMAIN["tiktok_redirect"] in _netloc:
            if re.search(r"/video/", _path) or BASE_DOMAIN["tiktok_redirect"] in _netloc:
                tiktok_video_list.append(link)
                continue

            tiktok_profile_list.append(link)
            continue

        if BASE_DOMAIN["youtube"] in _netloc or BASE_DOMAIN["youtube_short"] in _netloc:
            if re.search(r"/watch|/shorts", _path) or BASE_DOMAIN["youtube_short"] in _netloc:
                youtube_video_list.append(link)
                continue

            youtube_profile_list.append(link)
            continue

        if BASE_DOMAIN["facebook"] in _netloc:
            if re.search(r"/videos/|/watch/\?v=|/watch\?v=|/reel/|\?story_fbid=|/posts/pfbid", link):
                facebook_video_list.append(link)
                continue

            facebook_profile_list.append(link)
            continue

        if BASE_DOMAIN["kuaishou"] in _netloc or BASE_DOMAIN["kuaishou_redirect"] in _netloc:
            if re.search(r"/short-video/", _path) or BASE_DOMAIN["kuaishou_redirect"] in _netloc:
                kuaishou_video_list.append(link)
                continue

            kuaishou_profile_list.append(link)
            continue

        if BASE_DOMAIN["douyin"] in _netloc or BASE_DOMAIN["douyin_redirect"] in _netloc:
            if re.search(r"/video/", _path) or BASE_DOMAIN["douyin_redirect"] in _netloc:
                douyin_video_list.append(link)
                continue

            douyin_profile_list.append(link)
            continue

    return {
        "tiktok_video_list": tiktok_video_list,
        "tiktok_profile_list": tiktok_profile_list,
        "youtube_video_list": youtube_video_list,
        "youtube_profile_list": youtube_profile_list,
        "facebook_video_list": facebook_video_list,
        "facebook_profile_list": facebook_profile_list,
        "kuaishou_video_list": kuaishou_video_list,
        "kuaishou_profile_list": kuaishou_profile_list,
        "douyin_video_list": douyin_video_list,
        "douyin_profile_list": douyin_profile_list,
        "instagram_video_list": instagram_video_list,
        "instagram_profile_list": instagram_profile_list,
        "other_list": other_list,
        "generic_list": generic_list
    }
