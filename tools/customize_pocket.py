"""Brand pinned Pocket Voice as tbenitz's Pocket TTS-only clipboard studio.

Executed after the MIT Pocket Voice upstream is copied into web/pocket.
Keep original upstream attribution in ATTRIBUTION.txt.
"""
from pathlib import Path

base = Path("web/pocket")
html_file = base / "index.html"
app_file = base / "app.js"
html = html_file.read_text(encoding="utf-8")
app = app_file.read_text(encoding="utf-8")

def change(old, new):
    global html
    if old not in html:
        raise RuntimeError("Upstream Pocket template changed, cannot find: " + old[:65])
    html = html.replace(old, new)

change("Pocket Voice — Clone any voice in your browser", "tbenitz · Pocket TTS Voice Studio")
change('<meta name="theme-color" content="#050504">', '<meta name="theme-color" content="#080e1c">')
change('<meta name="author" content="Hemanth HM">', '<meta name="author" content="tbenitz">')
change('href="/ai/pocket-voice/favicon.svg"', 'href="./favicon.svg"')
change('href="/ai/pocket-voice/og-image.png"', 'href="./favicon.svg"')
change('content="https://h3manth.com/ai/pocket-voice/og-image.png"', 'content="./favicon.svg"')
change('<meta name="twitter:creator" content="@anthropic">', '<meta name="twitter:creator" content="@tbenitz">')
change('"name": "Pocket Voice",', '"name": "tbenitz Pocket TTS Voice Studio",')
change('"creator": { "@type": "Person", "name": "Hemanth HM", "url": "https://h3manth.com" }',
       '"creator": { "@type": "Person", "name": "tbenitz", "url": "https://github.com/tbenitz" }')
change('<link rel="stylesheet" href="style.css?v=2.0.9">',
       '<link rel="stylesheet" href="style.css?v=2.0.9">\n<link rel="stylesheet" href="./pocket-theme.css">')
change('Clone any voice.<br><em>In your browser.</em>', 'Your voice. Your clipboard.<br><em>Entirely on-device.</em>')
change('<h2 class="app-section__title">Voice Studio</h2>',
       '<h2 class="app-section__title">Pocket TTS Voice Studio</h2>')
change('Clone a voice, select a preset, type text, generate.',
       'Choose a voice, generate and listen to an example, then export your Windows clipboard reader.')
change('Built with ❤️ by <a href="https://h3manth.com" target="_blank" rel="noopener">Hemanth HM</a> · Powered by <a href="https://github.com/kyutai-labs/pocket-tts" target="_blank" rel="noopener">Pocket TTS</a>',
       'Created by <a href="https://github.com/tbenitz" target="_blank" rel="noopener">tbenitz</a> · Powered by Kyutai Pocket TTS · <a href="./ATTRIBUTION.txt">Open-source credits</a>')
change('<script type="module" src="app.js?v=2.0.9"></script>',
       '<script type="module" src="app.js?v=2.0.9"></script>\n<script src="./pocket-export.js" type="module"></script>')
if "new PocketVoice();" not in app:
    raise RuntimeError("Pocket app bootstrap changed: cannot expose instance")
app = app.replace("new PocketVoice();", "window.__pocketApp = new PocketVoice();")
html_file.write_text(html, encoding="utf-8")
app_file.write_text(app, encoding="utf-8")
print("Applied tbenitz branding, cyan theme, and Pocket EXE export UI")
