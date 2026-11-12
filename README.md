# Frame Extractor (Full Resolution)

<p align="center">
  <img src="icon.png" width="128" height="128" alt="Frame Extractor Logo">
  <br>
  <b>Fast, lossless, 100% native resolution video frame extractor for Windows.</b>
  <br><br>
  <a href="https://buymeacoffee.com/dahltools" target="_blank">
    <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="160">
  </a>
</p>

---

## Features

- **100% Native Resolution Retained**: Extracted frames match the exact pixel dimensions of your source video (4K remains 4K, 1080p remains 1080p). Zero distortion or squishing.
- **Drag-and-Drop Support**:
  - Drag and drop videos directly into the app window.
  - Or drag and drop video files onto `FrameExtractor.exe` or `run.bat` in Windows Explorer.
- **Lossless Quality**: Exports to uncompressed PNG by default, with an optional toggle for high-quality JPG.
- **Flexible Extraction Modes**:
  - **Every Frame**: Extracts every single frame from the video.
  - **1 per Second (1 FPS)**: Grabs one frame per second.
  - **Every N Frames**: Customizable step interval (e.g. every 5th or 10th frame).
- **Fast Performance**: Utilizes FFmpeg for rapid extraction (hundreds of frames per second) without locking the UI.
- **Convenient Output**: Automatically creates an output folder alongside your video and provides an **"Open Output Folder"** button upon completion.

---

## Getting Started

### Option 1: Standalone Executable (No Python Required)
1. Download `FrameExtractor.exe` from the [Releases](https://github.com/DahlTools/FrameExtractor/releases) section.
2. Double-click `FrameExtractor.exe` or drag a video file onto the executable icon.

### Option 2: Running from Source
1. Clone the repository:
   ```bash
   git clone https://github.com/DahlTools/FrameExtractor.git
   cd FrameExtractor
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python FrameExtractor.py
   ```

*Note: For maximum speed, make sure [FFmpeg](https://ffmpeg.org/download.html) is installed and available in your system PATH.*

---

## Building the Executable

To build a standalone single-file executable using PyInstaller:

```bash
pyinstaller --noconfirm --onefile --windowed --icon="icon.ico" --name="FrameExtractor" "FrameExtractor.py"
```

The resulting executable will be placed in the `dist/` directory.

---

## License

This project is licensed under the [MIT License](LICENSE).

Inspired by the concept of [barisx/dragndropvideo2frame](https://github.com/barisx/dragndropvideo2frame).
