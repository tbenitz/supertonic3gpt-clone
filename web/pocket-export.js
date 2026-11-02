/* Supertonic3GPT Clone — Pocket-only clipboard executable export.
   Uses the same cloned PCM the live ONNX demo encodes; never uploads voice data. */
(() => {
  'use strict';
  const app = window.__pocketApp;
  if (!app) { console.error('Pocket TTS app not initialized'); return; }
  const html = String.raw`<section class="export-panel panel" id="export-panel" aria-label="Windows clipboard reader export">
      <div class="export-panel__head"><span class="export-panel__step">03 · EXPORT</span><span class="export-panel__pill">Windows 10/11 · x64</span></div>
      <h2>Make your clipboard talk.</h2>
      <p>Record or upload your own voice above, type a short example and press <strong>Generate Audio</strong>. Listen to your cloned voice here before creating the Windows executable.</p>
      <div class="export-panel__grid">
        <div class="export-panel__check">1 <span>Clone a voice</span></div>
        <div class="export-panel__check">2 <span>Generate &amp; hear a sample</span></div>
        <div class="export-panel__check">3 <span>Download your EXE</span></div>
      </div>
      <label class="export-panel__consent"><input id="export-consent" type="checkbox"> I own the reference voice or have the speaker's permission to clone it.</label>
      <button type="button" id="export-reader" class="btn-primary export-panel__download" disabled>Download personalized ClipboardVoice.exe</button>
      <div id="export-status" class="export-panel__status" role="status" aria-live="polite">Clone your voice and listen to a generated example first to unlock export.</div>
      <p class="export-panel__fine">The sample and personal voice profile stay in your browser. The EXE contains your reference audio, not a recording uploaded to GitHub. The speech model downloads once on the Windows PC. Windows may warn about unsigned executables.</p>
    </section>`;
  const section = document.querySelector('#app .container');
  if (!section) throw Error('Pocket studio layout not found');
  section.insertAdjacentHTML('beforeend', html);
  const button = document.getElementById('export-reader');
  const consent = document.getElementById('export-consent');
  const status = document.getElementById('export-status');
  const setStatus = (message, error = false) => {
    status.textContent = message;
    status.classList.toggle('is-error', error);
  };
  let clonedSerial = 0, auditionedSerial = -1, previewStartedSerial = -1;
  function eligible() {
    return !!app.lastClonedPCM && app.lastClonedPCM.length >= 24000 * 3 &&
      app.activeVoice === 'custom' && app.el.voiceSelect.value === 'custom' &&
      auditionedSerial === clonedSerial && consent.checked && !app.isGenerating;
  }
  function updateButton() { button.disabled = !eligible(); }
  const processOriginal = app.processVoiceClip.bind(app);
  app.processVoiceClip = async (...args) => {
    clonedSerial++;
    auditionedSerial = -1;
    updateButton();
    setStatus('Extracting the cloned voice locally. Then type an example and select Generate Audio.');
    return processOriginal(...args);
  };
  const loadSavedOriginal = app.loadSavedVoice.bind(app);
  app.loadSavedVoice = async (...args) => {
    clonedSerial++;
    auditionedSerial = -1;
    updateButton();
    setStatus('Saved voice loaded. Generate and listen to a new sample before export.');
    return loadSavedOriginal(...args);
  };
  const generateOriginal = app.generate.bind(app);
  app.generate = async (...args) => {
    previewStartedSerial = app.activeVoice === 'custom' && app.el.voiceSelect.value === 'custom' ?
      clonedSerial : -1;
    auditionedSerial = -1;
    updateButton();
    if (previewStartedSerial >= 0) setStatus('Generating your example with Pocket TTS locally. Listen through to the end.');
    return generateOriginal(...args);
  };
  const finalizeOriginal = app.finalizePlayback.bind(app);
  app.finalizePlayback = (...args) => {
    const valid = app.currentChunks.length > 0 &&
      app.activeVoice === 'custom' && app.el.voiceSelect.value === 'custom' &&
      previewStartedSerial === clonedSerial && !!app.lastClonedPCM;
    const result = finalizeOriginal(...args);
    if (valid) {
      auditionedSerial = clonedSerial;
      setStatus('Example finished. Tick the permission box to download the personalized Windows reader.');
    }
    updateButton();
    return result;
  };
  const stopOriginal = app.stop.bind(app);
  app.stop = (...args) => {
    auditionedSerial = -1;
    previewStartedSerial = -1;
    updateButton();
    setStatus('Playback stopped. Generate and finish another example before exporting.');
    return stopOriginal(...args);
  };
  consent.addEventListener('change', updateButton);
  app.el.voiceSelect.addEventListener('change', updateButton);
  // Studio voice-gallery choices are managed by worker events; re-check when updated.
  const workerOriginal = app.handleWorkerMessage.bind(app);
  app.handleWorkerMessage = (msg) => { const value = workerOriginal(msg); updateButton(); return value; };
  function encodeBase64(arrayBuffer) {
    const bytes = new Uint8Array(arrayBuffer);
    const pieces = [];
    for (let i = 0; i < bytes.length; i += 32768) {
      pieces.push(String.fromCharCode(...bytes.subarray(i, i + 32768)));
    }
    return btoa(pieces.join(''));
  }
  function saveFile(blob, name) {
    const url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = name;
    document.body.appendChild(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  }
  button.addEventListener('click', async () => {
    if (!eligible()) { setStatus('Clone a voice, finish a sample and confirm permission before export.', true); return; }
    button.disabled = true;
    try {
      const pcm = app.lastClonedPCM;
      if (pcm.length > 24000 * 12) throw Error('Voice reference is too long to embed.');
      const wav = app.float32ToWav(pcm, 24000);
      const lang = app.el.langSelect.value;
      const allowed = new Set(['english_2026-04','english','german','italian','portuguese','spanish']);
      if (!allowed.has(lang)) throw Error('Unsupported Windows voice language. Choose one from the language menu.');
      const profile = {
        engine: 'pocket',
        lang,
        voice_wav_b64: encodeBase64(wav)
      };
      const payload = new TextEncoder().encode(JSON.stringify(profile));
      if (payload.byteLength > 8000000) throw Error('Embedded voice profile too large.');
      setStatus('Checking the latest published Windows build…');
      const infoReply = await fetch('../download/build-info.json', {cache: 'no-store'});
      if (!infoReply.ok) throw Error('Build verification file is missing; wait for the updated GitHub Pages deployment.');
      const info = await infoReply.json();
      if (info.architecture !== 'windows-x64' || !/^[a-f0-9]{64}$/i.test(info.sha256)) {
        throw Error('Invalid EXE build metadata. Refusing to download.');
      }
      setStatus('Downloading Windows reader engine (' + info.revision + ')…');
      const r = await fetch('../download/ClipboardReader-Base.exe', {cache: 'no-store'});
      if (!r.ok) throw Error('Windows engine is not published. Check GitHub Actions (HTTP ' + r.status + ').');
      const engine = await r.blob();
      if (engine.size !== info.size || engine.size < 500000) {
        throw Error('Incomplete Windows EXE download. Expected ' + info.size + ' bytes; received ' + engine.size + '.');
      }
      setStatus('Verifying downloaded Windows EXE SHA-256…');
      const binary = await engine.arrayBuffer();
      const view = new DataView(binary);
      const data = new Uint8Array(binary);
      const ascii = (offset, len) => new TextDecoder('ascii').decode(data.subarray(offset, offset + len));
      if (ascii(0, 2) !== 'MZ') throw Error('Windows executable header is missing.');
      const peOffset = view.getUint32(0x3c, true);
      if (peOffset < 64 || peOffset + 6 > data.length || ascii(peOffset, 4) !== 'PE\\0\\0'.replace(/\\0/g, String.fromCharCode(0))) {
        throw Error('The downloaded file has an invalid Windows PE signature.');
      }
      if (view.getUint16(peOffset + 4, true) !== 0x8664) {
        throw Error('The Windows executable is not x64.');
      }
      if (ascii(data.length - 16, 8) !== 'CVRZIP01') throw Error('The Windows engine ZIP bundle is missing.');
      const zipSize = Number(view.getBigUint64(data.length - 8, true));
      const zipStart = data.length - 16 - zipSize;
      if (zipSize < 1000000 || zipStart < 1024 || ascii(zipStart, 2) !== 'PK') {
        throw Error('The bundled reader is truncated or corrupted.');
      }
      const digest = await crypto.subtle.digest('SHA-256', binary);
      const actualHash = Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2,'0')).join('');
      if (actualHash !== info.sha256.toLowerCase()) {
        throw Error('The EXE integrity check failed. Reload the site and export again.');
      }
      setStatus('Verified Windows EXE build ' + info.revision + '; embedding your voice…');
      const footer = new Uint8Array(16);
      footer.set(new TextEncoder().encode('CVRCFG01'));
      new DataView(footer.buffer).setBigUint64(8, BigInt(payload.byteLength), true);
      setStatus('Embedding your voice into the executable locally…');
      saveFile(new Blob([engine, payload, footer], {type:'application/octet-stream'}), 'ClipboardVoice-' + info.revision + '.exe');
      setStatus('Verified EXE (' + info.revision + ') downloaded. Test it from the Windows Desktop, not directly in Shared.');
    } catch (e) {
      setStatus('Export failed: ' + (e.message || String(e)), true);
    } finally { updateButton(); }
  });
  setStatus('Clone your voice and generate a short example above. After it finishes playing, export becomes available.');
})();
