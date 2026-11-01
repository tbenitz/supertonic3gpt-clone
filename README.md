# Supertonic3GPT Clone

**A GitHub Pages voice-builder website + GitHub Actions Windows EXE builder + optional CPU/GPU voice-style extraction.**

This repository is a **testable starter**, not a production voice-cloning SaaS. Its source and formatting tests run locally, but the full Windows compilation and model extraction need their first real GitHub Actions / CPU or GPU test. Please check the Actions logs before distributing any EXE.

## What users can do

- **Built-in voice:** choose any Supertonic 3 voice M1–M5 or F1–F5, language, speed and quality.
- **Upload a voice JSON:** import a compatible Supertonic-3 `style_ttl` / `style_dp` JSON.
- **Upload an audio recording:** with explicit speaker permission, send a WAV/MP3/FLAC/OGG/M4A recording to **your own authenticated cloning backend** (CPU or GPU), then download the resulting JSON or bundle it into the EXE.
- **Download a personalized EXE:** browser embeds profile into an already-built Windows application **without sending JSON to GitHub**. The same published EXE engine is reused for everybody.
- **Read clipboard:** when launched on Windows x64, it captures the current text clipboard. The red floating Stop button interrupts speaking, and the application exits **after actual blocking audio playback completes**. You can launch it again later; no perpetual background process.

**Important limits:** GitHub Pages is a static host. It does not run PyTorch or voice cloning jobs. GitHub Actions builds the EXE, and can perform a **manual CPU voice-style extraction** using an upstream example recording or a WAV explicitly committed to this repository. It **cannot directly accept private anonymous website audio uploads**. Do not commit private voice samples into a public repo.

## 1. Create the brand-new GitHub repository

GitHub's connected integration cannot create a repository directly in this environment, so the repository owner must create the empty repository once:

