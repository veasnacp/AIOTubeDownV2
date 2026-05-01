
import asyncio
import json
import re
from math import ceil
from typing_extensions import Literal, TypeAlias, Union, Optional
from urllib.parse import quote

import requests

# from chompjs import parse_js_object
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
class webdriver:
  ...
def Options():
  pass
  
class By:
  ...

# , osA, safe_filename
from yt_dlp.extractor.common import traverse_obj

from .util_extract import (
    Pool,
    _execute_request,
    all_promise,
    arr_chunk,
    datetime_timestamp,
    default_chrome_options,
    generate_image,
    generate_url_query,
    _urlencode,
    get_content_from_html_selector,
    headers,
    localhost_image,
    query_dict_encode,
    res_async,
    use_cpu,
)
from .youtube_ import YouTubeSortBy as InstaSortBy

# from yt_dlp.extractor.instagram import InstagramIE
# from yt_dlp import YoutubeDL

InstaKeyVideoInfoList: TypeAlias = Literal["video_info_list","user_info","video_list"]

#__import_section__

class InstaBaseIE:
  _HOST_DOMAIN = "https://www.instagram.com"
  _LINK_USERNAME = "https://www.instagram.com/%s"
  _LINK_REEL = "https://www.instagram.com/reel/%s"
  
  _API_USER = "https://www.instagram.com/api/v1/users/web_profile_info/?username=%s"
  _HEADERS_USER = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "priority": "u=1, i",
    "sec-ch-prefers-color-scheme": "dark",
    # "sec-ch-ua": "\"Not)A;Brand\";v=\"99\", \"Google Chrome\";v=\"127\", \"Chromium\";v=\"127\"",
    # "sec-ch-ua-full-version-list": "\"Not)A;Brand\";v=\"99.0.0.0\", \"Google Chrome\";v=\"127.0.6533.99\", \"Chromium\";v=\"127.0.6533.99\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-model": "\"\"",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-ch-ua-platform-version": "\"10.0.0\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "x-asbd-id": "129477",
    "x-csrftoken": "", #Jsk7onHX77b35xAhSSdJUl
    "x-ig-app-id": "936619743392459",
    "x-ig-www-claim": "0",
    "x-requested-with": "XMLHttpRequest",
    "cookie": "", #csrftoken=Jsk7onHX77b35xAhSSdJUl
    "Referer": "https://www.instagram.com/techmankind/",
    "Referrer-Policy": "strict-origin-when-cross-origin"
  }
  
  _API_GRAPHQL = "https://www.instagram.com/graphql/query/"
  _API_GRAPHQL_SLN = "https://www.instagram.com/api/graphql"
  _API_HEADERS = {
    'X-IG-App-ID': '936619743392459',
    'X-ASBD-ID': '198387',
    'X-IG-WWW-Claim': '0',
    'Origin': 'https://www.instagram.com',
    'Accept': '*/*',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
  }
  # csrf_token = None #type: Union[str,None]
  
  _HEADERS_VIDEO_JSON = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/x-www-form-urlencoded",
    "priority": "u=1, i",
    "sec-ch-prefers-color-scheme": "dark",
    # "sec-ch-ua": "\"Not)A;Brand\";v=\"99\", \"Google Chrome\";v=\"127\", \"Chromium\";v=\"127\"",
    # "sec-ch-ua-full-version-list": "\"Not)A;Brand\";v=\"99.0.0.0\", \"Google Chrome\";v=\"127.0.6533.99\", \"Chromium\";v=\"127.0.6533.99\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-model": "\"\"",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-ch-ua-platform-version": "\"10.0.0\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "x-asbd-id": "129477",
    "x-bloks-version-id": "d48864a035b1835e7d6839f3f4f6eccef248b3d94fbc4ded47b31025a6d691c3",
    "x-csrftoken": "", #Jsk7onHX77b35xAhSSdJUl
    "x-fb-friendly-name": "PolarisPostActionLoadPostQueryQuery",
    "x-fb-lsd": "AVptQ0OsUJw",
    "x-ig-app-id": "936619743392459",
    "cookie": "", # csrftoken=Jsk7onHX77b35xAhSSdJUl
    "Referer": "https://www.instagram.com/reel/C39Fo4cxbwQ/",
    "Referrer-Policy": "strict-origin-when-cross-origin"
  }
  _HEADERS_VIDEO_HTML = {
    "dpr": "1",
    "sec-ch-prefers-color-scheme": "dark",
    # "sec-ch-ua": "\"Not)A;Brand\";v=\"99\", \"Google Chrome\";v=\"127\", \"Chromium\";v=\"127\"",
    # "sec-ch-ua-full-version-list": "\"Not)A;Brand\";v=\"99.0.0.0\", \"Google Chrome\";v=\"127.0.6533.99\", \"Chromium\";v=\"127.0.6533.99\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-model": "\"\"",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-ch-ua-platform-version": "\"10.0.0\"",
    "upgrade-insecure-requests": "1",
    "viewport-width": "674"
  }

  def get_cookie(self, name:str="csrftoken"):
    variables = { 'shortcode': '' }
    params = self.query_params(variables)
    r = requests.get(self._API_GRAPHQL, params=params)
    cookies = [cookie.value for cookie in r.cookies if name in cookie.name]
    # print(cookies)
    return cookies[0]

  def query_params(self, variables:dict, query_hash:str="9f8827793ef34641b2fb195d4d41151c"):
    params = {
      "query_hash": query_hash,
      'variables': json.dumps(variables, separators=(',', ':')),
    }
    return params

  def headers_csrf_token(self):
    csrf_token = self.get_cookie()
    return {
      **self._API_HEADERS,
      'X-CSRFToken': csrf_token or '',
      'X-Requested-With': 'XMLHttpRequest',
      'Referer': "https://www.instagram.com/",
    }

  def get_video_shortcode(self, url_shortcode:str):
    url = url_shortcode.strip()
    def _shortcode(val):
      return url.split(val)[1].split("?")[0].split("/")[0]
    if "/reels/" in url:
      shortcode = _shortcode("/reels/")
    elif "/reel/" in url:
      shortcode = _shortcode("/reel/")
    elif "/p/" in url:
      shortcode = _shortcode("/p/")
    elif "/tv/" in url:
      shortcode = _shortcode("/tv/")
    else:
      shortcode = url
    return shortcode

  def get_user_info(self, url_username:str):
    username = self.get_username(url_username)

    api_url = "https://www.instagram.com/api/v1/users/web_profile_info/?username=%s" % username
    # print(api_url)

    def fetch_user():
      res = _execute_request(api_url,headers=self._API_HEADERS)
      return bytes.decode(res.read())

    user_info = {}
    for i in range(4):
      data = fetch_user()
      if "</script>" in data and "</body>" in data:
        print("Error Data %s times" % str(i+1))
        pass
      elif not ("</script>" in data and "</body>" in data):
        user = json.loads(data)["data"]["user"]
        user_info = {
          "id": user["id"],
          "name": user["full_name"],
          "username": user["username"],
          "biography": user["biography"],
          "follower_count": user["edge_followed_by"]["count"],
          "total_posts": user["edge_owner_to_timeline_media"]["count"],
        }
        break

    return user_info

  def get_username(self, url_username:str):
    url = url_username.strip()
    if ".com/" in url:
      username = url.split('.com/')[1].split("?")[0].split("/")[0]
    else:
      username = url
    return username

  def get_user_id(self, url_username:str) -> str:
    return self.get_user_info(url_username)["id"]

  def js_fetch_promise_selenium(
    self, url:str,
    params:dict[str,str]=None,
    res_type:Literal["text","json"]="json"
  ):
    if params:
      for key, value in params.items():
        if isinstance(value, dict):
          params[key] = query_dict_encode(params[key])
      url = generate_url_query(url, params)
      # params = "&".join([f"{k}={v}" for k, v in params.items()])
      # url = f"{url}?{params}"
    # print(url)

    res_type = "response.json()" if res_type == "json" else "response.text()"
    return f"""
            return new Promise((resolve, reject) => {{
                fetch('{url}', {{ method: 'POST' }})
                    .then(response => {res_type})
                    .then(data => resolve(data))
                    .catch(error => reject(error.message));
            }});
    """

  def js_fetch_graphql_promise_all_selenium(
    self, headers_body_url_list:list[dict],
  ):
    # res_type = "response.json()" if res_type == "json" else "response.text()"
    return f"""
            return Promise.all(
              {headers_body_url_list}.map(({{headers,body}}) => {{
                return new Promise((resolve, reject) => {{
                  fetch("{self._API_GRAPHQL_SLN}", {{ method: 'POST', headers: headers, body: body }})
                      .then(response => response.json())
                      .then(data => resolve(data))
                      .catch(error => reject(error.message));
                }});
              }})
            )
    """

  def js_fetch_promise_all_selenium(
    self, url_list:str,
    headers:dict[str,str]=None
  ):
    headers = headers if isinstance(headers, dict) else {
      'Accept': '*/*',
      'Accept-Encoding': 'gzip, deflate, br, zstd',
      'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
      'Connection': 'keep-alive',
      'Content-Type': 'application/json',
    }

    # res_type = "response.json()" if res_type == "json" else "response.text()"
    return f"""
            return Promise.all(
              {url_list}.map(url => {{
                return new Promise((resolve, reject) => {{
                  fetch(url, {{ method: 'POST', headers: {headers} }})
                      .then(response => response.json())
                      .then(data => resolve(data))
                      .catch(error => reject(error.message));
                }});
              }})
            )
    """

  def chrome_options(self, user_agent:str=None, use_default_options=True):
    chrome_options = Options()
    user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
    chrome_options.add_argument('--user-agent=%s' % user_agent)
    if use_default_options is True:
      default_chrome_options(chrome_options)
    chrome_options.add_argument('--headless=new')

    return chrome_options
  
  def dict_to_url_quote(self, info_dict:dict):
    update_info_dict = {"info_dict": {**info_dict}}
    url_dl = info_dict["hd"] + ("&download_with_info_dict=%s" % quote(json.dumps(update_info_dict)))
    return { **update_info_dict, "url_dl": url_dl }

  def extract_node(self, info_dict:dict[str,any], only_url_dl=False):
    # info_dict = self.extract_user_videos_info(url_username, "Video")
    def get_value(key, default_val:any=""):
      return info_dict[key] if info_dict.get(key) is not None else default_val

    user:dict = get_value("owner",{})
    # print(user)
    user_id = user.get("id","")
    username = user.get("username", "")
    shortcode = get_value("shortcode")
    webpage_url = self._LINK_REEL % shortcode
    url_dl = get_value("video_url")

    release_timestamp = get_value("taken_at_timestamp",0)
    title_edges = get_value("edge_media_to_caption",{"edges":[]})["edges"]
    title = title_edges[0]["node"]["text"] if len(title_edges) > 0 else ""
    title = f"Video by {username} [{shortcode}]" if title.strip() == "" else title
    # title = title.replace("\n\n\n\n"," ").replace("\n\n\n"," ").replace("\n\n"," ").replace("\n"," ")

    width = traverse_obj(info_dict, ("dimensions", "width"), default=0)
    height = traverse_obj(info_dict, ("dimensions", "height"), default=0)
    resolution = f"{width}x{height}"
    
    dash_info = get_value("dash_info",None)
    if dash_info:
      dash_info = quote(query_dict_encode(dash_info))
    video_info = {
      "id": shortcode,
      "display_id": shortcode,
      "id_number": get_value("id"),
      "thumbnail": get_value("display_url"),
      # "thumbnail_base64": generate_image(get_value("display_url")),
      # "thumbnail_base64": localhost_image(get_value("display_url")),
      "sd": url_dl,
      "hd": url_dl,
      "title": title,
      "fulltitle": title,
      "description": title,
      "comment_count": traverse_obj(info_dict, ("edge_media_to_comment", "count")) or traverse_obj(info_dict, ("edge_media_to_parent_comment", "count")),
      "like_count": traverse_obj(info_dict, ("edge_media_preview_like", "count")),
      "view_count": get_value("video_view_count",None),
      "url": webpage_url,
      "webpage_url": webpage_url,
      "original_url": webpage_url,
      "webpage_url_domain": "instagram.com",
      "uploader": username,
      "uploader_id": user_id,
      "uploader_url": f"{self._HOST_DOMAIN}/{username}",
      "extractor": "instagram",
      "extractor_key": "Instagram",
      "width": width,
      "height": height,
      "resolution": resolution,
      "duration": get_value("video_duration",0),
      "timestamp": release_timestamp,
      "release_timestamp": release_timestamp,
      "upload_date": datetime_timestamp(release_timestamp).__str__(),
      "requested_download": [{
        "title": title,
        "width": width,
        "height": height,
        "resolution": resolution,
        "url": webpage_url,
        # "video": unescape(video_hd),
      }],
      "dash_info": dash_info,
      "subtitles": [],
      "audio_only": [],
      "video_only": [],
      "user_info": {
        "id": user_id,
        "name": user.get("full_name",""),
        "username": username,
        "is_verified": user.get("is_verified", False),
        "avatar": user.get("profile_pic_url",""),
        "profile_pic_url": user.get("profile_pic_url",""),
        # "avatar_base64": generate_image(user.get("profile_pic_url")) if user.get("profile_pic_url") else None,
        "edge_followed_by": user["edge_followed_by"].get("count",0) if user.get("edge_followed_by") is not None else 0,
      }
    }
    if only_url_dl is True:
      return self.dict_to_url_quote(video_info)
    return video_info

