using System;
using System.Buffers.Binary;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;

static class Program
{
    [DllImport("user32.dll", SetLastError = true)] private static extern bool OpenClipboard(IntPtr hWndNewOwner);
    [DllImport("user32.dll", SetLastError = true)] private static extern bool CloseClipboard();
    [DllImport("user32.dll")] private static extern IntPtr GetClipboardData(uint uFormat);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern IntPtr GlobalLock(IntPtr hMem);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool GlobalUnlock(IntPtr hMem);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern int MessageBoxW(IntPtr hWnd, string text, string caption, uint type);
    const uint CF_UNICODETEXT = 13;
    static string ReadClipboard()
    {
        // Capture at process start, BEFORE any model download or engine extraction.
        for (int i = 0; i < 12; i++)
        {
            if (OpenClipboard(IntPtr.Zero))
            {
                try
                {
                    var handle = GetClipboardData(CF_UNICODETEXT);
                    if (handle == IntPtr.Zero) return string.Empty;
                    var ptr = GlobalLock(handle);
                    if (ptr == IntPtr.Zero) return string.Empty;
                    try { return Marshal.PtrToStringUni(ptr) ?? string.Empty; }
                    finally { GlobalUnlock(handle); }
                }
                finally { CloseClipboard(); }
            }
            Thread.Sleep(40);
        }
        return string.Empty;
    }
    static bool ReadFooter(FileStream fs, ref long end, string marker, out long start, out long length)
    {
        start = 0; length = 0;
        if (end < 16) return false;
        Span<byte> tail = stackalloc byte[16];
        fs.Position = end - 16;
        fs.ReadExactly(tail);
        if (Encoding.ASCII.GetString(tail.Slice(0,8)) != marker) return false;
        ulong n = BinaryPrimitives.ReadUInt64LittleEndian(tail.Slice(8,8));
        if (n > (ulong)(end - 16)) throw new InvalidDataException("Invalid bundle length");
        length = (long)n;
        start = end - 16 - length;
        end = start;
        return true;
    }
    static void CopyRange(FileStream src, long start, long len, Stream dst)
    {
        src.Position = start;
        byte[] buf = new byte[1024 * 1024];
        while (len > 0)
        {
            var n = src.Read(buf, 0, (int)Math.Min(buf.Length, len));
            if (n == 0) throw new EndOfStreamException();
            dst.Write(buf, 0, n);
            len -= n;
        }
    }
    static string HashRange(FileStream fs, long start, long len)
    {
        using var h = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        fs.Position = start;
        byte[] buf = new byte[1024 * 1024];
        while (len > 0)
        {
            int n = fs.Read(buf, 0, (int)Math.Min(buf.Length, len));
            if (n == 0) throw new EndOfStreamException();
            h.AppendData(buf, 0, n);
            len -= n;
        }
        return Convert.ToHexString(h.GetHashAndReset()).Substring(0, 16);
    }
    static void Main()
    {
        var clipboard = ReadClipboard();
        if (string.IsNullOrWhiteSpace(clipboard)) return;
        if (clipboard.Length > 250_000)
        {
            MessageBoxW(IntPtr.Zero, "Clipboard exceeds the 250,000 character safety limit.", "Clipboard Voice", 0x10);
            return;
        }
        try
        {
            var exe = Environment.ProcessPath ?? throw new Exception("Cannot locate executable");
            using var fs = File.Open(exe, FileMode.Open, FileAccess.Read, FileShare.Read);
            long end = fs.Length;
            string configJson = "{\"voice\":\"M1\",\"lang\":\"en\",\"speed\":1.05,\"steps\":8}";
            if (ReadFooter(fs, ref end, "CVRCFG01", out var configStart, out var configLen))
            {
                if (configLen > 8_000_000) throw new InvalidDataException("Voice config is too large");
                byte[] bytes = new byte[(int)configLen];
                fs.Position = configStart;
                fs.ReadExactly(bytes);
                configJson = Encoding.UTF8.GetString(bytes);
            }
            if (!ReadFooter(fs, ref end, "CVRZIP01", out var zipStart, out var zipLen))
                throw new InvalidDataException("Reading engine is missing. Download a fresh EXE.");
            var root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ClipboardVoiceStudio");
            Directory.CreateDirectory(root);
            string digest = HashRange(fs, zipStart, zipLen);
            string runtime = Path.Combine(root, "runtime-" + digest);
            string engine = Path.Combine(runtime, "reader.exe");
            if (!File.Exists(engine))
            {
                string extracting = runtime + "-partial-" + Guid.NewGuid().ToString("N");
                Directory.CreateDirectory(extracting);
                try
                {
                    string zipPath = Path.Combine(extracting, "runtime.zip");
                    using (var outZip = File.Create(zipPath)) CopyRange(fs, zipStart, zipLen, outZip);
                    ZipFile.ExtractToDirectory(zipPath, extracting, overwriteFiles: true);
                    File.Delete(zipPath);
                    if (!File.Exists(Path.Combine(extracting, "reader.exe"))) throw new InvalidDataException("Engine bundle incomplete");
                    try { Directory.Move(extracting, runtime); }
                    catch (IOException) when (File.Exists(engine)) { Directory.Delete(extracting, recursive: true); }
                }
                catch { if (Directory.Exists(extracting)) Directory.Delete(extracting, true); throw; }
            }
            var job = Path.Combine(root, "job-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(job);
            try
            {
                var inputPath = Path.Combine(job, "clipboard.txt");
                File.WriteAllText(inputPath, clipboard, Encoding.UTF8);
                var configPath = Path.Combine(job, "profile.json");
                using var doc = JsonDocument.Parse(configJson);
                var cfg = doc.RootElement;
                var voice = cfg.TryGetProperty("voice", out var pVoice) ? (pVoice.GetString() ?? "M1") : "M1";
                var lang = cfg.TryGetProperty("lang", out var pLang) ? (pLang.GetString() ?? "en") : "en";
                var speed = cfg.TryGetProperty("speed", out var pSpeed) ? pSpeed.GetDouble() : 1.05;
                var steps = cfg.TryGetProperty("steps", out var pSteps) ? pSteps.GetInt32() : 8;
                var engineMode = cfg.TryGetProperty("engine", out var pEngine) && pEngine.GetString() == "pocket" ? "pocket" : "supertonic";
                string? pocketVoicePath = null;
                if (engineMode == "pocket")
                {
                    if (!cfg.TryGetProperty("voice_wav_b64", out var pAudio)) throw new InvalidDataException("Pocket reference recording is missing");
                    var audio = Convert.FromBase64String(pAudio.GetString() ?? "");
                    if (audio.Length < 44 || audio.Length > 5_000_000 || Encoding.ASCII.GetString(audio, 0, 4) != "RIFF" || Encoding.ASCII.GetString(audio, 8, 4) != "WAVE")
                        throw new InvalidDataException("Invalid Pocket WAV recording");
                    pocketVoicePath = Path.Combine(job, "voice.wav");
                    File.WriteAllBytes(pocketVoicePath, audio);
                }
                string? customStyle = null;
                if (cfg.TryGetProperty("style", out var style) && style.ValueKind == JsonValueKind.Object)
                {
                    customStyle = Path.Combine(job, "voice.json");
                    File.WriteAllText(customStyle, style.GetRawText(), Encoding.UTF8);
                }
                File.WriteAllText(configPath, JsonSerializer.Serialize(new ReaderProfile
                {
                    Voice = voice, Language = lang, Speed = speed, Steps = steps, StylePath = customStyle, Engine = engineMode, VoicePath = pocketVoicePath
                }, ReaderProfileJsonContext.Default.ReaderProfile), Encoding.UTF8);
                using var process = Process.Start(new ProcessStartInfo
                {
                    FileName = engine,
                    ArgumentList = { "--input-file", inputPath, "--config-file", configPath },
                    WorkingDirectory = runtime,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                }) ?? throw new Exception("Could not start reading engine");
                process.WaitForExit(); // reader.exe exits only after audio really ends (or Stop).
            }
            finally { try { Directory.Delete(job, recursive: true); } catch { } }
        }
        catch (Exception ex)
        {
            MessageBoxW(IntPtr.Zero, ex.Message, "Clipboard Voice - Error", 0x10);
        }
    }
}

internal sealed class ReaderProfile
{
    [JsonPropertyName("engine")] public string Engine { get; set; } = "supertonic";
    [JsonPropertyName("voice_path")] public string? VoicePath { get; set; }
    [JsonPropertyName("voice")] public string Voice { get; set; } = "M1";
    [JsonPropertyName("lang")] public string Language { get; set; } = "en";
    [JsonPropertyName("speed")] public double Speed { get; set; } = 1.05;
    [JsonPropertyName("steps")] public int Steps { get; set; } = 8;
    [JsonPropertyName("style_path")] public string? StylePath { get; set; }
}

[JsonSerializable(typeof(ReaderProfile))]
internal partial class ReaderProfileJsonContext : JsonSerializerContext { }
