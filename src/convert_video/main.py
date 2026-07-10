import argparse
import datetime
import sys
import time
from argparse import ArgumentParser
from ast import arg
from pathlib import Path

import ffmpeg

from .convert import format_run_time_str, run
from .logger import logger


def validate_path(path):
    """Validates if a file exists and is indeed a file."""
    path = Path(path)
    if not path.exists():
        raise argparse.ArgumentTypeError(f"{path}' does not exist.")
    return path


def validate_scale(scale):
    try:
        scale = float(scale)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{scale}' must be a float")

    if any([scale >= 1, scale < 0]):
        raise argparse.ArgumentTypeError(
            f"{scale}' must be greater than 0 and less than or equal to 1"
        )
    return scale


def validate_crf(crf):
    try:
        crf = float(crf)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"{crf}' must be an int or float between 0 and 51"
        )
    if any([crf < 0, crf > 51]):
        raise argparse.ArgumentTypeError(f"{crf}' must be between 0 and 51")
    return crf


def parse_arguments():
    parser = ArgumentParser(description="Convert videos to a smaller size")

    parser.add_argument("path", type=validate_path, help="can be a directory or file")

    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="set to recursively search directories for videos to convert",
    )

    parser.add_argument(
        "-s",
        "--suffix",
        action="store",
        default="converted",
        help="suffix added to file name after converting: vid1.mp4 -> vid1.converted.mp4",
    )

    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="set to overwrite output file if it exists",
    )

    parser.add_argument(
        "-sf",
        "--scale",
        action="store",
        type=validate_scale,
        help="Must be a float between 0 and 1.Mmultiplied by videos width to reduce size.",
    )
    parser.add_argument(
        "-crf",
        action="store",
        type=validate_crf,
        required=False,
        help="Must be a float or int between 0 and 51",
    )

    parser.add_argument(
        "-p",
        "--preset",
        choices=[
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ],
        action="store",
        default="slow",
        help="Select ffmpeg x265 preset",
    )

    parser.add_argument(
        "-t",
        "--tune",
        choices=["psnr", "ssim", "grain", "zerolatency", "fastdecode"],
        action="store",
        default="fastdecode",
        help="Select ffmpeg x265 tune",
    )

    parser.add_argument(
        "--pix_fmt",
        action="store",
        default="yuv444p10le",
        help="pixel format for ffmpeg",
    )

    parser.add_argument(
        "-g",
        "--gop_interval",
        action="store",
        type=int,
        help="GOP Interval. Used to calculate values for g and keyint_min",
    )

    args = parser.parse_args()
    return {k: v for k, v in vars(args).items() if v is not None}


def main():
    start_time = datetime.datetime.fromtimestamp(time.time())
    args = parse_arguments()
    print(args)
    path = args.pop("path")
    recursive = args.pop("recursive", False)

    run(path, recursive=recursive, **args)
    finish_time = datetime.datetime.fromtimestamp(time.time())
    logger.info(f"finished")
    logger.info(f"Total runtime: {format_run_time_str(start_time,finish_time)}")


if __name__ == "__main__":
    main()
