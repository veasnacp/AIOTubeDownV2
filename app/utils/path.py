import os
from pathlib import Path
from typing import Literal, Optional, TypeAlias, Union

# Type Aliases
EnvSortName: TypeAlias = Literal[
    "$AppData", "$Roaming", "$Roaming", "$LocalAppData", "$Temp", "$Home", "$User"
]
HomeSortName: TypeAlias = Literal[
    "Desktop", "Documents", "Downloads", "Music", "Pictures", "Videos"
]
PathLike: TypeAlias = Optional[Union[str, Path]]
ExpandBehavior: TypeAlias = Literal["~", "$", None]


def split_filepath(filepath: PathLike):
    """
    Splits a filepath into its root, basename, filename, and extension.

    Args:
        filepath (str): The filepath to split.

    Returns:
        tuple: A tuple containing (root, basename, filename, ext).
    """
    root = os.path.dirname(os.path.abspath(str(filepath)))
    basename = os.path.basename(str(filepath))
    filename, ext = os.path.splitext(basename)
    return root, basename, filename, ext


class PathHandler:
    """Handles file paths, environment variable and user directory expansion."""

    _ENV_VARS = {  # Dictionary of common environment variables
        "AppData": "APPDATA",  # Windows
        "Roaming": "APPDATA",  # Often used with AppData on Windows
        "LocalAppData": "LOCALAPPDATA",  # Windows
        "Temp": "TEMP",
        "Home": "HOME",  # Linux/macOS
        "User": "USERPROFILE"  # Windows
    }

    def __init__(self, path: Union[PathLike, EnvSortName] = None, expand: ExpandBehavior = None):
        self._original_path: PathLike = path or "~"
        self._expanded_path: Optional[Path] = None
        self._expand_behavior = expand
        env_var = self._ENV_VARS.get(str(self._original_path)[1:])
        if env_var:
            self._expand_behavior = "$"
        self._expand_path()

    def _expand_path(self):
        path_str = str(self._original_path)

        if self._expand_behavior == "~":
            path_str = os.path.expanduser(path_str)
        elif self._expand_behavior == "$":
            # Expand environment variables, handling our special cases
            other = ''
            if "/" in path_str or '\\' in path_str:
                path_part = path_str.replace('\\', '/').split('/', 1)
                path_str = path_part[0]
                other = '/' + path_part[1]
            env_var = self._ENV_VARS.get(path_str[1:])
            if env_var is not None:
                path_str = path_str.replace(
                    path_str, os.environ.get(env_var, ""))
            # else:
                # for short_name, env_var in self._ENV_VARS.items():
                #     path_str = path_str.replace(
                #         f"${short_name}", os.environ.get(env_var, ""))
            path_str = path_str + other
            path_str = os.path.expandvars(path_str)  # Handle other env vars
        elif self._expand_behavior is None:
            pass  # No expansion
        else:
            raise ValueError(
                f"Invalid expand behavior: {self._expand_behavior}")

        self._expanded_path = Path(path_str).resolve()  # Resolve to full path

    @property
    def path(self) -> Path:
        if self._expanded_path is None:
            raise ValueError("Path expansion failed.")
        return self._expanded_path

    @property
    def original_path(self) -> PathLike:
        return self._original_path

    def __str__(self) -> str:
        return str(self.path)

    def __repr__(self) -> str:
        return f"PathHandler(path='{self._original_path}', expand='{self._expand_behavior}')"

    def join(self, path: Union[PathLike, HomeSortName], *other_paths: PathLike) -> Path:
        return self.path.joinpath(path, *other_paths)


# # Example Usage:
# appdata_path = PathHandler("$AppData/MyApp", expand="$")
# print(f"AppData Path: {appdata_path}")  # Output: Full path to AppData/MyApp

# # Often the same as AppData
# roaming_path = PathHandler("$Roaming/MyApp", expand="$")
# print(f"Roaming Path: {roaming_path}")

# temp_path = PathHandler("$Temp", expand="$").join('myfile.txt')
# print(f"Temp Path: {temp_path}")

# local_path = PathHandler("$LocalAppData", expand="$").join('MyApp')
# print(f"Local AppData Path: {local_path}")

# home_path = PathHandler("~", expand="~")
# print(f"Home path: {home_path}")

# relative_path = home_path.join("documents", "report.pdf")
# print(f"Relative path (resolved): {relative_path}")

# home_path = PathHandler("$Home", expand="$")
# print(f"Home path $: {home_path}")

# Demonstrates Path.resolve()
# import sys
# executable = sys.executable
# unresolved_path = PathHandler("./AIOTubeDown.exe", expand=None).path.as_posix()
# print(f"Unresolved Path: {unresolved_path}", Path(executable).as_posix())

# resolved_path = PathHandler("./some/path", expand=None).path.resolve()
# print(f"Resolved Path: {resolved_path}")

# # Example of using a custom environment variable (you'd need to set this)
# custom_path = PathHandler("$MY_CUSTOM_DIR/data.txt", expand="$")
# print(f"Custom Path: {custom_path}")
