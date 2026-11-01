"""Single-run clipboard narration window. Clipboard is captured by the native launcher."""
import argparse
import json
import re
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


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-file', required=True)
    parser.add_argument('--config-file', required=True)
    args = parser.parse_args()

    text = Path(args.input_file).read_text(encoding='utf-8-sig').strip()
    config = json.loads(Path(args.config_file).read_text(encoding='utf-8'))
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
            from supertonic import TTS
            tts = TTS(auto_download=True)
            if stopped.is_set():
                return
            if config.get('style_path'):
                style = tts.get_voice_style_from_path(str(config['style_path']))
            else:
                voice = str(config.get('voice', 'M1')).upper()
                if voice not in {f'{prefix}{n}' for prefix in ('M', 'F') for n in range(1, 6)}:
                    raise ValueError('Unsupported preset voice')
                style = tts.get_voice_style(voice_name=voice)
            speed = min(2.0, max(0.7, float(config.get('speed', 1.05))))
            steps = min(12, max(2, int(config.get('steps', 8))))
            lang = str(config.get('lang', 'en'))
            if lang not in LANGS:
                lang = 'en'
            segments = split_text(text)
            for i, segment in enumerate(segments):
                if stopped.is_set():
                    break
                ready.append(f'Reading {i+1} / {len(segments)}')
                wav, _dur = tts.synthesize(segment, voice_style=style, lang=lang, speed=speed, total_steps=steps)
                if stopped.is_set():
                    break
                # Blocking playback, not just synthesis completion, determines end of task.
                samples = np.asarray(wav, dtype=np.float32).reshape(-1)
                if not samples.size:
                    continue
                rate = int(getattr(tts, 'sample_rate', 44100))
                sd.play(samples, samplerate=rate, blocking=True)
                if stopped.is_set():
                    break
            ready.append('Playback finished')
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
