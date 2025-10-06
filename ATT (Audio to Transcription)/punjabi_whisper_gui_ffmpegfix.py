#!/usr/bin/env python3
"""
Punjabi Transcription/Translation GUI (Whisper) — FFmpeg-friendly build
Adds automatic FFmpeg discovery via imageio-ffmpeg (if available) and clearer
Windows-specific error messages for [WinError 2].
"""
import os
import sys
import json
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox

# Optional: PyTorch CUDA info (not required)
try:
    import torch  # type: ignore
    _TORCH_AVAILABLE = True
except Exception:
    _TORCH_AVAILABLE = False

# Prefer imageio-ffmpeg to supply an ffmpeg.exe if PATH lacks one
_FFMPEG_DIR_ADDED = False
try:
    import imageio_ffmpeg  # type: ignore
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    # Prepend so our ffmpeg wins
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    _FFMPEG_DIR_ADDED = True
except Exception:
    pass

import whisper  # openai-whisper

def _check_ffmpeg() -> str:
    """Return a string with ffmpeg -version first line or raise informative error."""
    try:
        out = subprocess.check_output(["ffmpeg", "-version"], stderr=subprocess.STDOUT, text=True, timeout=5)
        first = out.splitlines()[0] if out else "ffmpeg found"
        return first
    except FileNotFoundError as e:
        hint = (
            "FFmpeg executable not found.\n\n"
            "Quick fixes:\n"
            "1) Install 'imageio-ffmpeg' (pip install imageio-ffmpeg) and rerun this app, OR\n"
            "2) Install FFmpeg system-wide and add its 'bin' folder to PATH, then restart this app.\n\n"
            "Windows guide:\n"
            "- Download static build from gyan.dev or BtbN GitHub, unzip, and add the 'bin' folder to PATH.\n"
        )
        raise FileNotFoundError("[WinError 2] FFmpeg not found on PATH. " + hint) from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError("FFmpeg exists but failed to run. Output:\n" + (e.output or "")) from e


