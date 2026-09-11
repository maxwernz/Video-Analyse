"""Generate the real media the canonical fixture refers to.

The video-surface question cannot be answered against a placeholder rectangle,
so the prototype plays a genuine H.264 file that Qt must decode and composite.
The clip is synthetic — this repository carries no match footage — but it is a
real file of the real duration with real motion and a burned-in timecode, which
is what makes a seek visibly right or wrong.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
MEDIA = PROTOTYPE_ROOT / "media"
FONT = PROTOTYPE_ROOT.parents[1] / "assets" / "fonts" / "NotoSans.ttf"

PITCH = "0x24422F"


def _filters() -> str:
    """A pitch, a halfway line, a moving marker and a burned-in timecode."""
    return ",".join(
        (
            f"drawbox=x=0:y=252:w=640:h=108:color=0x1D3626@1:t=fill",
            "drawbox=x=319:y=0:w=2:h=252:color=white@0.35:t=fill",
            "drawbox=x=0:y=250:w=640:h=2:color=white@0.35:t=fill",
            "drawbox=x=40:y=60:w=2:h=190:color=white@0.25:t=fill",
            "drawbox=x=598:y=60:w=2:h=190:color=white@0.25:t=fill",
            # Two markers moving at different rates, so any frame is distinct.
            "drawbox=x='40+mod(t*47\\,540)':y='120+70*sin(t*0.7)':w=11:h=11"
            ":color=0xF2F4F6@1:t=fill",
            "drawbox=x='560-mod(t*31\\,520)':y='150+55*cos(t*0.5)':w=11:h=11"
            ":color=0x5B87D6@1:t=fill",
            f"drawtext=fontfile={FONT}:text='%{{pts\\:hms}}'"
            ":x=w-tw-14:y=h-th-12:fontsize=20:fontcolor=0xE8EAED@0.85"
            ":box=1:boxcolor=0x000000@0.45:boxborderw=6",
        )
    )


def render(name: str, seconds: int) -> Path:
    MEDIA.mkdir(parents=True, exist_ok=True)
    destination = MEDIA / name
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-f", "lavfi",
        "-i", f"color=c={PITCH}:s=640x360:r=25:d={seconds}",
        "-vf", _filters(),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "32",
        "-g", "50",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(destination),
    ]
    print(f"==> {destination.name} ({seconds}s)")
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return destination


def main() -> int:
    for name, seconds in (("halbzeit-1.mp4", 2700), ("halbzeit-2.mp4", 2550)):
        rendered = render(name, seconds)
        print(f"    {rendered.stat().st_size / 1_000_000:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