class InstagramRequest(InstaBaseIE):
  def __init__(self) -> None:
    super().__init__()
    self.is_stopped = False
    
  def stop_extraction(self):
    self.is_stopped = True
    
  def on_callback_progress(self, video_info: dict):
    pass

  def callback_progress(self, video_info: dict):
    self.on_callback_progress(video_info)
    
  async def extract_video_info_list_all(self, url_shortcode_list:list[str], only_url_dl=False, chunks:int=None):
    shortcode = self.get_video_shortcode(url_shortcode_list[0])
    link_reel = self._LINK_REEL % shortcode

    r = _execute_request(link_reel, headers=self._HEADERS_VIDEO_HTML)
    page_source = bytes.decode(r.read())

    def get_eqmc(__eqmc={}):
      lsd = "AVptQ0OsUJw"
      lsd = __eqmc.get("l", lsd)
      jazoest = __eqmc.get("u", "jazoest=2980").split("jazoest=")[1]
      return lsd, jazoest

    __eqmc = get_eqmc()
    lsd, jazoest = __eqmc
    try:
      content = get_content_from_html_selector(page_source, "script", ['id="__eqmc"', 'type="application/json"'])[0]
      __eqmc = json.loads(content)
      lsd, jazoest = get_eqmc(__eqmc)
    except:
      for content in page_source.split('type=\"application/json\"'):
        if "?__a=1&__user=0&__comet_req=7&jazoest" in content:
          __eqmc = json.loads(content.split(">")[1].split("<")[0])
          lsd, jazoest = get_eqmc(__eqmc)
          break
    print("==========================================")
    print(__eqmc, lsd, jazoest)
    print("==========================================")

    async def fetch(url_shortcode):
      await asyncio.sleep(0.0001)
      shortcode = self.get_video_shortcode(url_shortcode)
      params = {
        "av":"0",
        "__d":"www",
        "__user":"0",
        "__a":"1",
        "__req":"3",
        "__hs":"19685.HYP:instagram_web_pkg.2.1..0.0",
        "dpr":"1",
        "__ccg":"UNKNOWN",
        "__rev":"1010026767",
        "__comet_req":7,
        "lsd":lsd,
        "jazoest":jazoest,
        "fb_api_caller_class":"RelayModern",
        "fb_api_req_friendly_name":"PolarisPostActionLoadPostQueryQuery",
        "variables": query_dict_encode({
          "shortcode": shortcode,
          "fetch_comment_count": 40,
          "fetch_related_profile_media_count": 3,
          "parent_comment_count": 24,
          "child_comment_count": 3,
          "fetch_like_count": 10,
          "fetch_tagged_user_count": None,
          "fetch_preview_comment_count": 2,
          "has_threaded_comments": True,
          "hoisted_comment_id": None,
          "hoisted_reply_id": None
        }),
        "server_timestamps": "true",
        "doc_id":"10015901848480474"
      }

      payload = _urlencode(params)
      data = None
      try:
        headers = self._HEADERS_VIDEO_JSON
        headers['Referer'] = (self._LINK_REEL % shortcode) + "/"
        headers['x-fb-lsd'] = lsd
        if self.csrf_token:
          headers['x-csrftoken'] = self.csrf_token
          headers['cookie'] = "csrftoken=%s" % self.csrf_token
        r = _execute_request(self._API_GRAPHQL_SLN, method="POST", headers=headers, data=payload)
        __data = json.loads(bytes.decode(r.read())) #type: dict
        data = __data
      except:
        pass
      
      return data
      
    url_shortcode_list_of_list = list(arr_chunk(url_shortcode_list, int(chunks or 50)))
    video_info_list = []
    for url_list in url_shortcode_list_of_list:
      if self.is_stopped:
        break
      # tasks = [
      #   fetch(url) for url in url_list
      # ]
      tasks = []
      for url in url_list:
        if self.is_stopped:
          break
        task = asyncio.create_task(fetch(url))
        tasks.append(task)
        
      data_list = await asyncio.gather(*tasks, return_exceptions=True)

      for i, data in enumerate(data_list):
        if isinstance(data, dict) and isinstance(data.get("data"), dict) and isinstance(data.get("data",{}).get("xdt_shortcode_media"), dict):
          node = data["data"]["xdt_shortcode_media"]
          video_info = self.extract_node(node)
          self.callback_progress(video_info)
          if only_url_dl == True:
            video_info = self.dict_to_url_quote(video_info)
          
          video_info_list.append(video_info)
        # else:
        #   print("================================")
        #   print("error url", url_list[i])
        #   print("================================")

    return video_info_list

  def extract_video_info_list_all_run(self, url_shortcode_list:list[str], with_url_dl=False, chunks:int=None):
    return asyncio.run(self.extract_video_info_list_all(url_shortcode_list,with_url_dl,chunks))

