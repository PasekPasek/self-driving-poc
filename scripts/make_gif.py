"""Assemble a folder of PNG frames into a palette-optimised GIF (used by scripts/make_gifs.mjs).

Usage: python3 scripts/make_gif.py FRAMES_DIR OUT.gif [--fps 12] [--width 800] [--colors 64] [--hold-last MS]
Needs Pillow only.
"""
import argparse
import sys
from pathlib import Path

from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("frames", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--colors", type=int, default=64)
    parser.add_argument("--hold-last", type=int, default=0, help="extra milliseconds on the last frame")
    args = parser.parse_args()

    files = sorted(args.frames.glob("*.png"))
    if not files:
        sys.exit(f"no PNG frames in {args.frames}")
    frames = []
    for file in files:
        image = Image.open(file).convert("RGB")
        height = round(image.height * args.width / image.width)
        frames.append(image.resize((args.width, height), Image.LANCZOS))

    # One shared palette (built from a sample of frames) keeps colours steady from frame to frame.
    sample = frames[:: max(1, len(frames) // 12)]
    mosaic = Image.new("RGB", (args.width, frames[0].height * len(sample)))
    for i, image in enumerate(sample):
        mosaic.paste(image, (0, i * image.height))
    palette = mosaic.quantize(colors=args.colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    paletted = [image.quantize(palette=palette, dither=Image.Dither.NONE) for image in frames]

    durations = [round(1000 / args.fps)] * len(paletted)
    durations[-1] += args.hold_last
    args.out.parent.mkdir(parents=True, exist_ok=True)
    paletted[0].save(
        args.out, save_all=True, append_images=paletted[1:], duration=durations, loop=0, optimize=True, disposal=1
    )
    print(f"{args.out}: {len(paletted)} frames, {args.out.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
