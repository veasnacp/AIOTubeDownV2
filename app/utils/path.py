import os
import subprocess
import sys
import time
import urllib.parse

try:
    import winreg

    import win32com.client
except:
    pass

def split_filepath(filepath: str):
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


def focus_window(compare_path, select_file_path=None):
    window_found = False
    shell = win32com.client.Dispatch("Shell.Application")
    for window in shell.Windows():
        # Check if the window is an Explorer window and matches our path
        # Note: We use .lower() and normalization to ensure paths match
        try:
            window_path = os.path.abspath(
                window.LocationURL.replace("file:///", "").replace("/", "\\"))
            # LocationURL uses URL encoding (e.g., %20 for spaces)
            window_path = urllib.parse.unquote(window_path)

            if window_path.lower() == compare_path.lower():
                # We found the window! Now focus it and select the file
                window.Visible = True

                # Bring to front (Visual focus)
                shell_gui = win32com.client.Dispatch("WScript.Shell")
                shell_gui.AppActivate(window.LocationName)

                if select_file_path:
                    # Select the specific file inside the folder
                    folder_view = window.Document
                    folder_view.SelectItem(select_file_path, 1 | 4 | 8 | 16)
                    # Flags: 1=Select, 4=Focus, 8=Scroll into view, 16=Deselect others

                window_found = True
                break
        except Exception:
            continue

    return window_found


def reveal_in_explorer(file_path: str):
    file_path = os.path.abspath(file_path)
    folder_path = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)

    window_found = focus_window(folder_path, file_path)
    if not window_found:
        os.startfile(folder_path)
        for i in range(3):
            time.sleep(0.15)
            window_found = focus_window(folder_path, file_path)
            if window_found:
                break


def reveal_in_finder(file_path: str):
    # This script tells Finder to activate (come to front),
    # open the file's container, and select the file.
    script = f'''
    set theFile to POSIX file "{file_path}"
    tell application "Finder"
        activate
        reveal theFile
    end tell
    '''
    subprocess.Popen(['osascript', '-e', script])

    # subprocess.Popen(['open', '-R', str(path)])


def reveal_in_linux(file_path):
    # Most modern Linux file managers (Nautilus, Dolphin, Nemo)
    # support the 'ShowItems' DBus interface.
    uri = f"file://{file_path}"
    try:
        subprocess.Popen([
            'dbus-send', '--print-reply', '--dest=org.freedesktop.FileManager1',
            '/org/freedesktop/FileManager1', 'org.freedesktop.FileManager1.ShowItems',
            f'array:string:{uri}', 'string:""'
        ])
    except Exception:
        # Fallback: Just open the parent folder if DBus fails
        parent_folder = os.path.dirname(file_path)
        subprocess.Popen(['xdg-open', parent_folder])


def reveal_file(file_path: str):
    if sys.platform == "win32":
        reveal_in_explorer(file_path)
    elif sys.platform == "darwin":
        reveal_in_finder(file_path)
    else:
        reveal_in_linux(file_path)


def get_open_with_apps(file_path: str):
    """Returns a list of (app_name, app_path) for the given file's extension."""
    ext = os.path.splitext(file_path)[1].lower()
    apps = []

    try:
        # Path to the 'OpenWithList' for this extension
        reg_path = rf"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{ext}\OpenWithList"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
            i = 0
            while True:
                try:
                    # Values are usually named 'a', 'b', 'c'...
                    value_name, app_exe, _ = winreg.EnumValue(key, i)
                    if app_exe.endswith(".exe"):
                        apps.append(app_exe)
                    i += 1
                except OSError:
                    break
    except OSError:
        pass

    return list(set(apps))


def trigger_windows_open_with(file_path):
    """Launch the file with a specific app."""
    subprocess.Popen(
        f'rundll32.exe shell32.dll,OpenAs_RunDLL {file_path}', shell=True)


if __name__ == "__main__":
    path = r"C:\Users\USER\Downloads\AIOTubeDown\YouTube\danmartell\AI TOOLS TIER LIST (2026).mp4"
    exe_list = get_open_with_apps(path)
    print(exe_list)
    trigger_windows_open_with(path)
