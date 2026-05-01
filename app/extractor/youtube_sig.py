import json
import re
from pathlib import Path
from types import FunctionType

from pytubefix import YouTube, extract
from yt_dlp.utils import format_bytes, mimetype2ext, parse_codecs

# import_section#__import_section__


def format_bytes_tbr(duration: int, tbr: int):
    return int(duration * tbr * (1024 / 8))

# https://github.com/wayne931121/Python_URL_Decode


def extract_video_formats(html: str, ytInitialPlayerResponse: dict, video_info: dict, js: FunctionType = None, visitor_data=None, streaming_data=None):

    matches = re.search(r'player\\?/([0-9a-fA-F]{8})\\?/', html)
    player_version = next(g for g in matches.groups()
                          if g is not None) if matches else None
    if not player_version:
        # /s/player/%s/player_ias.vflset/en_US/base.js
        player_path = re.search(
            r'jsUrl":"(?P<url>.+?base.js)"', html)['url']  # type: ignore
        player_version = player_path.split('s/player/')[1].split('/')[0]
    js_url = "https://www.youtube.com/s/player/%s/player_ias.vflset/en_US/base.js" % player_version

    # print("Download Source Code From %s" % js_url)

    url = video_info.get('original_url')

    both = []
    video_only = []
    audio_only = []

    ydl = YouTube(url)
    # ydl._vid_info = ytInitialPlayerResponse
    ydl._watch_html = html
    ydl._js_url = js_url
    _js = ydl._js
    if isinstance(js, FunctionType):
        _js = js(js_url)
        ydl._js = _js

    # if streaming_data:
    #     try:
    #         stream_manifest = extract.apply_descrambler(streaming_data)
    #         extract.apply_signature(
    #             stream_manifest, ytInitialPlayerResponse, _js, js_url)
    #         current_dir = Path(__file__).parent
    #         with open(current_dir.joinpath("mobile_stream_manifest.json"), "w", encoding="utf-8") as f:
    #             json.dump(stream_manifest, f, indent=2)
    #     except Exception as err:
    #         print("Error applying descrambler/signature:", err)

    if visitor_data:
        ydl._visitor_data = visitor_data

    fmt_streams = []
    # for info in ydl.fmt_streams:
    #     try:
    #         stream = info.__dict__
    #         if isinstance(stream,dict) and stream.get('_monostate') is not None:
    #             del stream['_monostate']
    #         fmt_streams.append(stream)
    #     except ValueError as err:
    #         print("error PyTube", err)

    try:
        for stream in ydl.fmt_streams:
            try:
                stream_dict = dict(stream.__dict__)
                if isinstance(stream_dict, dict) and stream_dict.get('_monostate') is not None:
                    del stream_dict['_monostate']
                # print(stream_dict)
                if stream_dict.get('_width'):
                    stream_dict['width'] = stream_dict["_width"]
                if stream_dict.get('_height'):
                    stream_dict['height'] = stream_dict["_height"]

                filesize_num = stream.filesize
                bitrate = stream.bitrate
                tbr = bitrate / \
                    1000 if isinstance(bitrate, (int, float)) else bitrate
                if stream.filesize <= 0:
                    if isinstance(bitrate, int) and bitrate > 0:
                        tbr = bitrate / 1000
                        filesize_num = format_bytes_tbr(
                            video_info.get("duration"), tbr)
                        filesize = format_bytes(filesize_num)
                    else:
                        tbr = bitrate
                        filesize_num = None
                        filesize = None
                else:
                    filesize = format_bytes(filesize_num)
                info = {
                    "tbr": tbr,
                    "fps": stream_dict.get("fps"),
                    "title": stream.title,
                    "ext": "unknown",
                    "filesize": filesize,
                    "filesize_num": filesize_num,
                    "url": stream.url
                }
                if stream_dict.get('width') is not None and stream_dict.get('height') is not None:
                    width = stream_dict['width']
                    height = stream_dict['height']
                    resolution = f"{width}x{height}"
                    info.update(**{
                        "width": width,
                        "height": height,
                        "resolution": resolution
                    })
                mime_mobj = re.match(
                    r'((?:[^/]+)/(?:[^;]+))(?:;\s*codecs="([^"]+)")?', stream_dict.get('mime_type') or '')
                if mime_mobj:
                    info['ext'] = mimetype2ext(mime_mobj.group(1))
                codecs = stream_dict.get('codecs')
                if isinstance(codecs, list) and len(codecs) > 0:
                    info.update(parse_codecs(codecs[0]))
                if isinstance(stream_dict, dict):
                    video_codec = stream_dict.get('video_codec')
                    audio_codec = stream_dict.get('audio_codec')
                    if video_codec and audio_codec:
                        both.append(info)
                    elif video_codec and not audio_codec:
                        video_only.append(info)
                    elif not video_codec and audio_codec:
                        audio_only.append(info)

                # fmt_streams.append(stream_dict)
            except ValueError as err:
                print("error format", err)
    except Exception as err:
        print("fmt_streams", err)

    formats = {
        "both": both,
        "video_only": video_only,
        "audio_only": audio_only,
        # "fmt_streams": fmt_streams,
    }

    return formats


