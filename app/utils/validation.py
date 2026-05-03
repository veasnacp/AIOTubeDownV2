from urllib.parse import urlparse


def is_valid_url(link: str):
    is_starts_with_www = isinstance(link, str) and link.startswith('www.')
    if is_starts_with_www:
        link = 'https://' + link
    try:
        url = urlparse(link)
        host = url.netloc
        host_split = host.split('.')
        ext = host_split[-1] if host_split else ''
        if is_starts_with_www and len(host_split) < 3:
            ext = ''
        return bool(url) and len(host_split) > 1 and len(ext) > 1 and any(url.geturl().startswith(v) for v in ["http://", "https://"])
    except:
        return False


def n_formatter(num, digits=2):
    lookup = [
        {"value": 1, "symbol": ""},
        {"value": 1e3, "symbol": "k"},
        {"value": 1e6, "symbol": "M"},
        {"value": 1e9, "symbol": "G"},
        {"value": 1e12, "symbol": "T"},
        {"value": 1e15, "symbol": "P"},
        {"value": 1e18, "symbol": "E"}
    ]
    # regexp = r'\.0+$|(?<=\.[0-9]*[1-9])0+$'
    item = next((item for item in reversed(lookup)
                if num >= item["value"]), None)
    if item:
        return f"{(num / item['value']):.{digits}f}".rstrip('0').rstrip('.') + item["symbol"]
    return "0"


def format_number(number):
    """
    Formats a number with K, M, G, T, P, or E suffixes.

    Args:
        number: The number to format (int or float).

    Returns:
        A string representing the formatted number.
    """

    if not isinstance(number, (int, float)):
        return '0'

    suffixes = {
        10**3: "K",
        10**6: "M",
        10**9: "G",
        10**12: "T",
        10**15: "P",
        10**18: "E",
    }

    for value, suffix in sorted(suffixes.items(), reverse=True):
        if abs(number) >= value:  # Use abs() for negative numbers
            formatted_value = number / value
            if abs(formatted_value) < 10:
                # 2 decimal places if less than 10
                return f"{formatted_value:.2f}{suffix}"
            elif abs(formatted_value) < 100:
                # 1 decimal place if less than 100
                return f"{formatted_value:.1f}{suffix}"
            else:
                # Integer if 100 or more
                return f"{int(formatted_value)}{suffix}"

    return str(number)  # Return original number if smaller than 1000


def format_duration(seconds):
    """
    Formats a duration in seconds into HH:MM:SS or MM:SS format.

    Args:
        seconds: The duration in seconds (int).

    Returns:
        A string representing the formatted duration.  Returns "Invalid input" if input is not an integer or is negative.
    """

    if not isinstance(seconds, int) or seconds < 0:
        return ""

    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"  # HH:MM:SS
    else:
        return f"{minutes:02d}:{seconds:02d}"  # MM:SS


def format_duration_readable(seconds: int | float):
    """
    Formats a duration in seconds into a human-readable string of hours, minutes, and seconds.

    Args:
        seconds: The duration in seconds.

    Returns:
        A string representing the formatted duration.
    """

    if seconds < 0:
        return "..."

    if seconds == 0:
        return ""

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60

    parts = []

    if hours > 0:
        parts.append(f"{int(hours)} hour{'s' if int(hours) > 1 else ''}")

    if minutes > 0:
        parts.append(f"{int(minutes)} minute{'s' if int(minutes) > 1 else ''}")

    if hours <= 0 and remaining_seconds > 0:
        parts.append(
            f"{int(remaining_seconds)} second{'s' if int(remaining_seconds) > 1 else ''}")

    if not parts:
        return "0 seconds"

    return " ".join(parts)
