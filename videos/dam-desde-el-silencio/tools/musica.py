# Original dark metal bed for the DAM "Desde el silencio" spot (25 s).
# Silence/drone -> heartbeat -> heavy hits on the title -> full riff -> ring-out.
import numpy as np, soundfile as sf, sys
sr = 44100; T = 25.0; n = int(sr * T); t = np.arange(n) / sr
rng = np.random.default_rng(3)
L = np.zeros(n); R = np.zeros(n)
def hz(m): return 440 * 2 ** ((m - 69) / 12)
def add(sig, at, gl=1.0, gr=1.0):
    s0 = int(at * sr)
    if s0 >= n: return
    e = min(n, s0 + len(sig)); L[s0:e] += sig[: e - s0] * gl; R[s0:e] += sig[: e - s0] * gr
def lowpass(x, fc):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / sr); X /= (1 + (f / fc) ** 4); return np.fft.irfft(X, len(x))
def highpass(x, fc):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / sr); X *= 1 - 1 / (1 + (f / fc) ** 4); return np.fft.irfft(X, len(x))
# Drone: low D, dark and slowly swelling
drone = sum(np.sin(2 * np.pi * hz(m) * t + 0.3 * np.sin(2 * np.pi * 0.1 * t)) for m in (26, 38, 45))
drone = drone * np.clip(t / 3.0, 0, 1) * 0.06
L += drone; R += np.roll(drone, 300)
# Wind/air noise
air = lowpass(rng.standard_normal(n), 900) * 0.05 * np.clip(t / 2, 0, 1)
L += air; R += np.roll(air, 900)
# Heartbeat kicks 1.5–6 s
for at in np.arange(1.5, 6.2, 1.0):
    for d, g in ((0, 0.5), (0.22, 0.3)):
        ln = int(0.3 * sr); tt = np.arange(ln) / sr
        add(np.sin(2 * np.pi * (40 * tt + 50 * (1 - np.exp(-tt * 25)) / 25)) * np.exp(-tt * 10) * g, at + d)
# Distorted power chord (D5) and riff
def chord(root, dur, gain):
    ln = int(dur * sr); tt = np.arange(ln) / sr
    x = sum(2 * ((hz(root + iv) * (1 + det) * tt) % 1) - 1 for iv in (0, 7, 12) for det in (-0.004, 0.004))
    x = np.tanh(x * 3.5) * np.minimum(1, tt / 0.01) * np.exp(-tt * 0.6) * gain
    return lowpass(x, 3200)
def hit(at, root=38, dur=2.2, g=0.22):
    c = chord(root, dur, g); add(c, at, 1.0, 0.92); add(c, at + 0.012, 0.9, 1.0)
    ln = int(1.6 * sr); tt = np.arange(ln) / sr
    add(np.sin(2 * np.pi * (34 * tt + 60 * (1 - np.exp(-tt * 20)) / 20)) * np.exp(-tt * 3) * 0.6, at)
    add(highpass(rng.standard_normal(int(2.5 * sr)), 4000) * np.exp(-np.arange(int(2.5 * sr)) / sr * 1.6) * 0.09, at)
# Reverse swells before the hits
def swell(end, dur=1.4):
    ln = int(dur * sr); tt = np.arange(ln) / sr
    add(highpass(rng.standard_normal(ln), 1500) * (tt / dur) ** 3 * 0.12, end - dur)
for at in (7.0, 11.0, 13.0, 15.0):
    swell(at); hit(at)
# Riff 16–23 s: chugging D with accents, double kick
riff = [38, 38, 41, 38, 43, 41, 38, 36]
bpm = 140; e8 = 60 / bpm / 2
for k, at in enumerate(np.arange(16.0, 23.0, e8)):
    root = riff[(k // 2) % len(riff)]
    c = chord(root, e8 * 0.95, 0.16 if k % 2 else 0.2); add(c, at, 1.0, 0.9); add(c, at + 0.01, 0.9, 1.0)
    ln = int(0.18 * sr); tt = np.arange(ln) / sr
    add(np.sin(2 * np.pi * (45 * tt + 60 * (1 - np.exp(-tt * 30)) / 30)) * np.exp(-tt * 18) * 0.45, at)
    if k % 4 == 2:
        ln2 = int(0.25 * sr); t2 = np.arange(ln2) / sr
        add(highpass(rng.standard_normal(ln2), 900) * np.exp(-t2 * 16) * 0.18, at)
hit(23.0, dur=2.0, g=0.24)
mix = np.stack([L, R], 1); mix = np.tanh(mix * 1.3) / 1.3
fade = np.ones(n); fade[-int(1.2 * sr):] = np.linspace(1, 0, int(1.2 * sr)); mix *= fade[:, None]
mix /= np.max(np.abs(mix)) / 0.89
sf.write(sys.argv[1], mix.astype(np.float32), sr)
