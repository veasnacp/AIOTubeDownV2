import json
import os
import subprocess
import time
from typing import Callable, List, Literal, Optional

from loguru import logger

from ..utils.path import split_filepath
from ._worker import Callback, DefaultWorker


def silent_cli():
    startup_info = None
    if os.name == 'nt':  # Windows platform
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup_info.wShowWindow = subprocess.STARTF_USESHOWWINDOW
    return startup_info


creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0


def extractMetadata(filePath: str, ffprobe: str = None):
    try:
        # Use ffprobe to get metadata in JSON format
        ffprobe_cmd = [
            ffprobe or "ffprobe",
            "-v", "error",
            "-show_format",
            "-show_streams",
            "-print_format", "json",
            filePath,
        ]
        silent_cli()
        process = subprocess.Popen(
            ffprobe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creationflags)
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            return

        metadata: dict = json.loads(stdout.decode())
        return metadata

    except FileNotFoundError:
        return "ffprobe not found. Make sure FFmpeg is installed and in your PATH."
    except json.JSONDecodeError:
        return "Error decoding metadata. Invalid JSON."
    except Exception as e:
        return f"An error occurred: {e}"


def args_bitrate(video_bitrate: int, quality: Literal["better", "best"] | None = None):
    if quality == "better":
        divide_by = 2
    elif quality == "best":
        divide_by = 4
    else:
        divide_by = 1
    return [
        '-b:v', str(video_bitrate*divide_by),
        '-bufsize', str(video_bitrate*3*divide_by),
        '-maxrate', str(video_bitrate*3*divide_by)
    ]


class FFmpegIO:
    def __init__(self):
        pass

    def args(
        self,
        video_file: str,
        output_file: str,
        add_music: str | None = None,
        music_loop: bool | None = False,
        trim: list[Optional[str | int]] | None = None,
        resolution: str | None = None,
        speed: str | None = None,
        flip: str | None = None,
        frame_rate: str | None = None,
        quality: str | None = None,
        video_bitrate: int | str | None = None,
        before_agrs: list | None = None,
        custom_args: list | None = None,
        threads: str | None = None,
        mute: bool | None = False,
        gpu: bool | None = False,
    ):
        gpu = isinstance(gpu, bool) and gpu
        arg_trim = ["-ss", str(trim[0]), "-to", str(trim[1])
                    ] if isinstance(trim, list) and len(trim) == 2 else []

        preset = ['-preset', 'p2', '-tune',
                  'hq'] if gpu else ['-preset', 'superfast']
        if resolution or speed or flip:
            scale_opt = "scale_cuda" if gpu else "scale"
            scale = f"{scale_opt}={resolution}," if isinstance(
                resolution, str) else ""
            # :force_original_aspect_ratio=decrease,pad=640:640:-1:-1

            is_speed = isinstance(speed, str) and speed not in ("1", 1)
            is_flip = isinstance(flip, str) and flip in ("x", "y") and not gpu

            if is_flip:
                flip = 'hflip,' if flip == 'x' else 'vflip,'
            else:
                flip = ''

            if is_speed:
                # if gpu:
                #   preset = ['-preset','p2','-tune','hq']
                if isinstance(mute, bool) and mute:
                    arg_speed = f"setpts=1/{speed}*PTS"
                else:
                    # arg_speed = f"setpts=PTS/{speed};[0:a]atempo={speed}"
                    arg_speed = f"setpts=1/{speed}*PTS;[0:a]atempo={speed}"
                    # 'setpts=1/<x>*PTS[v];[0:a]atempo=<x>[a]'
            else:
                arg_speed = ''

            fc_val = f"[0:v]{flip}{scale}{arg_speed}"
            fc_val = fc_val[:-1] if fc_val.endswith(',') else fc_val
            filter_complex = ["-filter_complex",
                              fc_val] if fc_val != "[0:v]" else []
        else:
            filter_complex = []

        if (mute or trim) and not resolution and not speed and not frame_rate and not flip:
            vcodec = 'copy'
        if speed in ("1", 1) and not resolution and not frame_rate and not flip:
            vcodec = 'copy'
        elif gpu:
            vcodec = "h264_nvenc"
        else:
            vcodec = 'libx264'

        arg_bitrate = args_bitrate(
            video_bitrate, quality) if video_bitrate and vcodec != 'copy' else []

        arg_add_music = [
            *(["-stream_loop", "-1"]
              if music_loop is True and isinstance(add_music, str) else []),
            "-i", add_music,
            "-map", "0:0", "-map", "1:0",
            "-c:v", "copy", "-c:a", "libmp3lame",
            "-q:a", "1", "-shortest"
        ] if isinstance(add_music, str) else []
        arg_threads = []
        if isinstance(threads, str):
            arg_threads = ["-threads", threads]

        is_custom_args = isinstance(custom_args, list)
        args = [
            *("-hwaccel cuda -hwaccel_output_format cuda".split(' ') if gpu else []),
            *(before_agrs if isinstance(before_agrs, list) else []),
            *arg_trim,
            "-i", video_file,
            *arg_add_music,
            *filter_complex,
            *(["-c:v", vcodec] if not is_custom_args else []),
            *(arg_bitrate if not is_custom_args else []),
            *(preset if not is_custom_args else []),
            # *preset,
            *arg_threads,
            *(custom_args if is_custom_args else []),
            *(arg_bitrate if is_custom_args else []),
            *(["-an"] if isinstance(mute, bool) and mute else []),
            *(["-r", frame_rate] if isinstance(frame_rate, str) else []),
            output_file, '-y'
        ]

        return args

    def args_add_new_audio(
        self,
        video_file: str,
        audio_file: str,
        output_file: str,
        music_loop: bool | None = False,
        threads: str | None = None,
    ):
        arg_threads = []
        if isinstance(threads, str):
            arg_threads = ["-threads", threads]

        args = [
            # *("-hwaccel cuda -hwaccel_output_format cuda".split(' ') if gpu else []),
            "-i", video_file,
            *(["-stream_loop", '-1'] if isinstance(music_loop, bool)
              and music_loop else []),
            "-i", audio_file,
            *("-map 0:v -map 1:a -c:v copy -c:a libmp3lame -q:a 1 -shortest".split(' ')),
            *arg_threads,
            output_file, '-y'
        ]

        return args


