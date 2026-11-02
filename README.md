# tbenitz · Pocket TTS Voice Studio

**Browser-local voice cloning, real speech preview, and a personalized Windows clipboard-reader EXE — using Pocket TTS only.**

Live site after GitHub Pages deployment: https://tbenitz.github.io/supertonic3gpt-clone/

## The workflow

1. Open the main website. It leads to the full Pocket TTS studio at `/pocket/`.
2. Let the Pocket TTS ONNX/WASM models download (only on the first visit; the browser caches them).
3. Select **Record** or **Upload** under **Voice Clone** (typically 5–10 seconds of clean speech).
4. When the new voice is encoded, choose **★ Cloned Voice** from the voice dropdown.
5. Type an example in **Text to Speak** or select an example button. Click **Generate Audio**.
6. Listen to the **actual cloned speech in your browser**. Playback streams as audio is generated.
7. After the sample finishes playing, confirm that you own or have permission to clone the voice. **Download personalized ClipboardVoice.exe** unlocks.
8. Copy any text on a **Windows 10/11 x64** PC and launch the EXE. It reads the clipboard immediately, generates Pocket TTS speech locally, shows a floating red Stop button, and exits **after real playback finishes**, or immediately on Stop.

The site does **not** send the audio recording, voice embedding or narration text to a cloning API. The browser uses ONNX Runtime Web and WASM. Model assets are downloaded from Hugging Face on first run and cached by the browser. The packaged Windows EXE also downloads model assets once on first use, then generates locally.

**Note:** The browser preview uses an ONNX/WASM runtime, while the Windows EXE uses KevinAHM's public Python ONNX Runtime implementation. Both use Pocket TTS and the same reference PCM; small differences in playback may occur between implementations. Model downloads, browser memory limits, and Windows CPU speed affect performance.

## Publish the repository

1. Repository: https://github.com/tbenitz/supertonic3gpt-clone
2. Under **Settings → Pages**, choose **GitHub Actions** as the source.
3. Open **Actions → Build Windows EXE and publish Studio → Run workflow** (or commit to `main`).
4. Verify that both the **windows** and **deploy** jobs finish successfully.
5. Open https://tbenitz.github.io/supertonic3gpt-clone/ and test the audio preview and EXE download.
6. On Windows, test startup, microphone/voice conditioning, speech, Stop, and automatic exit after speaking ends.

The workflow uses a Windows runner to package the Pocket TTS ONNX speech reader with PyInstaller. The Windows EXE uses the public KevinAHM ONNX voice-cloning bundles (CC BY 4.0), not Kyutai's gated native CLI model. On first use it downloads only the selected language's INT8 models from Hugging Face to the user's local model cache; no account or voice uploads are required. The website downloads a shared base EXE and appends each visitor's voice profile **in the browser**. Neither profile nor reference WAV goes into GitHub Actions.

The browser studio is built during deployment from a **pinned upstream revision** of https://github.com/hemanth/pocket-voice, then customized by `tools/customize_pocket.py`, `web/pocket-theme.css` and `web/pocket-export.js`. Source code remains editable here; no code from an unreviewed rolling branch is loaded at deploy time.

## Repository layout

- `web/index.html` — main URL forwards into the integrated Pocket TTS studio
- `web/pocket-export.js` — waits for a completed generated voice preview, then packages voice WAV into the EXE locally
- `web/pocket-theme.css` — navy/slate/cyan design matching the main site
- `tools/customize_pocket.py` — sets `tbenitz` branding, removes unrelated website/social tags, wires preview+export
- `desktop/engine/reader.py` — public Pocket ONNX voice cloning, low-latency streamed audio playback, red Stop button and automatic exit
- `.github/workflows/smoke-onnx.yml` — manual Windows voice-cloning smoke test that downloads models and produces an audible WAV
- `desktop/launcher/Program.cs` — Windows clipboard capture and profile extraction
- `.github/workflows/build-deploy.yml` — Windows EXE and GitHub Pages builder
- `.github/workflows/check.yml` — static source and Python/JavaScript syntax checks

## Attribution and licensing

- Website adaptation, branding and Windows export integration: **tbenitz**.
- Original browser voice-cloning application: **Pocket Voice**, Hemanth HM, licensed MIT: https://github.com/hemanth/pocket-voice
- Pocket TTS models and native runtime: Kyutai, under their respective model and code terms: https://github.com/kyutai-labs/pocket-tts
- Browser ONNX/WASM conversion and assets: KevinAHM: https://huggingface.co/spaces/KevinAHM/pocket-tts-web

The visitor-facing footer identifies **tbenitz** as the creator of this website/adaptation. Upstream attribution remains in `web/pocket/ATTRIBUTION.txt` after publishing. Only clone voices you own or are explicitly authorized to use. Do not impersonate someone deceptively.

If inference fails, the reader now shows the complete error in a Windows dialog, saves details under `%LOCALAPPDATA%\\ClipboardVoiceStudio\\last-error.txt`, and exits after dismissal rather than leaving the Stop button stuck. The manual **Verify Pocket TTS ONNX speech** workflow exercises actual model download, reference-audio encoding, and WAV generation. The published EXE should still be tested on the target Windows PC to confirm sound output, Stop and automatic exit.