1. Visit <https://github.com/new?name=supertonic3gpt-clone> while signed into GitHub.
2. Owner: `tbenitz`; repository name: **`supertonic3gpt-clone`**; visibility: **Public**.
3. You may leave **Add a README** and **Add .gitignore** unchecked, because this ZIP already contains both. Click **Create repository**.
4. Download the supplied `supertonic3gpt-clone.zip` and **extract it**. **Upload the contents, not the ZIP**, so `README.md`, `web/`, `desktop/`, `backend/`, and `.github/` appear at the repository root.
5. On the empty repo page choose **uploading an existing file** (or **Add file > Upload files**). Drag the extracted files and folders, ensuring GitHub preserves nested paths, especially `.github/workflows/` (GitHub's `.` directories may be hidden in some file managers). Click **Commit changes**.
6. Check that `.github/workflows/build-deploy.yml` and `.github/workflows/clone-voice-cpu.yml` are visible on GitHub. If nested folders were lost, use the web editor at `https://github.dev/tbenitz/supertonic3gpt-clone` to fix them and commit.

**Chromebook-friendly method:** GitHub web upload or the VS Code editor at `github.dev` does not require a local Windows computer. If GitHub's web uploader doesn't preserve folder paths, use a GitHub Codespace or Git on another system to commit the extracted folder.

## 2. Deploy the website and EXE builder

1. Open **Settings → Pages** in your new repository. For **Build and deployment**, select **GitHub Actions**.
2. Open **Actions**. If workflows require approval, enable them. Open **Build Windows EXE and publish Studio**, then **Run workflow**, or just push a commit to `main`.
3. The Windows runner installs Python/.NET 8, builds the Python speech reader with PyInstaller, compiles a native Windows launcher, packages the runtime into `ClipboardReader-Base.exe`, and publishes `web/` to GitHub Pages.
4. Open the Actions run and make sure both jobs (**windows**, **deploy**) succeed. If not, use the failing step's logs to diagnose dependency/version problems; the first Windows build has *not* been validated on GitHub yet.
5. Visit **<https://tbenitz.github.io/supertonic3gpt-clone/>**, which should be available only **after** a successful deploy. GitHub's Settings → Pages shows its actual URL.
6. First try the **Preset voice** tab and **Download personalized EXE**; copy some text on a **Windows 10/11 x64** PC and launch the downloaded EXE. You should see the red Stop control. Allow one sentence to finish completely and verify the process exits; test Stop and relaunch separately.

The executable currently downloads roughly 400 MB of Supertonic 3 assets on its first run. After caching, inference runs locally. It is **not a completely self-contained offline-first-run download**; the downloaded voice profile is contained in the EXE, but the ONNX model weights are downloaded once by the Python SDK.

Windows may warn about unfamiliar unsigned executables. This project does not automatically sign builds. Inspect source and release artifacts; do not disable security tools indiscriminately.

## 3. Try voice cloning using GitHub Actions CPU (optional, without GPU)

The project you supplied, <https://github.com/saurabhv749/supertonic3-voice-clone>, loads Supertonic **ONNX** assets but uses **PyTorch gradient-based optimization** to learn a JSON style. Its `train_style.py` chooses CUDA when available **or CPU otherwise**. Speech synthesis itself is ONNX and runs locally on CPU without training.

For the **manual CPU demo**, after uploading this repository:

1. Go to **Actions → Optional CPU voice cloning (manual) → Run workflow**.
2. Select **`upstream-example`** for `source`. Leave the default **300 steps** to test. More steps can improve voice similarity but are slower, especially on CPU.
3. Run the workflow. It downloads the original example clip and model, runs CPU-only training, and uploads `supertonic3-voice-style-json` as an Actions artifact **if it finishes before the 240-minute job timeout**. Successful completion is **not guaranteed**, especially at higher step counts.
4. Download the artifact, unzip it and import `personal.json` into your website's **Upload voice JSON** tab. Export your custom EXE.

**Your own recording with Actions:** The `repo-wav` choice can use `samples/reference.wav` in the repository. The `.gitignore` intentionally ignores WAVs to prevent accidental disclosure; uploading this sample explicitly via the GitHub UI or force-adding it with Git (`git add -f samples/reference.wav`) is required. **Do not do this for sensitive recordings in a public repository**: Git history retains uploaded voice data. Only use this for recordings you own and explicitly intend to publish. For private voice samples, use a private clone of this repo, a controlled backend, or run the extractor locally. The public GitHub website itself cannot turn a private audio upload directly into an Actions run without more infrastructure.

GitHub-hosted Actions minutes and runner execution limits apply. CPU training can be *significantly* slower than the upstream GPU-reported 6–30 minutes; this workflow is experimental and may time out. GPU is optional, not required by the underlying optimizer.

## 4. Enable the site's **Clone from audio** tab with a private CPU service (optional)

A separate machine with sufficient RAM, free disk space, Python dependency support, Docker and HTTPS hosting can run the included FastAPI service. From **this repository root**:

```sh
docker build -f backend/Dockerfile.cpu -t supertonic3gpt-cpu .
docker run --rm -p 7860:7860 \
  -e CLONE_API_TOKEN=REPLACE_WITH_A_LONG_RANDOM_SECRET \
  -e ALLOWED_ORIGINS=https://tbenitz.github.io \
  -e CLONE_STEPS=600 \
  -e CLONE_TIMEOUT_SECONDS=14400 \
  supertonic3gpt-cpu
```

The Dockerfile downloads the Supertonic model and installs the upstream CPU/PyTorch trainer. **This may consume several gigabytes of disk and RAM and take hours per voice.** Use `CLONE_STEPS=300` for an initial experiment if needed. More training steps are not a guarantee of quality. The app keeps the JSON for about an hour, deletes uploaded audio after the training job, and allows one processing job at a time.

For a remotely hosted site, put this container behind an **HTTPS reverse proxy**; do **not** expose plain HTTP over the Internet. The **private cloning service URL** and **token** are entered on the website when using the audio tab. Do not put that token in the repository or send it to anonymous visitors.

The server currently requires one manually supplied secret (`CLONE_API_TOKEN`) and is intended **only for private, trusted testing**. To enable public anonymous cloning you would need a user identity system, rate limiting, abuse prevention, per-user quotas, an upload/privacy policy and funded CPU/GPU capacity. **A public GitHub Pages website without these services still fully supports presets and JSON-to-EXE exports.**

An optional GPU Docker example is provided as `backend/Dockerfile.gpu`, but GPU use is not mandatory. Its base image/Python/CUDA dependency combination needs validation on the actual host; the **CPU Dockerfile** is the recommended starting point for no-GPU testing.

## How the Windows EXE works

- GitHub Actions packages the entire PyInstaller `reader` directory as ZIP data at the end of a compiled .NET native launcher, ending in the magic bytes `CVRZIP01` and an 8-byte length.
- The browser downloads this **base engine**, appends the selected voice JSON/configuration, plus `CVRCFG01` and a length, then saves a single `ClipboardVoice.exe`. Neither the voice JSON nor the clipboard text is sent to GitHub.
- The native executable reads the clipboard immediately, extracts a cached engine under `%LOCALAPPDATA%/ClipboardVoiceStudio`, and launches the reader. On first run, the reader downloads and caches Supertonic model weights.
- Tkinter displays a small red Stop window near the bottom right of the primary display. The playback loop synthesizes chunks, **plays each with blocking sounddevice audio**, and exits after the last playback returns. Pressing Stop interrupts audio and closes the UI. Launch again whenever you want.

Windows-specific limitations: text clipboard only; Windows 10/11 x64; no startup hotkey installed by default; one-time model download; Windows unsigned executable; first-run extraction adds startup latency; corner positioning may be imperfect with multiple monitors or display scaling. This is not a background clipboard watcher.

## Files

```text
web/index.html                         GitHub Pages website, voice import and browser-side EXE export
.github/workflows/build-deploy.yml      Windows build + Pages publish
.github/workflows/clone-voice-cpu.yml   Optional manually run CPU-training workflow
.github/workflows/check.yml            Python syntax and regression tests
desktop/launcher/Program.cs             Single-file Windows bootstrapping, clipboard, custom voice overlay
desktop/engine/reader.py                Supertonic ONNX speech, playback/stop/exit
backend/app.py                          Private authenticated audio-upload training API
backend/Dockerfile.cpu                  CPU-only cloning service image
backend/Dockerfile.gpu                  Optional GPU service image
tools/prepare_cpu_clone.py              Validate workflow-dispatch input sample path and steps
tools/append_bundle.py                  Embed bundled reader in native EXE
samples/README.md                       Warnings about public voice recordings
tests/test_starter.py                   Smoke and format tests
```

## Source, licensing and privacy

- Supertonic 3 model: Supertone Inc., **OpenRAIL-M** terms: <https://huggingface.co/Supertone/supertonic-3>
- Supertonic Python: <https://github.com/supertone-oss-archive/supertonic-py>
- The cloning implementation you linked: <https://github.com/saurabhv749/supertonic3-voice-clone> (MIT).
- Original gradient-optimization research: <https://github.com/kdrkdrkdr/supertonic.embed>
- This original website, workflow and bootstrapper source: MIT, see `LICENSE`.

Use only your own voice or one you have explicit authorization to clone. Do not use synthetic speech to deceive or impersonate others. The public website doesn't upload voice JSON for EXE creation; if you use the **private** audio-cloning API, it necessarily receives the uploaded recording. Treat voice data and embedding JSON as sensitive. The tool does not provide biometric consent verification.
