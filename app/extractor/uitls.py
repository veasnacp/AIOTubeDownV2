import json
from typing import Generator


def search_dict(partial: dict, search_key: str) -> Generator[dict, None, None]:
        stack = [partial]
        while stack:
            current_item = stack.pop(0)
            if isinstance(current_item, dict):
                for key, value in current_item.items():
                    if key == search_key:
                        yield value
                    else:
                        stack.append(value)
            elif isinstance(current_item, list):
                for value in current_item:
                    stack.append(value)

def get_json_from_html(html: str, key: str, num_chars: int = 2, stop: str = '"') -> str:
    pos_begin = html.find(key) + len(key) + num_chars
    pos_end = html.find(stop, pos_begin)
    return html[pos_begin:pos_end]

def query_dict_encode(dict_obj: dict):
    return json.dumps(dict_obj, separators=(',', ':'))