# def extract_video_formats(html:str, ytInitialPlayerResponse:dict, video_info:dict, prt_full=0, list_all=False):

#     decrypt = Decrypt_2022_10_29_zh_TW()
#     html = html
#     # yt = re.search(b'var ytInitialPlayerResponse = (?P<ytInitialPlayerResponse>{.+("timestamp":){[^}]+}}+);', html)
#     js = re.search(r'jsUrl":"(?P<url>.+?base.js)"', html) # Example:"jsUrl":"/s/player/19fc75cf/player_ias.vflset/zh_TW/base.js"
#     # title = re.search(r'<meta name="title" content="(?P<title>.+?)">', html)

#     yt = ytInitialPlayerResponse
#     if not yt:
#         print("ERROR -1: not yt js title")
#         #print(content)
#         raise Exception(-1)
#     js = js["url"]
#     print("JS: ", js)

#     formats_adaptive = yt["streamingData"]["adaptiveFormats"] if yt["streamingData"]["adaptiveFormats"] else []
#     formats_download = yt["streamingData"]["formats"] if yt["streamingData"]["formats"] else []
#     datas = [*formats_adaptive, *formats_download]
#     flag = "signatureCipher" in datas[0] #是否加密
#     # videos = []
#     # audios = []
#     # i = 0

#     if list_all:
#         list_availbale(datas)
#         return {}

# # if flag:
#     # js = 'https://www.youtube.com'+str(js)
#     js = "https://www.youtube.com/s/player/%s/player_ias.vflset/en_US/base.js" % js.split('s/player/')[1].split('/')[0]
#     print("is flag", flag,"Download Source Code From %s"%js)
#     js = bytes.decode(request(js))
#     status = decrypt.decrypt(js, prt=prt_full)
#     if (type(status)==int) and (status<0):
#         # print("Error: code %d"%status)
#         raise Exception("Error: code %d"%status)

#     def get_video_formats(data_list):
#         videos = []
#         audios = []
#         i = 0
#         # print("Getting video formats: ", len(data_list))
#         while i<len(data_list):
#             media_url = ""
#             sigcipher = ""
#             data = data_list[i]
#             if i == 0:
#                 print("data == ",data)
#             if flag:
#                 a = [e.split("=") for e in data["signatureCipher"].split("&")]
#                 media_url = decodeURIComponent(a[2][1])
#                 sigcipher = a[0][1]
#                 if prt_full:
#                     print("\n\nSignature Cipher: "+sigcipher)
#             else:
#                 media_url = data["url"]

#             if sigcipher:
#                 sigcipher = decrypt.Decrypt_Signature_Cipher(sigcipher)
#                 media_url = media_url+"&alr=yes&sig="+sigcipher
#             if not 'contentLength' in data:
#                 if isinstance(data.get("bitrate"), int) and data.get("bitrate") > 0:
#                     tbr = data.get("bitrate") / 1000
#                     filesize_num = format_bytes_tbr(video_info.get("duration"), tbr)
#                     filesize = format_bytes(filesize_num)
#                     data['contentLength']=filesize_num
#                 else:
#                     tbr = data.get("bitrate")
#                     filesize_num = None
#                     filesize = None
#             else:
#                 tbr = data.get("bitrate")
#                 filesize_num = int(data['contentLength'])
#                 filesize = format_bytes(filesize_num)
#             i += 1

#             data["url"] = media_url
#             # print(data["mimeType"])
#             info = {
#                 "tbr": tbr,
#                 "fps": data.get("fps"),
#                 "ext": data["mimeType"].split("/")[1].split(";")[0].strip(),
#                 "filesize": filesize,
#                 "filesize_num": filesize_num,
#                 "url": media_url,
#                 "width": data.get("width"),
#                 "height": data.get("height"),
#             }
#             mime_mobj = re.match(
#                 r'((?:[^/]+)/(?:[^;]+))(?:;\s*codecs="([^"]+)")?', data.get('mimeType') or '')
#             if mime_mobj:
#                 info['ext'] = mimetype2ext(mime_mobj.group(1))
#                 info.update(parse_codecs(mime_mobj.group(2)))
#             if "video" in data["mimeType"]:
#                 videos.append(info)
#             if "audio" in data["mimeType"]:
#                 audios.append(info)

#         if len(videos) > 0 and len(audios) > 0:
#             return { "videos": videos, "audios": audios }
#         elif len(videos) > 0 and len(audios) <= 0:
#             return { "videos": videos }
#         elif len(audios) > 0 and len(videos) <= 0:
#             return { "audios": audios }
#         else:
#             return {}

#     formats = {}
#     if len(formats_download) > 0:
#         video_formats = get_video_formats(formats_download)
#         if isinstance(video_formats.get("videos"), list):
#             formats["both"] = video_formats["videos"]
#     if len(formats_adaptive) > 0:
#         video_only_formats = get_video_formats(formats_adaptive)
#         if isinstance(video_only_formats.get("videos"), list):
#             formats["video_only"] = video_only_formats["videos"]
#         if isinstance(video_only_formats.get("audios"), list):
#             formats["audio_only"] = video_only_formats["audios"]

#     return formats