class InstagramExtractor(InstagramRequest):
  def __init__(self, csrf_token=None) -> None:
    super().__init__()
    
    self.csrf_token = csrf_token
    self.hasMore = False
    self.cursor = None
    self.require_login = False
    if isinstance(csrf_token, str):
      if "csrftoken=" in csrf_token:
        self.csrf_token = csrf_token.split("csrftoken=")[1].split(";")[0]
      else:
        self.csrf_token = csrf_token.strip().split(";")[0]
    else:
      self.csrf_token = self.get_cookie()

  def on_callback_progress(self, video_info: dict):
    pass

  def callback_progress(self, video_info: dict):
    self.on_callback_progress(video_info)
    
  def extract_video_info(self, url_shortcode:str, only_url_dl=False):
    shortcode = self.get_video_shortcode(url_shortcode)
    csrf_token = self.get_cookie()
    variables = {
      'shortcode': shortcode, #'CxTFsgzroy8'
      'child_comment_count': 3,
      'fetch_comment_count': 40,
      'parent_comment_count': 24,
      'has_threaded_comments': True,
    }
    # {"shortcode":shortcode,"fetch_comment_count":40,"fetch_related_profile_media_count":3,"parent_comment_count":24,"child_comment_count":3,"fetch_like_count":10,"fetch_tagged_user_count":None,"fetch_preview_comment_count":2,"has_threaded_comments":True,"hoisted_comment_id":None,"hoisted_reply_id":None}
    params = self.query_params(variables)

    # print("Cookie", csrf_token)
    headers={
      **self._API_HEADERS,
      'X-CSRFToken': csrf_token or '',
      'X-Requested-With': 'XMLHttpRequest',
      'Referer': "https://www.instagram.com/",
    }

    api_url = generate_url_query("https://www.instagram.com/graphql/query/", params)
    # print(api_url)

    res = _execute_request(api_url,headers=headers)
    data:dict[str, any] = json.loads(bytes.decode(res.read()))["data"]
    video_info = self.extract_node(data.get("shortcode_media",{}), only_url_dl=only_url_dl)

    return video_info

  def get_api_url(self, url_shortcode:str):
    shortcode = self.get_video_shortcode(url_shortcode)
    variables = {
      'shortcode': shortcode, #'CxTFsgzroy8'
      'child_comment_count': 3,
      'fetch_comment_count': 40,
      'parent_comment_count': 24,
      'has_threaded_comments': True,
    }
    params = self.query_params(variables)

    # csrf_token = "1QdkOURng2sbcrXtcyFX528m3A8af76p"
    # print("[csrf_token]: ", csrf_token)

    api_url = generate_url_query("https://www.instagram.com/graphql/query/", params)
    return api_url

  async def extract_video_info_list(self, url_shortcode_list:list[str], only_url_dl=False):
    csrf_token = self.csrf_token
    # print("[csrf_token]: ", csrf_token)
    headers={
      **self._API_HEADERS,
      'X-CSRFToken': csrf_token or '1QdkOURng2sbcrXtcyFX528m3A8af76p',
      'X-Requested-With': 'XMLHttpRequest',
      'Referer': "https://www.instagram.com/",
    }
    api_url_list = [self.get_api_url(url) for url in url_shortcode_list]
    def progress_callback(is_stopped):
      if self.is_stopped:
        return True
    data_list = await res_async(api_url_list, "json", headers, progress_callback=progress_callback)
    # data_list = await all_promise(api_url_list, "json", headers)
    video_info_list = []
    api_url_list_retries = []
    for i, data in enumerate(data_list):
      if self.is_stopped:
        break
      try:
        if isinstance(data,dict) and isinstance(data.get("data"), dict):
          info_dict = self.extract_node(data["data"].get("shortcode_media",{}))
          self.callback_progress(info_dict)
          if only_url_dl == True:
            info_dict = self.dict_to_url_quote(info_dict)
          video_info_list.append(info_dict)
        else:
          print("================================================")
          print("No Data ... ", data)
          print("================================================")
          if isinstance(data,dict) and isinstance(data.get("_content"), str):
            content = data["_content"]
            if 'require_login' in content:
              self.require_login = True
              break

          api_url_list_retries.append(api_url_list[i])
      except Exception as e:
        print("Error", e)

    if len(api_url_list_retries) > 0:
      print("================================================")
      print("Retrying... ", len(api_url_list_retries))
      print("================================================")
      _data_list = await res_async(api_url_list_retries, "json", headers)
      for i, _data in enumerate(_data_list):
        try:
          if isinstance(_data,dict) and isinstance(_data.get("data"), dict):
            _info_dict = self.extract_node(_data["data"].get("shortcode_media",{}), only_url_dl=only_url_dl)
            video_info_list.append(_info_dict)
          else:
            if isinstance(data,dict) and isinstance(data.get("_content"), str):
              content = data["_content"]
              if 'require_login' in content:
                self.require_login = True
                break
        except Exception as e:
          print("Error", e)

    if self.require_login is True:
      return []

    return video_info_list

  def extract_video_info_list_run(self, url_shortcode_list:list[str], only_url_dl=False):
    return asyncio.run(self.extract_video_info_list(url_shortcode_list, only_url_dl))
  
  def extract_video_info_list_sln(self, url_shortcode_list:list[str], only_url_dl=False):
    if True:
      return []
    shortcode = self.get_video_shortcode(url_shortcode_list[0])
    link_reel = self._LINK_REEL % shortcode

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    browser = webdriver.Chrome(chrome_options)

    browser.get(link_reel)
    # csrftoken_cookie = browser.get_cookie('csrftoken')
    # csrf_token = None
    # if csrftoken_cookie:
    #   csrf_token = csrftoken_cookie.get('value')
    # print("csrf_token", csrf_token)
    page_source = browser.page_source

    def get_eqmc(__eqmc={}):
      lsd = "AVptQ0OsUJw"
      lsd = __eqmc.get("l", lsd)
      jazoest = __eqmc.get("u", "jazoest=2980").split("jazoest=")[1]
      return lsd, jazoest

    __eqmc = get_eqmc()
    lsd, jazoest = __eqmc
    try:
      content = get_content_from_html_selector(page_source, "script", ['id="__eqmc"', 'type="application/json"'])[0]
      __eqmc = json.loads(content)
      lsd, jazoest = get_eqmc(__eqmc)
    except:
      for content in page_source.split('type=\"application/json\"'):
        if "?__a=1&__user=0&__comet_req=7&jazoest" in content:
          __eqmc = json.loads(content.split(">")[1].split("<")[0])
          lsd, jazoest = get_eqmc(__eqmc)
          break
    print("==========================================")
    print(__eqmc, lsd, jazoest)
    print("==========================================")

    def requestInit(url_shortcode):
      shortcode = self.get_video_shortcode(url_shortcode)
      url = (self._LINK_REEL % shortcode) + "/"
      headers = self._HEADERS_VIDEO_JSON
      headers['Referer'] = url
      headers['x-fb-lsd'] = lsd
      # if csrf_token:
      #   headers['x-csrftoken'] = csrf_token
      #   headers['cookie'] = "csrftoken=%s" % csrf_token
      params = {
        "av":"0",
        "__d":"www",
        "__user":"0",
        "__a":"1",
        "__req":"3",
        "__hs":"19685.HYP:instagram_web_pkg.2.1..0.0",
        "dpr":"1",
        "__ccg":"UNKNOWN",
        "__rev":"1010026767",
        "__comet_req":7,
        "lsd":lsd,
        "jazoest":jazoest,
        "fb_api_caller_class":"RelayModern",
        "fb_api_req_friendly_name":"PolarisPostActionLoadPostQueryQuery",
        "variables": query_dict_encode({
          "shortcode": shortcode,
          "fetch_comment_count": 40,
          "fetch_related_profile_media_count": 3,
          "parent_comment_count": 24,
          "child_comment_count": 3,
          "fetch_like_count": 10,
          "fetch_tagged_user_count": None,
          "fetch_preview_comment_count": 2,
          "has_threaded_comments": True,
          "hoisted_comment_id": None,
          "hoisted_reply_id": None
        }),
        "server_timestamps": "true",
        "doc_id":"10015901848480474"
      }
      data = {
        "headers": headers,
        "body": _urlencode(params),
        "url": url
      }
      return data

    url_shortcode_list_of_list = list(arr_chunk(url_shortcode_list, 50))
    video_info_list = []
    for url_list in url_shortcode_list_of_list:
      requestInit_list = [
        requestInit(url) for url in url_list
      ]
      script = self.js_fetch_graphql_promise_all_selenium( requestInit_list )
      # script = self.js_fetch_promise_all_selenium( api_list )
      # print("script", script)
      data_list = browser.execute_script(script)
      save_path = "C:/Users/DELL/Desktop/Web Dev/Electron App/AIOTubeDown/electron/public/bin/video_info.txt"
      with open(save_path, "w", encoding='utf-8') as f:
        f.write(json.dumps(data_list, indent=2))
        # f.write(data)
      for i, data in enumerate(data_list):
        if isinstance(data, dict) and isinstance(data.get("data"), dict) and isinstance(data.get("data",{}).get("xdt_shortcode_media"), dict):
          node = data["data"]["xdt_shortcode_media"]
          video_info = self.extract_node(node, only_url_dl)
          video_info_list.append(video_info)
        # else:
        #   print("================================")
        #   print("error url", url_list[i])
        #   print("================================")

    browser.quit()
    return video_info_list

  def extract_video_info_list_sln_all_pool(self, url_shortcode_list:list[str], only_url_dl=False):
    total_url = len(url_shortcode_list)

    if total_url <= 30:
      video_info_list = self.extract_video_info_list_run(url_shortcode_list, only_url_dl)

      # print("================================")
      # print(len(video_info_list))
      # print("================================")
      if len(video_info_list) > 0:
        return video_info_list

    def get_info_for_url_90_or_more(url_shortcode_list):
      chunk_size = 30
      runtime = ceil(total_url / chunk_size)
      url_list_of_list = list(arr_chunk(url_shortcode_list, chunk_size))
      only_url_dl_list = [only_url_dl for url in url_list_of_list]

      cpu = use_cpu(runtime)
      with Pool(cpu) as p:
        video_info_list_of_list = p.starmap(self.extract_video_info_list_run, zip(*[url_list_of_list, only_url_dl_list]))
        p.close()
        p.join()
        video_info_list = sum(video_info_list_of_list, [])

      return video_info_list

    if total_url <= 90:
      video_info_list = get_info_for_url_90_or_more(url_shortcode_list)
    else:
      url_vid_user_id_list_of_list = list(arr_chunk(url_shortcode_list, 90))
      video_info_list_of_list = [
        get_info_for_url_90_or_more(url_list)
        for url_list in url_vid_user_id_list_of_list
      ]
      video_info_list = sum(video_info_list_of_list, [])

    # print("[video_info_list]: ", len(video_info_list))
    if len(video_info_list) > 0:
      return video_info_list

    def get_info_for_url_less_or_equal_400(url_shortcode_list):
      chunk_size = 100
      runtime = ceil(total_url / 100)
      url_list_of_list = list(arr_chunk(url_shortcode_list, chunk_size))
      only_url_dl_list = [only_url_dl for url in url_list_of_list]

      cpu = use_cpu(runtime)
      with Pool(cpu) as p:
        video_info_list_of_list = p.starmap(self.extract_video_info_list_sln_all, zip(*[url_list_of_list, only_url_dl_list]))
        p.close()
        p.join()
        video_info_list = sum(video_info_list_of_list, [])

      return video_info_list

    if total_url <= 100:
      video_info_list = self.extract_video_info_list_sln_all(url_shortcode_list, only_url_dl)
    elif total_url > 100 and total_url <= 400:
      video_info_list = get_info_for_url_less_or_equal_400(url_shortcode_list)
    else:
      url_vid_user_id_list_of_list = list(arr_chunk(url_shortcode_list, 400))
      video_info_list_of_list = [
        get_info_for_url_less_or_equal_400(url_list)
        for url_list in url_vid_user_id_list_of_list
      ]
      video_info_list = sum(video_info_list_of_list, [])

    return video_info_list

  ################################
  # Extract video info from USER #
  ################################

  def extract_user_info_list_sln(self, url_username_list):
    if True:
      return []
    chrome_options = self.chrome_options()
    browser = webdriver.Chrome(options=chrome_options)

    def get_user_info(url_username):
      username = self.get_username(url_username)
      url_username = self._LINK_USERNAME % username

      browser.get(url_username)
      content = browser.page_source
      if "\"user_id\":" in content:
        user_id = content.split("\"user_id\":")[1].split(",")[0]
        user_id = re.sub(r"[\D]+", "", user_id)
        full_name = str(content.split("\"title\":\"")[1].split("(")[0]).strip()
        profile_pic_url = str(content.split("\"profile_pic_url\":\"")[1].split("\",")[0]).strip()
        profile_pic_url = profile_pic_url.replace("\\/", "/") if "\\/" in profile_pic_url else profile_pic_url
        # avatar_base64 = generate_image(profile_pic_url)
      else:
        user_id = username
        full_name = username
        profile_pic_url = ""
        # avatar_base64 = None
      return {
        "id": user_id,
        "name": full_name,
        "username": username,
        "total_posts": 5000,
        "url": self._LINK_USERNAME % username,
        "avatar": profile_pic_url,
        "profile_pic_url": profile_pic_url,
        # "avatar_base64": avatar_base64,
      }

    user_info_list = [get_user_info(url_username) for url_username in url_username_list]
    browser.close()
    return user_info_list

  def extract_user_posts_info(
    self, url_username:str,
    __type:Literal["Image","Video","Sidecar"]=None,
    limit:int=None,
    sort_by:InstaSortBy.ChannelVideos="newest",
    user_info:dict=None,
    cursor_continue:str=None,
    use_per_next_cursor=False,
  ) -> dict[InstaKeyVideoInfoList,list]:
    global cursor, hasMore
    cursor = cursor_continue
    cursor_position = int(0)
    hasMore = False
    
    use_per_next_cursor = sort_by and sort_by == "newest" and use_per_next_cursor

    username = self.get_username(url_username)

    is_first = True
    count = 0
    limit_copy = limit
    video_list = []
    video_info_list:list[dict] = []

    headers = self._HEADERS_USER
    if self.csrf_token:
      headers['x-csrftoken'] = self.csrf_token
      headers['cookie'] = "csrftoken=%s" % self.csrf_token
    headers['Referer'] = (self._LINK_USERNAME % username) + "/"
    # print("_HEADERS_USER", self._HEADERS_USER)
    api_url = self._API_USER % username
    res = _execute_request(api_url,headers=headers)
    data_ = json.loads(bytes.decode(res.read()))["data"]
    user = data_.get("user")
    
    if isinstance(user, dict):
      try:
        profile_pic_url = user['profile_pic_url']
        user_info = {
          "id": user["id"],
          "name": user["full_name"],
          "username": user["username"],
          "biography": user["biography"],
          "follower_count": user["edge_followed_by"]["count"],
          "total_posts": user["edge_owner_to_timeline_media"]["count"],
          "url": self._LINK_USERNAME % username,
          "avatar": profile_pic_url,
          "profile_pic_url": profile_pic_url,
          "profile_pic_url_hd": user.get('profile_pic_url_hd'),
        }
      except:
        pass
    else:
      user_info = user_info or {}

    print(user_info.get("id"), user_info.get("name"), user_info.get("url"))
    user_id = user_info["id"]
    total_posts = user_info["total_posts"]
    
    if isinstance(cursor_continue,str) and cursor_continue != '':
      is_first = False
    while True:
      if self.is_stopped:
        break
      try:
        if not is_first:
          after = {"after": cursor} if cursor is not None else {}
          params = {
            "doc_id": "17991233890457762", # 7950326061742207
            "variables": query_dict_encode({
              "id": user_id,
              **after,
              "first": 12
            })
          }
          # "https://www.instagram.com/graphql/query/"
          api_url = generate_url_query(self._API_GRAPHQL, params)
          # print(api_url)
          res = _execute_request(api_url,headers=self._API_HEADERS)
          data_ = json.loads(bytes.decode(res.read()))["data"]
          
        is_first = False
        user_media_ = data_["user"]["edge_owner_to_timeline_media"]

        current_cursor = cursor
        hasMore = user_media_["page_info"]["has_next_page"]
        cursor = user_media_["page_info"]["end_cursor"]
        edges = user_media_["edges"]
        
        print(hasMore, cursor, len(edges))
        if len(edges) <= 0:
          break

        for edge in edges:
          if self.is_stopped:
            break
          
          video_info = edge["node"]
          shortcode = video_info["shortcode"]
          count += 1
          if __type is None:
            # video_list.append(self._LINK_REEL % shortcode)
            # video_info_list.append(video_info)
            break
          else:
            if video_info["__typename"] == "Graph%s" % __type:
              # path = r'C:\Users\DELL\Desktop\Python\GUI\CustomTkinter\QT\download.info.json'
              # with open(path, "w") as f:
              #   f.write(json.dumps(video_info, indent=2))
              info = self.extract_node(video_info, False)
              info['cursor'] = current_cursor
              info['next_cursor'] = '' if not hasMore else cursor
              info['cursor_position'] = cursor_position
              # print("User Info ", user_info, info["user_info"])
              info["user_info"].update(**user_info)
              info_dict = self.dict_to_url_quote(info)
              info_dict["view_count"] = info["view_count"]
              info_dict["timestamp"] = info["timestamp"]
              # video_list.append(info.get("url"))
              video_list.append(info_dict["url_dl"])
              video_info_list.append(info_dict)
              
              self.callback_progress(info)
            else:
              break
            
          if sort_by and sort_by != "newest":
            limit_copy = None
          if  not use_per_next_cursor and count == limit_copy:
            hasMore = False
            break
      except ValueError as e:
        print('Instagram Error', e)
        pass

      if use_per_next_cursor:
        break
      cursor_position += 1
      if hasMore is False or count == limit_copy:
        break

    if sort_by and sort_by != "newest":
      limit = limit if isinstance(limit, int) and limit != 0 else len(video_info_list)
      if sort_by == "popular":
        sort_key = "view_count"
        reverse = True
      else:
        sort_key = "timestamp"
        reverse = False
      video_info_list.sort(key=lambda x : int(x[sort_key]), reverse=reverse)
      video_info_list = video_info_list[0:limit]
      video_list = [
        # self._LINK_REEL % video_info["shortcode"]
        video_info["url_dl"]
        for video_info in video_info_list
      ]

      video_list = video_list[0:limit]

    # print(len(video_list), len(video_info_list))
    return {
      "video_info_list": video_info_list,
      "user_info": user_info,
      "video_list": video_list
    }

  def extract_user_videos_info(
    self, url_username:str,
    limit:int=None,
    sort_by:InstaSortBy.ChannelVideos="newest",
    user_info:dict=None,
    cursor_continue:str=None,
    use_per_next_cursor=False,
  ) -> dict[InstaKeyVideoInfoList, list]:
    return self.extract_user_posts_info(url_username, "Video", limit, sort_by, user_info, cursor_continue,use_per_next_cursor)

  def extract_videos_from_multiple_user(
    self,
    url_username_list:list[str],
    limit: Optional[int] = None,
    sort_by: InstaSortBy.ChannelVideos = "newest",
    cursor_continue:str=None,
    use_per_next_cursor=False,
    use_info_list_direct: Union[list[dict],bool] = False,
    with_url_dl=False, 
    only_url_dl=False
  ) -> list[str|dict]:
    async def extract_videos_from_multiple_user():
      async def extract_videos_from_user(user_url, user_info=None):
        await asyncio.sleep(0.0001)
        info = self.extract_user_videos_info(user_url, limit, sort_by, user_info, cursor_continue,use_per_next_cursor)
        video_list = info["video_list"] if only_url_dl else info['video_info_list']
        await asyncio.sleep(0.0001)
        return video_list

      if isinstance(use_info_list_direct, list) and len(use_info_list_direct) > 0:
        user_info_list = use_info_list_direct
      if isinstance(use_info_list_direct, bool) and use_info_list_direct is True:
        user_info_list = self.extract_user_info_list_sln(url_username_list)
        tasks = [extract_videos_from_user(user_info.get("url"), user_info) for user_info in user_info_list]
      else:
        tasks = [extract_videos_from_user(url, None) for url in url_username_list]

      get_tasks = await asyncio.gather(*tasks, return_exceptions=True)
      video_list_of_list = [video_list for video_list in get_tasks if isinstance(video_list, list)]
      return video_list_of_list

    return sum(asyncio.run(extract_videos_from_multiple_user()), [])