def to_srt_timestamp(t: float) -> str:
    hours = int(t // 3600)
    minutes = int((t % 3600) // 60)
    seconds = int(t % 60)
    millis = int(round((t - int(t)) * 1000))
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


class TranscriberApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Punjabi Transcription (Whisper) — FFmpeg OK")
        root.geometry("720x340")
        root.resizable(False, False)

        # Config
        self.model_options = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
        self.model_var = tk.StringVar(value="small")
        self.force_pa_var = tk.BooleanVar(value=True)
        self.translate_var = tk.BooleanVar(value=False)
        self.word_ts_var = tk.BooleanVar(value=False)

        self.model = None
        self.model_name_loaded = None
        self.transcription_thread = None
        self.cancel_event = threading.Event()

        # UI
        tk.Label(root, text="Select an audio/video file to transcribe or translate.").pack(pady=10)

        opts = tk.Frame(root); opts.pack(pady=5)
        tk.Label(opts, text="Whisper Model:").grid(row=0, column=0, padx=5, sticky="w")
        tk.OptionMenu(opts, self.model_var, *self.model_options).grid(row=0, column=1, padx=5, sticky="ew")
        tk.Checkbutton(opts, text="Force Punjabi Source", variable=self.force_pa_var).grid(row=0, column=2, padx=10, sticky="w")
        tk.Checkbutton(opts, text="Translate to English", variable=self.translate_var).grid(row=0, column=3, padx=10, sticky="w")
        tk.Checkbutton(opts, text="Word timestamps", variable=self.word_ts_var).grid(row=0, column=4, padx=10, sticky="w")

        btns = tk.Frame(root); btns.pack(pady=12)
        tk.Button(btns, text="Choose File and Go…", command=self.choose_file, width=24).grid(row=0, column=0, padx=6)
        tk.Button(btns, text="Cancel Current Job", command=self.cancel_job, width=20).grid(row=0, column=1, padx=6)

        self.status_label = tk.Label(root, text="Idle", bd=1, relief="sunken", anchor="w", padx=5)
        self.status_label.pack(side="bottom", fill="x", pady=5)

        self.output_dir = os.path.join(os.getcwd(), "whisper_outputs")
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_dir_label = tk.Label(root, text=f"Output Folder: {self.output_dir}", font=("Arial", 8), fg="gray")
        self.output_dir_label.pack(side="bottom", pady=2)

        # Environment status
        try:
            ff = _check_ffmpeg()
            self._push_status("FFmpeg OK: " + ff)
        except Exception as e:
            self._push_status(str(e))

        if _TORCH_AVAILABLE:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._push_status(self.status_label["text"] + f" | PyTorch: YES ({device})")
        else:
            self._push_status(self.status_label["text"] + " | PyTorch: NO")

    def _push_status(self, text: str) -> None:
        self.status_label.config(text=text)
        self.root.update_idletasks()

    def choose_file(self) -> None:
        if self.transcription_thread and self.transcription_thread.is_alive():
            messagebox.showwarning("Busy", "A transcription is already in progress. Please wait or Cancel.")
            return
        file_path = filedialog.askopenfilename(
            title="Select Audio/Video File",
            filetypes=[
                ("Media Files", "*.mp3 *.wav *.m4a *.mp4 *.mkv *.flac *.aac *.ogg *.wma *.mov"),
                ("All Files", "*.*")
            ]
        )
        if not file_path:
            return
        self._start_worker(file_path)

    def _start_worker(self, file_path: str) -> None:
        self.cancel_event.clear()
        self._push_status(f"Selected: {os.path.basename(file_path)}")
        self.transcription_thread = threading.Thread(target=self._transcribe_worker, args=(file_path,), daemon=True)
        self.transcription_thread.start()

    def cancel_job(self) -> None:
        if self.transcription_thread and self.transcription_thread.is_alive():
            self.cancel_event.set()
            self._push_status("Cancel requested…")
        else:
            messagebox.showinfo("Nothing to cancel", "No transcription is currently running.")

    def _load_model_if_needed(self) -> None:
        name = self.model_var.get()
        if self.model is None or self.model_name_loaded != name:
            self._push_status(f"Loading Whisper model: {name}… (first time may download)")
            try:
                self.model = whisper.load_model(name)
                self.model_name_loaded = name
            except Exception as e:
                self.model = None; self.model_name_loaded = None
                messagebox.showerror("Model Load Error", f"Failed to load model '{name}':\n{e}")
                raise

    def _transcribe_worker(self, file_path: str) -> None:
        try:
            # Ensure ffmpeg exists right before work (clear error msg if missing)
            _ = _check_ffmpeg()

            self._load_model_if_needed()

            base = os.path.splitext(os.path.basename(file_path))[0]
            txt_path = os.path.join(self.output_dir, f"{base}.txt")
            json_path = os.path.join(self.output_dir, f"{base}.json")
            srt_path = os.path.join(self.output_dir, f"{base}.srt")

            language_param = "pa" if self.force_pa_var.get() else None
            task_param = "translate" if self.translate_var.get() else "transcribe"

            self._push_status("Processing… (Whisper running; can take time)")
            result = self.model.transcribe(
                file_path,
                task=task_param,
                language=language_param,
                fp16=False,
                word_timestamps=self.word_ts_var.get(),
                verbose=False
            )

            if self.cancel_event.is_set():
                self._push_status("Canceled by user.")
                return

            text_out = (result.get("text") or "").strip()
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text_out + ("\n" if text_out else ""))
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            if "segments" in result and result["segments"]:
                with open(srt_path, "w", encoding="utf-8") as f:
                    for i, seg in enumerate(result["segments"], start=1):
                        start = to_srt_timestamp(float(seg.get("start", 0.0)))
                        end = to_srt_timestamp(float(seg.get("end", 0.0)))
                        text = (seg.get("text") or "").strip()
                        f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
            else:
                srt_path = None

            final = ["Done. Output saved to:", os.path.basename(txt_path), os.path.basename(json_path)]
            if srt_path:
                final.append(os.path.basename(srt_path))
            done_msg = "\n".join(final)
            self._push_status(done_msg)
            messagebox.showinfo("Operation Complete", done_msg)

        except FileNotFoundError as e:
            # Common Windows case: ffmpeg missing
            self._push_status("FFmpeg not found. See details.")
            messagebox.showerror("FFmpeg Missing", str(e))
        except Exception as e:
            self._push_status(f"Error: {e}")
            messagebox.showerror("Error", f"An error occurred:\n{e}")
        finally:
            self._push_status("Idle. Ready for next file.")
            self.transcription_thread = None
            self.cancel_event.clear()


def main() -> None:
    root = tk.Tk()
    app = TranscriberApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