class VideoConverter(Callback):
    def __init__(self, ffmpeg: Optional[str] = None):
        self.output_path = ''
        self.command: List[str] = []

        self.audio_quality: Optional[str | int] = '128'
        self.duration: Optional[int | float] = None
        self.ffmpeg = ffmpeg or 'ffmpeg'

        self.info = {}
        self.percentage = 0
        self.cancel = False

        self.logger = logger.bind(name=self.__class__.__name__)

    def get_video_duration(self, video_path, default=0.0):
        try:
            startupinfo = silent_cli()
            duration_command = ['ffprobe', '-v', 'error', '-show_entries',
                                'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path]
            duration_process = subprocess.Popen(
                duration_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creationflags, startupinfo=startupinfo)
            duration_str, _ = duration_process.communicate()
            return float(duration_str.decode('utf-8').strip())
        except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as e:
            self.logger.error(f"Error getting duration: {e}")
            return default

    def get_duration_from_many_videos(self, video_paths: list[str], default=0.0):
        """
        Calculates the total video duration using moviepy.
        """
        total_duration = 0.0
        for video_path in video_paths:
            if not os.path.exists(video_path):
                self.logger.error(f"File not found: {video_path}")
                return default

            total_duration += self.get_video_duration(video_path)

        return total_duration

    def get_duration_from_many_videos_(self, file_video_list: str, default=0.0):
        video_duration_cmd = [
            self.ffmpeg,
            "-f", "concat",
            "-safe", "0",
            "-i", file_video_list,
            "-f", "ffmetadata",
            "-",
        ]
        startupinfo = silent_cli()
        video_duration_process = subprocess.Popen(
            video_duration_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creationflags, startupinfo=startupinfo)
        _, stderr = video_duration_process.communicate()
        duration_line = next(
            (line for line in stderr.decode().splitlines() if "Duration:" in line), None)
        if duration_line:
            duration_str = duration_line.split("Duration: ")[1].split(",")[0]
            hours, minutes, seconds = map(float, duration_str.split(":"))
            total_seconds = hours * 3600 + minutes * 60 + seconds
        else:
            # raise ValueError("Could not determine video duration.")
            total_seconds = default

        return total_seconds

    def on_stop_covert(self):
        pass

    def complete_callback(self, output_path: str = None, percentage=100):
        self.percentage = percentage
        output_path = output_path or self.output_path
        self.callbackProgress({
            'progress': self.percentage,
            'filename': output_path,
            'data': self.info,
            'status': 'finished',
        })

    def error_callback(self, e, options: dict = {}):
        self.callbackProgress({
            'data': self.info,
            'status': 'error',
            'error': str(e),
            **options,
        })

    def remove_file_when_finished(self, filepath, remove_original_file=True):
        try:
            if remove_original_file and self.percentage >= 100:
                if not filepath.strip().startswith('http') and os.path.exists(filepath):
                    os.remove(filepath)
        except:
            pass

    def args_convert_to_audio(
        self,
        video_url_or_path: str,
        output_filepath: str,
        audio_quality: Optional[str | int] = '128',
    ):
        args = [
            self.ffmpeg,
            '-y',
            # '-hide_banner',
            # '-loglevel',
            # 'repeat+info',
            # '-progress', 'pipe:3',
            '-i', video_url_or_path,
            '-vn',
            '-acodec', 'libmp3lame',
            '-b:a', f"{audio_quality}k",
            '-movflags', '+faststart',
            f"file:{output_filepath}"
        ]
        self.output_path = output_filepath
        self.command = args
        return args

    def convert_to_audio(
        self,
        video_url_or_path: str,
        output_filepath: str,
        audio_quality: Optional[str | int] = '128',
        remove_original_file=True
    ):
        self.args_convert_to_audio(
            video_url_or_path, output_filepath, audio_quality)
        self.run()
        self.remove_file_when_finished(video_url_or_path, remove_original_file)

    def args_merge_video_audio(
        self,
        video_path: str,
        audio_url_or_path: str,
        output_filepath: str,
    ):
        args = [
            self.ffmpeg,
            "-y", "-loglevel", "repeat+info",
            "-i", video_path,
            "-i", audio_url_or_path,
            "-c", "copy", "-map", "0:v:0", "-map", "1:a:0",
            "-movflags", "+faststart",
            output_filepath
        ]
        self.output_path = output_filepath
        self.command = args
        return args

    def merge_video_audio(
        self,
        video_path: str,
        audio_url_or_path: str,
        output_filepath: str,
        remove_original_file=True
    ):
        self.args_merge_video_audio(
            video_path, audio_url_or_path, output_filepath)
        self.run()
        output_filepath_basename = os.path.basename(output_filepath)
        for file in [video_path, audio_url_or_path]:
            if os.path.basename(file) != output_filepath_basename:
                self.remove_file_when_finished(file, remove_original_file)

    def merge_videos_with_looped_audio(self, video_paths: list[str], audio_path: str, output_path: str, total_seconds=0):
        """
        Merges multiple videos with a single looped audio track using ffmpeg.

        Args:
            video_paths: A list of file paths to the video files to merge.
            audio_path: The file path to the audio file.
            output_path: The file path to save the merged video.
        """

        total_seconds = total_seconds if bool(
            total_seconds) else self.get_duration_from_many_videos(video_paths)

        start = time.time()
        # Construct the ffmpeg command
        root, basename, filename, ext = split_filepath(video_paths[0])
        temp_video_path = os.path.join(root, f"temp_{start}.mp4")
        temp_video_path_text = os.path.join(root, f"temp_{start}.txt")

        # 1. Create a text file with input video paths
        with open(temp_video_path_text, "w") as f:
            for video_path in video_paths:
                f.write(f"file '{os.path.abspath(video_path)}'\n")

        # 2. Merge videos using concat demuxer and -c copy
        ffmpeg_merge_cmd = [
            "-f", "concat",
            "-safe", "0",
            "-i", temp_video_path_text,
            "-c", "copy",
            temp_video_path,
            "-y",
        ]
        self.duration = total_seconds
        self.output_path = output_path
        self.command = [self.ffmpeg, *ffmpeg_merge_cmd]

        self.first_success = False

        def on_first_success():
            self.first_success = True
        self.run_config(on_first_success)

        if os.path.exists(temp_video_path_text):
            os.remove(temp_video_path_text)

        if not self.first_success:
            if os.path.exists(temp_video_path):
                os.rename(temp_video_path, output_path)
            return
        # 2. Replace audio in the temporary file
        io = FFmpegIO()
        ffmpeg_replace_audio_cmd = io.args_add_new_audio(
            temp_video_path, audio_path, output_path, music_loop=True)

        self.command = [self.ffmpeg, *ffmpeg_replace_audio_cmd]

        def on_success():
            self.complete_callback()
            if os.path.exists(output_path):
                if os.path.exists(temp_video_path):
                    os.remove(temp_video_path)
            elif os.path.exists(temp_video_path):
                os.rename(temp_video_path, output_path)

        self.run_config(on_success, True)

    def run_config(self, on_success: Callable = lambda: None, use_on_progressing=True):
        try:
            command = self.command
            startupinfo = silent_cli()
            process = subprocess.Popen(
                command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creationflags, startupinfo=startupinfo)

            while True:
                line = process.stderr.readline().decode().strip()
                if not line:
                    break

                if self.cancel:
                    raise Exception("Convert stopped")

                # Parse progress (this is highly dependent on ffmpeg's output)
                if self.duration:
                    if "time=" in line:
                        time_str = line.split("time=")[1].split(" ")[0]
                        try:
                            h, m, s = map(float, time_str.split(':'))
                            total_seconds = h * 3600 + m * 60 + s
                            # Use pre-calculated duration
                            percentage = int(
                                (total_seconds / self.duration) * 100) if self.duration > 0 else 0
                            if percentage >= self.percentage:
                                self.percentage = 99 if percentage >= 99 else percentage

                            if use_on_progressing:
                                self.callbackProgress({
                                    'progress': self.percentage,
                                    'filename': self.output_path,
                                    'data': self.info,
                                    'status': 'progress',
                                })
                        except ValueError as e:
                            self.logger.error(f"Error Processing: {e}")
                        except Exception as e:
                            self.logger.error(f"Error getting duration: {e}")

            process.wait()  # Ensure process finishes

            if process.returncode == 0:
                on_success()
            else:
                error_message = process.stderr.read().decode('utf-8')
                self.error_callback(error_message, {
                    'ffmpeg-error': error_message,
                })

        except Exception as e:
            self.error_callback(e)

    def run(self):
        self.run_config(self.complete_callback)


class VideoConverterQRunnable(VideoConverter, DefaultWorker):
    def __init__(self, index: int = None):
        VideoConverter.__init__(self)
        DefaultWorker.__init__(self, index)
        self.on_stop_worker = self.on_stop_covert

        self.video_input = ''
        self.output_filepath = ''
        self.audio_input = ''

        self.video_input_list: List[str] = []

        self.type: Literal['Covert', 'Cut', 'Merge', 'Merges'] = ''

        _ffmpeg = 'C:/Users/DELL/Desktop/Inno Setup/app/ffmpeg/ffmpeg.exe'
        # _ffmpeg = 'C:/Program Files (x86)/Digiarty/VideoProc Vlogger/ffmpeg.exe'
        self.ffmpeg = _ffmpeg

    def set_covert(self, video_input, output_filepath, audio_quality: Optional[str | int] = None):
        self.video_input = video_input
        self.output_filepath = output_filepath
        if audio_quality:
            self.audio_quality: Optional[str | int] = '128'

    def set_merge_videos(self, video_input_list, audio_input, output_filepath):
        self.video_input_list = video_input_list
        self.audio_input = audio_input
        self.output_filepath = output_filepath

    def run(self):
        match self.type:
            case 'Covert':
                self.convert_to_audio(
                    self.video_input, self.output_filepath, self.audio_quality, False)
            case 'Cut':
                self.error_callback('Cut')
            case 'Merge':
                self.merge_videos_with_looped_audio(
                    self.video_input_list, self.audio_input, self.output_filepath)
            case _:
                self.error_callback('Nothing')
