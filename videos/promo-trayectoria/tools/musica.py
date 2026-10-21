# Original background track for the promo: modern, sober electronic bed.
# Grid: 4 bars per 10.5 s scene (≈91.4 bpm); scene cuts land on bar lines.
import numpy as np, soundfile as sf, sys
# Scene durations must match SCENES in index.html (each is a whole number of bars).
SCENES = [6, 10.5, 15.75, 15.75, 15.75, 15.75, 10.5, 10.5, 10.5, 9]
sr = 44100
T = float(sum(SCENES))
n = int(sr * T)
t = np.arange(n) / sr
rng = np.random.default_rng(11)
BAR = 10.5 / 4
BEAT = BAR / 4
GRID0 = SCENES[0] - 4 * BAR  # bar lines at GRID0 + k*BAR; first cut on a bar line
CUTS = [sum(SCENES[: i + 1]) for i in range(len(SCENES) - 1)]  # scene cuts land on bar lines
END_DRUMS = CUTS[-1]  # drums stop when the closing scene starts

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)
def lowpass(x, fc, width=0.25):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / sr)
    X *= 1 / (1 + (f / fc) ** (2 / width * 0.25 * 8))
    return np.fft.irfft(X, len(x))
def highpass(x, fc):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / sr)
    X *= 1 - 1 / (1 + (f / fc) ** 4)
    return np.fft.irfft(X, len(x))

# Progression per scene: Am9 | Fmaj7 | C(add9) | G6
CHORDS = [[57, 60, 64, 67, 71], [53, 57, 60, 64, 69], [55, 60, 62, 64, 67], [55, 59, 62, 64, 67]]
ROOTS = [45, 41, 48, 43]
L = np.zeros(n); R = np.zeros(n)
def add(sig, start, gl=1.0, gr=1.0):
    s0 = int(start * sr)
    if s0 >= n: return
    if s0 < 0: sig = sig[-s0:]; s0 = 0
    e = min(n, s0 + len(sig)); L[s0:e] += sig[: e - s0] * gl; R[s0:e] += sig[: e - s0] * gr

bars = [GRID0 + k * BAR for k in range(int((T - GRID0) / BAR) + 2)]

# Pad: detuned saws, filtered, swelling per bar
pad = np.zeros(n)
for k, b0 in enumerate(bars):
    ch = CHORDS[k % 4]; ln = int((BAR + 1.2) * sr); tt = np.arange(ln) / sr
    env = np.minimum(1, tt / 0.6) * np.where(tt < BAR, 1, np.exp(-(tt - BAR) * 3))
    sig = sum(2 * ((hz(m) * (1 + d) * tt) % 1) - 1 for m in ch for d in (-0.003, 0.003))
    s0 = int(b0 * sr)
    if s0 >= n: continue
    if s0 < 0: sig, env, s0 = sig[-s0:], env[-s0:], 0
    e = min(n, s0 + len(sig)); pad[s0:e] += (sig * env)[: e - s0] * 0.02
pad = lowpass(pad, 1400)
L += pad; R += np.roll(pad, int(0.012 * sr))

# Pluck arpeggio (8ths) with ping-pong echo
pat = [0, 2, 4, 1, 3, 4, 2, 1]
for k, b0 in enumerate(bars):
    ch = CHORDS[k % 4]
    for i in range(8):
        st = b0 + i * BEAT / 2
        if st < 0 or st > T - 0.5: continue
        f = hz(ch[pat[i]] + 12); ln = int(0.5 * sr); tt = np.arange(ln) / sr
        sig = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) + 0.12 * np.sin(6 * np.pi * f * tt)) * np.exp(-tt * 9)
        g = 0.05 * (0.6 if st < CUTS[0] else 1.0)
        pan = 0.5 + 0.35 * np.sin(i * 1.1 + k)
        for rep, dl in enumerate([0, 3 * BEAT / 4, 6 * BEAT / 4]):
            gg = g * (0.45 ** rep)
            add(sig, st + dl, gg * (1 - pan if rep % 2 == 0 else pan), gg * (pan if rep % 2 == 0 else 1 - pan))

# Bass: pulsing 8ths with sidechain feel (from first cut until the outro)
for k, b0 in enumerate(bars):
    f = hz(ROOTS[k % 4] - 12)
    for i in range(8):
        st = b0 + i * BEAT / 2
        if st < CUTS[0] or st >= END_DRUMS: continue
        ln = int(BEAT / 2 * sr); tt = np.arange(ln) / sr
        env = np.minimum(1, tt / 0.03) * np.exp(-tt * 3) * (0.55 + 0.45 * np.minimum(1, tt / 0.12))
        sig = np.tanh(1.6 * (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(4 * np.pi * f * tt))) * env * 0.13
        add(sig, st)

# Drums
for k, b0 in enumerate(bars):
    for bt in range(4):
        st = b0 + bt * BEAT
        if st < CUTS[0] or st >= END_DRUMS: continue
        ln = int(0.35 * sr); tt = np.arange(ln) / sr
        kick = np.sin(2 * np.pi * (48 * tt + 70 * (1 - np.exp(-tt * 28)) / 28)) * np.exp(-tt * 9) * 0.32
        add(kick, st)
        if st >= CUTS[1] and bt in (1, 3):
            ln2 = int(0.25 * sr); t2 = np.arange(ln2) / sr
            clap = np.diff(rng.standard_normal(ln2 + 1)) * np.exp(-t2 * 22) * 0.035
            add(clap, st, 0.9, 1.0)
        if st >= CUTS[2]:
            for off in (BEAT / 2,):
                ln3 = int(0.06 * sr); t3 = np.arange(ln3) / sr
                hat = np.diff(np.diff(rng.standard_normal(ln3 + 2))) * np.exp(-t3 * 70) * 0.012
                add(hat, st + off, 0.7, 1.0)

# Transition swells on every scene cut + soft impact
for c in CUTS:
    ln = int(1.6 * sr); tt = np.arange(ln) / sr
    sw = highpass(rng.standard_normal(ln), 600) * (tt / 1.6) ** 3 * np.where(tt < 1.4, 1, np.exp(-(tt - 1.4) * 25)) * 0.05
    add(sw, c - 1.4, 1.0, 0.8)
    add(sw[::-1] * 0.4, c - 0.05, 0.8, 1.0)
ln = int(3 * sr); tt = np.arange(ln) / sr
add(np.sin(2 * np.pi * (38 * tt + 40 * (1 - np.exp(-tt * 12)) / 12)) * np.exp(-tt * 1.8) * 0.4, END_DRUMS)

# Master
mix = np.stack([L, R], 1)
mix = np.tanh(mix * 1.4) / 1.4
fade = np.ones(n)
fade[: int(1.2 * sr)] = np.linspace(0, 1, int(1.2 * sr))
fade[-int(3.5 * sr):] *= np.linspace(1, 0, int(3.5 * sr)) ** 1.5
mix *= fade[:, None]
mix /= np.max(np.abs(mix)) / 0.89
sf.write(sys.argv[1], mix.astype(np.float32), sr)
