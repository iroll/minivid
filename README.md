# minivid

Quickly review video files in a folder without reaching for the mouse.

Drop a video onto minivid, or launch it with a video path. Minivid opens that
video, treats its folder as the review queue, and lets you tab through sibling
videos or send the current one to the Recycle Bin.

## Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - macOS/Linux: `source venv/bin/activate`
   - Windows: `venv\Scripts\activate`
4. Install VLC: https://www.videolan.org/vlc/
5. Install dependencies: `pip install -r requirements.txt`

## Usage

```powershell
python minivid.py C:\path\to\video.mp4
```

You can also launch minivid with no arguments and drop a video file onto the
window.

On Windows, drag a video file onto `minivid.bat` to launch minivid directly with
that file.

If Windows prints "UNC paths are not supported", CMD was started from a network
folder. Set a shortcut's **Start in** folder to `C:\Users\Isaac\minivid` (or your
local minivid folder). The batch launcher handles network paths with `pushd`,
but cannot prevent a warning printed before it starts.

## Controls

- `Tab`: next video in the folder
- `Shift+Tab`: previous video in the folder
- `Del`: move the current video to the Recycle Bin, then show the next video
- `Space`: pause or resume
- `Esc`: close minivid

## License

[Add license information here]
