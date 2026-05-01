import math
import re

import dill
from PySide6.QtGui import QColor


def oklch_to_hex(oklch_str):
    """Converts OKLCH string to Hex. Handles transparency if present."""
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", oklch_str)
    if not nums:
        return "#000000"

    # Extract L, C, H. Ignore Alpha for standard Hex, or use for RGBA.
    L, C, H = map(float, nums[:3])

    # Conversion logic
    a_ = C * math.cos(math.radians(H))
    b_ = C * math.sin(math.radians(H))

    l_ = L + 0.3963377774 * a_ + 0.2158037573 * b_
    m_ = L - 0.1055613458 * a_ - 0.0638541728 * b_
    s_ = L - 0.0894841775 * a_ - 1.2914855480 * b_

    l, m, s = l_**3, m_**3, s_**3

    r = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    b = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

    def clamp(x): return max(0, min(255, int(x * 255)))
    return f"#{clamp(r):02x}{clamp(g):02x}{clamp(b):02x}"


def rgb_to_hex(rgb_str: str) -> str:
    """
    Converts 'rgb(255, 255, 255)' or 'rgba(255, 255, 255, 0.5)' to Hex.
    Note: Standard QSS hex (#RRGGBB) doesn't support alpha,
    so we focus on the RGB channels.
    """
    if rgb_str.startswith("#"):
        return rgb_str  # Already in hex format

    # Extract all numbers (integers or decimals)
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", rgb_str)
    if len(nums) < 3:
        return "#000000"

    # Convert first 3 values to integers and clamp them 0-255
    r, g, b = [max(0, min(255, int(float(n)))) for n in nums[:3]]

    return f"#{r:02x}{g:02x}{b:02x}"


def alpha(self, color_val: str, opacity: float = None) -> str:
    """
    Returns a color with modified opacity.
    Usage: theme.alpha(theme.primary, 0.2) -> 'rgba(..., 0.2)'
    """
    q_color = QColor(color_val)
    if not q_color.isValid():
        return color_val

    return f"rgba({q_color.red()}, {q_color.green()}, {q_color.blue()}, {opacity if opacity is not None else q_color.alphaF()})"


def generate_theme_file(css_path, output_path="theme.py"):
    with open(css_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract Blocks
    blocks = re.findall(r'(\:root|\.dark)\s*\{(.*?)\}', content, re.DOTALL)

    parsed_themes = {}
    for selector, body in blocks:
        mode = "light" if ":root" in selector else "dark"
        # Extract all variables
        vars_dict = dict(re.findall(r'(--[\w-]+):\s*(.*?);', body))
        # print(f"--- {mode} ---")
        # print(vars_dict)
        parsed_themes[mode] = vars_dict

    # Template for theme.py
    file_content = [
        "from dataclasses import dataclass",
        "",
        "from PySide6.QtGui import QColor",
        "",
        "@dataclass",
        "class ShadcnTheme:",
        "    name: str",
        *[
            f"    {k.replace('--', '').replace('-', '_')}: str"
            for k, v in parsed_themes["light"].items()
            if k.startswith('--') and ('#' in v or k in ['--radius'])
        ],
        # "    background: str",
        # "    foreground: str",
        # "    card: str",
        # "    card_foreground: str",
        # "    popover: str",
        # "    popover_foreground: str",
        # "    primary: str",
        # "    primary_foreground: str",
        # "    secondary: str",
        # "    secondary_foreground: str",
        # "    muted: str",
        # "    muted_foreground: str",
        # "    accent: str",
        # "    accent_foreground: str",
        # "    destructive: str",
        # "    border: str",
        # "    input: str",
        # "    ring: str",
        # "    radius: str",
        "",
        f"    {'\n    '.join(dill.source.getsource(alpha).split('\n'))}",
    ]

    for mode in ["light", "dark"]:
        m = parsed_themes.get(mode, {})
        var_name = "LightMode" if mode == "light" else "DarkMode"

        file_content.append(f"{var_name} = ShadcnTheme(")
        file_content.append(f"    name=\"{mode}\",")

        # Mapping key variables
        # keys = [
        #     ("background", "--background"), ("foreground", "--foreground"),
        #     ("card", "--card"), ("card_foreground", "--card-foreground"),
        #     ("popover", "--popover"), ("popover_foreground", "--popover-foreground"),
        #     ("primary", "--primary"), ("primary_foreground", "--primary-foreground"),
        #     ("secondary", "--secondary"), ("secondary_foreground",
        #                                    "--secondary-foreground"),
        #     ("muted", "--muted"), ("muted_foreground", "--muted-foreground"),
        #     ("accent", "--accent"), ("accent_foreground", "--accent-foreground"),
        #     ("destructive", "--destructive"), ("border", "--border"),
        #     ("input", "--input"), ("ring", "--ring")
        # ]

        # for attr, css_var in keys:
        #     hex_val = rgb_to_hex(m.get(css_var, "#000000"))
        #     # hex_val = oklch_to_hex(m.get(css_var, "oklch(0 0 0)"))
        #     file_content.append(f"    {attr}=\"{hex_val}\",")

        for key, val in m.items():
            css_var = key
            attr = key.replace('--', '').replace('-', '_')
            if '#' in val:
                hex_val = rgb_to_hex(val)
                file_content.append(f"    {attr}=\"{hex_val}\",")

        # Radius (Special case: converting 0rem or px to string)
        radius = m.get("--radius", "0px")
        if "rem" in radius or "px" in radius:
            if "rem" in radius:
                radius_value = float(radius.replace("rem", "").strip()) * 16
            else:
                radius_value = float(radius.replace("px", "").strip())
            # if decimal .0, convert to int for cleaner output
            if radius_value.is_integer():
                radius_value = int(radius_value)
            radius = f"{radius_value}px"

        file_content.append(f"    radius=\"{radius}\"")
        file_content.append(")")
        file_content.append("")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(file_content))
    print(f"Successfully generated {output_path}")


# Run the generator
if __name__ == "__main__":
    generate_theme_file("theme_variable.css")
