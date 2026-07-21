import shutil
from collections import defaultdict
from pathlib import Path

import ffmpeg

from .logger import logger


def is_video(video_path):
    video_path = Path(video_path)
    if video_path.is_file():
        try:
            ffmpeg.probe(video_path)
            return True
        except ffmpeg.Error as e:
            logger.info(f"{video_path} is not a video")
    return False


def move_finished(vid_dir=".", done_dir="done", recursive=False):
    vid_dir = Path(vid_dir)
    done_dir = Path(done_dir)
    done_dir.mkdir(parents=True, exist_ok=True)
    vid_dict = get_vid_dict(vid_dir, recursive=recursive)
    for key, value in vid_dict.items():
        if len(value) == 2 and any(["converted" in str(v) for v in value]):
            for vid in value:
                src = vid
                dst = vid_dir.joinpath(src)
                shutil.move(src, dst)


def get_vid_dict(path=".", recursive=False):
    d = defaultdict(list)
    for file in Path(path).iterdir():
        if is_video(file):
            key = file.parent.joinpath(file.stem.replace(".converted", "")).as_posix()
            d[key].append(file)
        elif file.is_dir() and recursive == True:
            d.update(get_vid_dict(file, recursive))
    return d


def get_size_diff(path=".", recursive=False):
    path = "." if not path else path
    MB = 1024 * 1024
    c_size, u_size = [0, 0]
    size_d = {}
    for k, v in get_vid_dict(path, recursive).items():
        if len(v) == 2:
            c, u = [round(i.stat().st_size / MB, 2) for i in sorted(v)]
            size_d[k] = {"converted": c, "unconverted": u}
            c_size += c
            u_size += u
    c_size, u_size = [round(i, 2) for i in (c_size, u_size)]
    return {
        "saved": u_size - c_size,
        "converted": c_size,
        "unconverted": u_size,
        "files": size_d,
    }
