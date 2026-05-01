import re
from itertools import islice
from typing import Iterator, List, TypeVar

_T = TypeVar("_T")


def arr_chunk(arr_range: List[_T], arr_size: int) -> Iterator[List[_T]]:
    arr_range = iter(arr_range)  # type: ignore
    return iter(lambda: list(islice(arr_range, arr_size)), [])


def safe_filename(s: str, max_length: int = 255, more_safe: bool = False, more_safe_characters=None) -> str:
    """Sanitize a string making it safe to use as a filename.

    This function was based off the limitations outlined here:
    https://en.wikipedia.org/wiki/Filename.

    :param str s:
        A string to make safe for use as a file name.
    :param int max_length:
        The maximum filename character length.
    :rtype: str
    :returns:
        A sanitized string.
    """
    # Characters in range 0-31 (0x00-0x1F) are not allowed in ntfs filenames.
    ntfs_characters = [chr(i) for i in range(0, 31)]
    characters = [
        r'"',
        r"\*",
        r"\:",
        r"\/",
        r"\\",
        r"\<",
        r"\>",
        r"\?",
        r"\|",
        r"\\\\",
    ]
    safe_chars = [
        # r"\#",
        r"\$",
        r"\%",
        r"'",
        r"\,",
        r"\.",
        r'"',
        r"\;",
        r"\^",
        r"\~",
    ]
    if more_safe is True:
        more_safe_characters = more_safe_characters if isinstance(
            more_safe_characters, list) else []
        characters = [*characters, *safe_chars, *more_safe_characters]
    pattern = "|".join(ntfs_characters + characters)
    regex = re.compile(pattern, re.UNICODE)
    filename = regex.sub("", s)
    return filename[:max_length].rsplit(" ", 0)[0]
