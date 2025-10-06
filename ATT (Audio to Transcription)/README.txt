Punjabi Whisper GUI (Transcription & Translation)
===============================================

This tool provides a simple graphical interface (Tkinter) for transcribing or translating
Punjabi (Gurmukhi) audio/video files using OpenAI's Whisper model.

It automatically saves outputs as:
- Plain text (.txt)
- JSON (.json) with segment details
- SubRip subtitles (.srt)

-----------------------------------------------
Owner Information
-----------------------------------------------
Project Owner: Gurleen Rajput  
Official Website: https://gurleenrajput.online
E-mail - mail@gurleenrajput.online 
-----------------------------------------------
Requirements
-----------------------------------------------
1. Python 3.9+
2. The following Python packages (install via requirements file):
   - openai-whisper
   - torch (with CUDA if available)
   - imageio-ffmpeg (for ffmpeg executable)
   - tkinter (usually comes with Python on Windows)

-----------------------------------------------
Installation
-----------------------------------------------
1. Create a virtual environment (recommended):
   python -m venv venv
   venv\Scripts\activate   (Windows)
   source venv/bin/activate (Linux/macOS)

2. Install dependencies:
   pip install -r requirements_ffmpegfix.txt

   This will ensure Whisper, Torch, and FFmpeg are available.

-----------------------------------------------
Usage
-----------------------------------------------
1. Run the app:
   python punjabi_whisper_gui_ffmpegfix.py

2. Select Whisper model from dropdown (tiny, base, small, medium, large, large-v2, large-v3).
   - Smaller models are faster but less accurate.
   - Large models are slower but more accurate.

3. Options:
   - "Force Punjabi Source": Forces Whisper to treat input as Punjabi ("pa") for faster detection.
   - "Translate to English": Produces English text instead of Punjabi transcription.
   - "Word timestamps": Adds word-level timing (slower, larger output).

4. Click "Choose File and Go…" and select your audio/video file.
   Supported formats: mp3, wav, m4a, mp4, mkv, flac, aac, ogg, wma, mov.

5. The app processes the file. Progress shown in status bar.

6. Outputs will be saved in the "whisper_outputs" folder inside the current working directory.

-----------------------------------------------
FFmpeg Notes
-----------------------------------------------
- This patched version bundles FFmpeg automatically via `imageio-ffmpeg`.
- If you prefer, you can install FFmpeg manually system-wide:
  - Windows: Download static build (gyan.dev or BtbN GitHub), unzip, add 'bin' folder to PATH.
  - Linux: sudo apt-get install ffmpeg
  - macOS: brew install ffmpeg

Check installation with:
   ffmpeg -version

-----------------------------------------------
Canceling Jobs
-----------------------------------------------
- You can press "Cancel Current Job" while transcription is running.
- Whisper does not support mid-call cancellation; cancel request will stop *after* current run.

-----------------------------------------------
Packaging (Optional)
-----------------------------------------------
If you want to create a standalone executable:

   pip install pyinstaller
   pyinstaller --onefile --noconsole punjabi_whisper_gui_ffmpegfix.py

Distribute the resulting EXE (dist folder).

-----------------------------------------------
Tips
-----------------------------------------------
- If running on GPU, install CUDA-compatible PyTorch for speed.
- First run may download model weights (hundreds of MBs).
- Large model = higher RAM/VRAM usage.

Enjoy fast Punjabi transcription/translation!
