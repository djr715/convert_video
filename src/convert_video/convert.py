import glob
import itertools as it
import json
import logging
import os
import shutil
import sys
from logging import basicConfig, getLogger
from pathlib import Path
from typing import Union
from unittest import skip
from unittest.mock import DEFAULT

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(sys.stdout)
# log_format = logging.Formatter(
#    "%(filename)s] %(funcName)s() -> Line %(lineno)d | %(levelname)s: %(message)s"
# )
# console_handler.setFormatter(log_format)
logger.addHandler(console_handler)


import ffmpeg

VIDEO_EXTS = [
    "wmv",
    "avi",
    "mp4",
    "flv",
    "flac",
    "m4v",
    "mkv",
    "rm",
    "mpg",
    "mov",
    "asf",
]

DEFAULT_SUFFIX = "converted"

DEFAULT_CRF = 21.6
DEFAULT_PRESET = "slow"
DEFAULT_SCALE_FACTOR = 0.5
DEFAULT_TUNE = "fastdecode"
DEFAULT_GOP_INTERVAL = 10

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_output_path(input_path, suffix=None):
    if not suffix:
        suffix = DEFAULT_SUFFIX
    input_path = Path(input_path)
    new_suffix = f".{suffix}{input_path.suffix}"
    output_name = input_path.with_suffix(new_suffix).parts[-1]

    output_dir = input_path.parent.joinpath("tmp")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir.joinpath(output_name)


def create_patterns(recursive=False):
    patterns = [f"*{ext}" for ext in VIDEO_EXTS]
    if recursive is True:
        patterns = [f"**/{pattern}" for pattern in patterns]
    return patterns


def get_input_paths(path=Path("."), recursive=False):
    path = Path(path)
    posix = path.as_posix()
    if path.is_file():
        return glob.glob(posix)
    patterns = create_patterns(recursive)
    return it.chain.from_iterable(
        glob.iglob(pattern, recursive=recursive, root_dir=path) for pattern in patterns
    )


def create_video_filter(filter_converted=True):
    def video_filter(video_path):
        video_path = Path(video_path)
        try:
            probe = ffmpeg.probe(video_path)
        except ffmpeg.Error as e:
            logger.info(f"{video_path} is not a video")
            return False
        if filter_converted:
            fmt = probe.get("format", {})
            tags = fmt.get("tags", {})
            comment = tags.get("comment") or tags.get("Comment") or ""
            return "converted" not in comment.lower()
        return True

    return video_filter


def get_video_stream(path):
    data = ffmpeg.probe(path)
    for stream in data["streams"]:
        if stream["codec_type"] == "video":
            return stream


def get_fps(vid_stream):
    dd, dv = [int(i) for i in vid_stream["avg_frame_rate"].split("/")]
    return round(dd / dv)


def get_gop(vid_stream, gop_interval: int):
    fps = get_fps(vid_stream)
    return gop_interval * fps


def get_aspect_ratio(vid_stream):
    return vid_stream["width"] / vid_stream["height"]


def get_new_scale(vid_stream, scale_factor: Union[int, float]):
    w, h = [vid_stream[i] for i in ("width", "height")]
    w = int(round(w * scale_factor, 0))
    if w < 520:
        w = 520
    return (w, -2)


def convert_video(input_path, output_path, overwrite_existing=False, **kwargs):
    input_path, output_path = str(input_path), str(output_path)
    stream = get_video_stream(input_path)

    scale_factor = kwargs.get("scale", DEFAULT_SCALE_FACTOR)
    print(f"scale_factor = {scale_factor}")
    crf = kwargs.get("crf", DEFAULT_CRF)
    print(f"crf = {crf}")
    preset = kwargs.get("preset", DEFAULT_PRESET)
    print(f"preset = {preset}")
    tune = kwargs.get("tune", DEFAULT_TUNE)
    print(f"tune = {tune}")
    gop_interval = kwargs.get("gop_interval", DEFAULT_GOP_INTERVAL)
    print(f"gop_interval = {gop_interval}")

    gop = get_gop(stream, gop_interval)

    w, h = get_new_scale(stream, scale_factor)
    print(f"width = {w}")

    (
        ffmpeg.input(input_path)
        .filter("scale", w, h)
        .output(
            output_path,
            n=None,
            vcodec="libx265",
            **{"x265-params": "log-level=error"},
            **{"tag:v": "hvc1"},
            crf=crf,
            strict=-2,
            tune=tune,
            g=gop,  # sets the GOP size / maximum keyframe interval
            keyint_min=gop,
            preset=preset,
            pix_fmt="yuv444p10le",  # forces 10-bit color depth with 4:4:4 chroma subsampling
            movflags="+faststart",
            map_metadata=0,  # Added: copies all global metadata from the first input (input 0)
            metadata="comment=converted",  # Added: injects or overwrites the 'comment' metadata tag
        )
        .global_args("-v", "quiet", "-stats", "-n")
        .run()
    )


def run(path=".", recursive=False, filter_converted=True, **kwargs):
    errs = []
    count = 0
    completed = 0

    path = Path(path)
    video_filter = create_video_filter(filter_converted)
    input_paths = filter(video_filter, get_input_paths(path=path, recursive=recursive))
    for input_path in input_paths:
        count += 1
        input_path = Path(input_path)
        output_path = get_output_path(
            input_path, suffix=kwargs.get("suffix") or DEFAULT_SUFFIX
        )
        dest_path = input_path.parent.joinpath(
            output_path.parts[-1]
        )  # dest path for covnerted video
        if dest_path.exists and not kwargs.get("overwrite_existing"):
            logger.info(f"Skipping {output_path.parts[-1]}: already converted")
            continue
        logger.info(f"Converting: {input_path.parts[-1]}")
        try:
            convert_video(input_path.as_posix(), output_path.as_posix(), **kwargs)
        except Exception as e:
            logger.error(f"failed to convert: {input_path}", exc_info=e)
            errs.append((input_path, e))
            if all([count == 0, len(errs) > 2]):
                logger.error("error limit exceeded, exiting")
                sys.exit(1)
            else:
                continue
        if output_path.exists():
            dest = input_path.parent.joinpath(output_path.parts[-1])
            shutil.move(output_path, dest)
            logger.info(
                f"moved {output_path.parts[-1]} to {input_path.parent.absolute()}"
            )
            if len(list(output_path.parent.iterdir())) == 0:
                shutil.rmtree(output_path.parent)
            else:
                logger.warning(
                    "can't delete temporary output directory because it's not empty"
                )
        completed += 1
        logger.info(f"finished converting {input_path}")

    logger.info(f"converted {completed} out of {count} videos")
    if errs:
        with open("errors.json", "w") as f:
            json.dump([{e[0]: e[1].args} for e in errs], f, skipkeys=True, indent=4)
        logger.info(f"wrote errors to {Path("errors.json").absolute()}")
