"""Single-run Pocket TTS clipboard reader. Audio is synthesized locally and played to completion."""
import argparse
import json
import re
import subprocess
import sys
import threading
import traceback
import tkinter as tk
from pathlib import Path


LANGS = {'en','ko','ja','ar','bg','cs','da','de','el','es','et','fi','fr','hi','hr','hu','id','it','lt','lv','nl','pl','pt','ro','ru','sk','sl','sv','tr','uk','vi'}


def split_text(text: str, size: int = 320):
    """Keep playback incremental and interruptible, without dropping characters."""
    paras = re.split(r'(?<=\n)', text)
    chunks = []
    for para in paras:
        rest = para.strip()
        while rest:
            if len(rest) <= size:
                chunks.append(rest)
                break
            end = max(rest.rfind('. ', 0, size + 1), rest.rfind('! ', 0, size + 1), rest.rfind('? ', 0, size + 1))
            if end > size // 3:
                cut = end + 1
            else:
                cut = rest.rfind(' ', 0, size + 1)
                if cut <= size // 3:
                    cut = size
            chunks.append(rest[:cut].strip())
            rest = rest[cut:].lstrip()
    return [s for s in chunks if s]


def load_profile(path):
    """Accept legacy UTF-8 BOM profiles as well as clean UTF-8 JSON."""
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-file', required=True)
    parser.add_argument('--config-file', required=True)
    args = parser.parse_args()

    text = Path(args.input_file).read_text(encoding='utf-8-sig').strip()
    config = load_profile(args.config_file)
    if not text:
        return

    stopped = threading.Event()
    root = tk.Tk()
    root.title('Clipboard Voice • Stop')
    root.configure(bg='#111827')
    root.attributes('-topmost', True)
    root.overrideredirect(True)
    width, height = 218, 76
    root.update_idletasks()
    root.geometry(f'{width}x{height}+{root.winfo_screenwidth()-width-24}+{root.winfo_screenheight()-height-76}')
    root.resizable(False, False)
    label = tk.Label(root, text='Preparing speech…', fg='#e5e7eb', bg='#111827', font=('Segoe UI', 9))
    label.pack(pady=(8, 1))
    button = tk.Button(root, text='■  STOP', font=('Segoe UI', 11, 'bold'), fg='white', bg='#d9364e', activebackground='#b91c39', relief='flat', command=lambda: halt())
    button.pack(fill='x', padx=12, pady=(1, 7))

    def halt():
        stopped.set()
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        try:
            root.destroy()
        except tk.TclError:
            pass

    root.bind('<Escape>', lambda _e: halt())
    root.protocol('WM_DELETE_WINDOW', halt)
    ready = []

    def worker():
        try:
            import numpy as np
            import sounddevice as sd
            import soundfile as sf
            binary = Path(sys.executable).resolve().parent / 'pocket_engine' / 'pocket-tts.exe'
            voice_path = Path(str(config.get('voice_path', '')))
            if not binary.is_file():
                raise RuntimeError('Pocket TTS Windows engine missing from reader bundle')
            if not voice_path.is_file():
                raise RuntimeError('Pocket reference audio is missing')
            supported = {'english_2026-04', 'english', 'german', 'spanish', 'italian', 'portuguese'}
            lang = str(config.get('lang', 'english_2026-04'))
            if lang not in supported:
                raise ValueError('Unsupported Pocket TTS language')
            segments = split_text(text, size=250)
            for i, segment in enumerate(segments):
                if stopped.is_set():
                    break
                ready.append(f'Pocket TTS · generating {i+1} / {len(segments)}')
                wav_path = Path(args.input_file).parent / f'pocket_chunk_{i:04d}.wav'
                cmd = [str(binary), 'generate', '--text', segment, '--voice', str(voice_path), '--language', lang, '--output-path', str(wav_path)]
                stderr_path = Path(args.input_file).parent / f'pocket_stderr_{i:04d}.txt'
                with stderr_path.open('wb') as error_log:
                    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=error_log,
                                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                    while p.poll() is None:
                        if stopped.wait(0.12):
                            p.kill()
                            p.wait()
                            break
                if stopped.is_set():
                    break
                stderr = stderr_path.read_text(encoding='utf-8', errors='replace')[-1500:]
                stderr_path.unlink(missing_ok=True)
                if p.returncode:
                    raise RuntimeError('Pocket TTS failed: ' + stderr[-250:])
                samples, rate = sf.read(str(wav_path), dtype='float32')
                wav_path.unlink(missing_ok=True)
                if stopped.is_set():
                    break
                ready.append(f'Pocket TTS · speaking {i+1} / {len(segments)}')
                sd.play(np.asarray(samples, dtype=np.float32).reshape(-1),
                        samplerate=int(rate), blocking=True)
            ready.append('Playback finished')
            ready.append('__EXIT__')
            return
        except Exception as ex:
            ready.append('Error: ' + str(ex)[:110])
            traceback.print_exc()
            # Keep an error visible until the user closes it.
            return
        ready.append('__EXIT__')

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    def poll():
        while ready:
            status = ready.pop(0)
            if status == '__EXIT__':
                halt()
                return
            label.config(text=status)
        if stopped.is_set():
            return
        root.after(150, poll)

    root.after(100, poll)
    root.mainloop()


if __name__ == '__main__':
    run()
