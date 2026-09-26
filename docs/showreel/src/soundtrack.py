"""Soundtrack for the showreel: an original 128 BPM chiptune/electro cue, synthesized from scratch.

8 bars of 4/4 = exactly 15.0 s. Every hit and whoosh sits on the same frame-rounded beat grid
as showreel.html (see b() below), so picture and sound stay locked.

    python3 docs/showreel/src/soundtrack.py out.wav        (needs numpy + scipy)
"""
import sys
import wave

import numpy as np
from scipy import signal

SR = 48000
DUR = 15.0
N = int(SR * DUR)
BT = 60 / 128
FPS = 60
RNG = np.random.default_rng(128)


def b(n):
    """Beat number -> seconds, rounded to a video frame exactly like the animation."""
    return round(n * BT * FPS) / FPS


# ---------------------------------------------------------------- building blocks
def secs(d):
    return np.arange(int(d * SR)) / SR


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def noise(n):
    return RNG.uniform(-1, 1, n)


def sos_filter(x, kind, f, order=2):
    nyq = SR / 2
    if kind == 'band':
        sos = signal.butter(order, [f[0] / nyq, min(f[1] / nyq, .99)], 'bandpass', output='sos')
    else:
        sos = signal.butter(order, min(f / nyq, .99), kind, output='sos')
    return signal.sosfilt(sos, x)


def lp(x, f, order=2):
    return sos_filter(x, 'lowpass', f, order)


def hp(x, f, order=2):
    return sos_filter(x, 'highpass', f, order)


def bp(x, lo, hi, order=2):
    return sos_filter(x, 'band', (lo, hi), order)


def sweep_bp(x, f0, f1, q=2.0, block=256):
    """Band-pass whose centre glides from f0 to f1 (exponentially), block by block."""
    out = np.zeros_like(x)
    zi = None
    nb = max(1, len(x) // block)
    for k in range(nb + 1):
        s, e = k * block, min(len(x), (k + 1) * block)
        if s >= e:
            break
        fc = f0 * (f1 / f0) ** (s / max(1, len(x) - 1))
        bw = fc / q
        lo, hi = max(20, fc - bw / 2), min(SR / 2 * .95, fc + bw / 2)
        sos = signal.butter(2, [lo / (SR / 2), hi / (SR / 2)], 'bandpass', output='sos')
        if zi is None:
            zi = signal.sosfilt_zi(sos) * 0
        out[s:e], zi = signal.sosfilt(sos, x[s:e], zi=zi)
    return out


def blep(p, dt):
    y = np.zeros_like(p)
    m = p < dt
    x = p[m] / dt[m]
    y[m] = x + x - x * x - 1
    m = p > 1 - dt
    x = (p[m] - 1) / dt[m]
    y[m] = x * x + x + x + 1
    return y


def saw(f):
    dt = f / SR
    p = np.cumsum(dt) % 1.0
    return 2 * p - 1 - blep(p, dt)


def pulse(f, duty=.5):
    dt = f / SR
    p = np.cumsum(dt) % 1.0
    y = np.where(p < duty, 1.0, -1.0)
    return y + blep(p, dt) - blep((p - duty) % 1.0, dt) - (2 * duty - 1)


def sine(f):
    return np.sin(2 * np.pi * np.cumsum(f / SR))


def env(n, a=.004, d=.1, s=.6, r=.05, gate=None):
    """ADSR over n samples; gate = seconds the note is held (defaults to n minus release)."""
    t = np.arange(n) / SR
    g = gate if gate is not None else n / SR - r
    e = np.where(t < a, t / max(a, 1e-6), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-6)))
    rel = np.clip((t - g) / max(r, 1e-6), 0, 1)
    return e * (1 - rel)


def decay(n, tau):
    return np.exp(-np.arange(n) / SR / tau)


class Bus:
    def __init__(self):
        self.x = np.zeros((2, N))

    def add(self, y, t0, gain=1.0, pan=0.0):
        i0 = int(round(t0 * SR))
        if y.ndim == 1:
            a = (pan + 1) * np.pi / 4
            y = np.stack([y * np.cos(a), y * np.sin(a)]) * np.sqrt(2)
        if i0 < 0:
            y = y[:, -i0:]
            i0 = 0
        n = min(y.shape[1], N - i0)
        if n > 0:
            self.x[:, i0:i0 + n] += gain * y[:, :n]


# ---------------------------------------------------------------- drums
def kick(f0=170, f1=46, tau=.22):
    t = secs(.55)
    f = f1 + (f0 - f1) * np.exp(-t / .03)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / tau)
    click = hp(noise(len(t)), 2000) * np.exp(-t / .003) * .6
    return np.tanh(1.8 * (body + click)) / np.tanh(1.8)


def clap():
    t = secs(.4)
    e = sum(np.exp(-np.clip(t - o, 0, None) / .006) * (t >= o) for o in (0, .011, .023)) * .6
    e += np.exp(-t / .11) * .7
    return bp(noise(len(t)), 900, 3200) * e * 1.4


def snare():
    t = secs(.3)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t / .07)
    rattle = bp(noise(len(t)), 1200, 9000) * np.exp(-t / .12)
    return .7 * tone + rattle


def hat(open_=False):
    t = secs(.25 if open_ else .08)
    return lp(hp(noise(len(t)), 7000, 4), 12000) * np.exp(-t / (.07 if open_ else .02))


def crash(d=2.2):
    t = secs(d)
    metal = sum(np.sin(2 * np.pi * f * t + RNG.uniform(0, 6)) for f in (3120, 4480, 5230, 6720, 8110)) / 5
    return lp(hp(noise(len(t)), 3500) * .9 + metal * .25, 9000) * np.exp(-t / .5)


# ---------------------------------------------------------------- synths
def bass_note(m, dur):
    n = int((dur + .03) * SR)
    f = np.full(n, mtof(m))
    raw = .6 * saw(f) + .4 * pulse(f, .5)
    body = lp(raw, 380)
    pluck = lp(raw, 1800) * decay(n, .05)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * .4
    return (body + .6 * pluck + sub) * env(n, .003, .08, .8, .03, gate=dur)


def lead_note(m, dur, duty=.25):
    n = int((dur + .08) * SR)
    t = np.arange(n) / SR
    vib = 1 + .006 * np.sin(2 * np.pi * 5.6 * t) * np.clip((t - .12) / .1, 0, 1)
    f = mtof(m) * vib
    x = .65 * pulse(f, duty) + .35 * pulse(f * 1.004, .5)
    return lp(x, 5200) * env(n, .004, .15, .72, .07, gate=dur)


def arp_note(m, dur=.1):
    n = int(dur * SR)
    return lp(pulse(np.full(n, mtof(m)), .125), 6500) * decay(n, .05)


def pad_chord(ms, dur, cutoff=2600):
    n = int((dur + .25) * SR)
    x = np.zeros(n)
    for m in ms:
        for dc in (-.12, -.05, 0, .05, .12):
            x += saw(np.full(n, mtof(m + dc)))
    x /= len(ms) * 5
    return lp(x, cutoff, 2) * env(n, .02, .3, .85, .25, gate=dur)


def bell(m, tau=.6):
    t = secs(tau * 4)
    f = mtof(m)
    return sum(a * np.sin(2 * np.pi * f * k * t) * np.exp(-t / (tau / k ** .5)) for k, a in ((1, 1), (2.76, .45), (5.4, .25), (8.93, .12)))


# ---------------------------------------------------------------- sound effects
def whoosh(d, f0, f1, q=1.6):
    x = sweep_bp(noise(int(d * SR)), f0, f1, q)
    t = np.linspace(0, 1, len(x))
    return x * np.sin(np.pi * t) ** 1.5 * 2.2


def riser(d, f0=300, f1=5000):
    n = int(d * SR)
    t = np.linspace(0, 1, n)
    x = sweep_bp(noise(n), f0, f1, 2.5) * t ** 2 * 2
    tone = np.sin(2 * np.pi * np.cumsum(200 * (8 ** t)) / SR) * t ** 3 * .35
    return x + tone


def impact(big=1.0):
    t = secs(1.6)
    f = 42 + 70 * np.exp(-t / .1)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (.4 * big))
    crack = lp(noise(len(t)), 4000) * np.exp(-t / .07)
    return np.tanh(1.4 * (boom + .6 * crack))


def tick(freq=2200, d=.018):
    t = secs(d)
    return np.sin(2 * np.pi * freq * t) * np.exp(-t / (d / 3))


def blip(m, d=.07, duty=.5):
    n = int(d * SR)
    return pulse(np.full(n, mtof(m)), duty) * decay(n, d / 3)


def metal_clank(base=420, tau=.35):
    t = secs(tau * 3)
    x = sum(a * np.sin(2 * np.pi * base * r * t) for r, a in ((1, 1), (2.43, .7), (4.1, .45), (6.7, .3)))
    return (x * .35 + hp(noise(len(t)), 2500) * np.exp(-t / .01)) * np.exp(-t / tau)


def pop(f0=900, f1=280, d=.08):
    t = secs(d)
    f = f1 + (f0 - f1) * np.exp(-t / .015)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .03)


def flame(d):
    n = int(d * SR)
    t = np.linspace(0, 1, n)
    roar = lp(noise(n), 1400) * 1.4 + bp(noise(n), 300, 2600) * .8
    flutter = 1 + .35 * np.sin(2 * np.pi * 23 * np.arange(n) / SR) * np.sin(2 * np.pi * 7 * np.arange(n) / SR)
    crackle = np.zeros(n)
    idx = RNG.integers(0, n, 90)
    crackle[idx] = RNG.uniform(-1, 1, 90)
    crackle = hp(crackle, 3000) * 3
    return (roar * flutter + crackle) * (np.minimum(1, t * 6)) * (1 - t ** 4)


def glitch(d):
    n = int(d * SR)
    out = np.zeros(n)
    i = 0
    while i < n:
        seg_n = int(RNG.uniform(.006, .02) * SR)
        m = RNG.integers(60, 96)
        out[i:i + seg_n] = pulse(np.full(min(seg_n, n - i), mtof(m)), .25) * RNG.uniform(.3, 1)
        i += seg_n
    return lp(out, 7000) * np.hanning(n) ** .3


# ---------------------------------------------------------------- the score
CHORDS = {  # bar (0-based) -> list of (start beat, chord tones, bass root)
    'Am': ([57, 60, 64, 69, 72], 33), 'F': ([53, 57, 60, 65, 69], 29),
    'C': ([55, 60, 64, 67, 72], 36), 'G': ([55, 59, 62, 67, 71], 31),
}
PROG = [(4, 'Am', 4), (8, 'F', 4), (12, 'C', 4), (16, 'G', 4), (20, 'Am', 4), (24, 'F', 2), (26, 'G', 2)]
LEAD = [  # (beat, midi, beats)
    (4, 69, 1), (5, 76, 1), (6, 74, .5), (6.5, 72, .5), (7, 76, 1),
    (8, 77, 1.5), (9.5, 76, .5), (10, 72, 1), (11, 69, 1),
    (12, 67, 1), (13, 72, 1), (14, 76, .5), (14.5, 74, .5), (15, 72, 1),
    (16, 79, .5), (16.5, 79, .5), (17, 74, .5), (17.5, 79, .5), (18, 81, .5), (18.5, 83, .5), (19, 81, .5), (19.5, 79, .5),
    (20, 81, 1), (21, 76, 1), (22, 74, .5), (22.5, 72, .5), (23, 76, 1),
    (24, 77, 1), (25, 81, 1), (26, 79, 1), (27, 83, 1),
    (28, 84, 3.2),
]


def score():
    drums, bass, music, sfx, verb = Bus(), Bus(), Bus(), Bus(), Bus()
    kicks = []

    # --- bar 1: the hook. Hits on each word, the plate lands, the coin spins, the rush in
    K, CL, SN = kick(), clap(), snare()
    for n, g in ((0, .6), (1, .8), (2, .6), (3, .8), (3.5, .5)):
        drums.add(K, b(n), g)
        kicks.append(b(n))
    for n in (0, 2):
        drums.add(CL, b(n), .45)
    drums.add(SN, b(3), .6)
    sfx.add(impact(1.0), b(1), .5)
    sfx.add(metal_clank(360, .4), b(1), .45, -.2)
    sfx.add(whoosh(.5, 400, 3000), b(1.25), .35, .3)
    spin = whoosh(b(3) - b(1.25), 800, 6000, 3)
    sfx.add(spin * np.linspace(.2, 1, len(spin)), b(1.25), .35)
    sfx.add(bell(88, .25), b(3), .25, .2)
    sfx.add(impact(.8), b(3), .35)
    sfx.add(riser(b(4) - b(3.25), 500, 9000), b(3.25), .5)
    for k in range(8):                                   # snare roll into the drop
        drums.add(SN, b(3.5) + k * (b(4) - b(3.5)) / 8, .1 + .04 * k)
    arp_tones = [57, 60, 64, 69, 72, 69, 64, 60]
    for k in range(16):                                  # the intro arpeggio opens up
        s = b(k / 4)
        tone = arp_note(arp_tones[k % 8] + 12, .11)
        music.add(lp(tone, 900 + 4000 * k / 16), s, .06 + .08 * k / 16, (-.3, .3)[k % 2])
    music.add(pad_chord(CHORDS['Am'][0], b(3.75), 1100), 0, .14)

    # --- bars 2-7: the drop and the ride
    for bar in range(1, 7):
        for q in range(4):
            beat = bar * 4 + q
            drums.add(K, b(beat), 1.0)
            kicks.append(b(beat))
            if q in (1, 3):
                drums.add(CL, b(beat), .6)
            drums.add(hat(True), b(beat + .5), .11)
            for s16 in (.25, .75):
                drums.add(hat(), b(beat + s16), .06, .25)
    for n in (4, 16, 24):
        drums.add(crash(), b(n), .22)
    for start, name, beats in PROG:
        tones, root = CHORDS[name]
        for k in range(int(beats * 2)):                  # octave-pumping eighths
            m = root + (12 if k % 2 else 0)
            bass.add(bass_note(m, BT / 2 * .9), b(start + k / 2), .55)
        music.add(pad_chord(tones, b(start + beats) - b(start)), b(start), .32)
        for k in range(int(beats * 4)):                  # sixteenth arpeggio
            m = tones[[0, 2, 3, 4, 3, 2, 1, 2][k % 8]] + 12
            music.add(arp_note(m), b(start + k / 4), .09, (-.35, .35)[k % 2])
    for beat, m, dur in LEAD:
        music.add(lead_note(m, dur * BT * .95), b(beat), .2, .05)
        verb.add(lead_note(m, dur * BT * .95), b(beat), .12)

    # --- bar 7 build: snare roll, riser
    for k in range(16):
        drums.add(SN, b(26) + k * (b(28) - b(26)) / 16, .1 + .025 * k)
    sfx.add(riser(b(28) - b(26.5), 300, 8000), b(26.5), .35)

    # --- bar 8: the end card
    drums.add(K, b(28), 1.1)
    kicks.append(b(28))
    drums.add(crash(3.0), b(28), .3)
    sfx.add(impact(1.4), b(28), .8)
    final = pad_chord([48, 55, 60, 64, 67, 72, 76], DUR - b(28) - .4, 3200)
    music.add(final, b(28), .42)
    verb.add(final, b(28), .25)
    bass.add(bass_note(36, 1.4), b(28), .55)
    for i, m in enumerate([72, 76, 79, 84, 88, 91, 96]):  # sparkle as the wordmark lands
        music.add(arp_note(m, .16), b(29) + i * .045, .12, (-.4, .4)[i % 2])
        verb.add(arp_note(m, .16), b(29) + i * .045, .1)

    # --- scene sound design
    sfx.add(impact(1.6), b(4), .9)                                        # ball bursts open
    sfx.add(hp(noise(int(.6 * SR)), 1500) * decay(int(.6 * SR), .18), b(4), .45)
    sfx.add(whoosh(.35, 600, 2500), b(4) + .03, .35, .5)                  # card flies in
    for t0 in (b(5), b(5.5)):                                             # slot reels
        for k in range(10):
            sfx.add(tick(2400 + 90 * k), t0 + .03 * k * (1 + k * .08), .16, .4)
    sfx.add(tick(1400, .03), b(6.5), .5)                                  # tap
    sfx.add(pop(1300, 500), b(6.5), .4)
    sfx.add(whoosh(.45, 300, 4000), b(6.5), .45, .6)                      # fireball away
    sfx.add(whoosh(b(8) - b(7.5) + .08, 500, 7000, 1.2), b(7.5), .55, .7)  # whip pan
    sfx.add(flame(b(9) - b(8) + .25), b(8) - .1, .5, .2)                  # flamethrower
    sfx.add(impact(1.3), b(9), .95)                                       # CRITICAL HIT
    sfx.add(crash(1.2), b(9), .15)
    sfx.add(bell(91, .5), b(9) + .03, .22, .3)
    for k in range(12):                                                   # HP drains
        sfx.add(blip(84 - k, .045, .25), b(9) + .24 + k * .04, .07, .3)
    for k in range(10):                                                   # effort meter fills
        sfx.add(blip(72 + k * 2, .04, .5), b(9) + .15 + k * .035, .06, -.2)
    sfx.add(bell(96, .35), b(9) + .45, .18, -.2)                          # ...past the crit line
    sfx.add(whoosh(b(11.5) - b(11), 900, 3000), b(11), .45, -.5)          # ball thrown
    sfx.add(pop(1100, 350), b(11.5), .55, .4)                             # ball opens
    cap = sine(np.linspace(500, 1800, int(.18 * SR))) * np.hanning(int(.18 * SR))
    sfx.add(cap, b(11.5) + .02, .22, .4)
    sfx.add(tick(900, .03), b(11.5) + .17, .5, .4)                         # snaps shut
    sfx.add(metal_clank(1900, .08), b(12), .35, .4)                       # lands
    sfx.add(metal_clank(2300, .05), b(12) + .15, .18, .4)
    for n in (12.5, 13):                                                  # wobble, wobble
        sfx.add(tick(700, .04), b(n), .5, .35)
        sfx.add(tick(560, .04), b(n) + .09, .35, .45)
    sfx.add(tick(1800, .05), b(13.5), .6, .3)                             # click: caught
    for i, m in enumerate([81, 85, 88, 93]):
        sfx.add(blip(m, .12, .25), b(13.5) + .04 + i * .06, .12, .2)
    sfx.add(whoosh(.5, 3000, 300, 1.4), b(14), .4)                        # pull back to the dex
    for k in range(46):                                                   # icons pop in
        sfx.add(pop(RNG.uniform(900, 2400), 400, .04), b(14) + .12 + k * .012 + RNG.uniform(0, .02), .08, RNG.uniform(-.8, .8))
    for k in range(14):                                                   # the counter
        sfx.add(tick(3000, .012), b(14) + .4 + k * .025, .08)
    sfx.add(whoosh(.25, 400, 5000, 1.2), b(16) - .12, .45)               # VS panels slam
    sfx.add(impact(1.2), b(16) + .2, .8)
    sfx.add(metal_clank(620, .25), b(16) + .2, .25)
    for i in range(8):                                                    # leaders + badges
        t0 = b(17) + i * BT / 4
        sfx.add(blip(64 + [0, 2, 4, 5, 7, 9, 11, 12][i], .06, .25), t0, .12, .3)
        sfx.add(metal_clank(2400 + 180 * i, .07), t0 + BT / 4, .14, -.1)
    sfx.add(glitch(.38), b(20) - .2, .2)                                  # pixel wipe
    for i, m in enumerate([72, 76, 79, 84, 88]):                          # LEVEL UP
        sfx.add(blip(m, .1, .5), b(21) + i * .05, .16, .1)
    sfx.add(bell(96, .4), b(21) + .25, .14)
    for n in (21, 21.5, 22):                                              # cards flip
        sfx.add(whoosh(.14, 2000, 6000, 2), b(n), .3, -.3 + (n - 21) * .6)
        sfx.add(tick(420, .04), b(n) + .12, .3)
    sfx.add(bell(93, .45), b(23), .2)                                     # choose
    sfx.add(riser(.22, 800, 6000), b(24) - .22, .3)                       # card flies at camera
    sfx.add(impact(.9), b(24), .6)                                        # KANTO
    sfx.add(whoosh(.32, 400, 5000, 1.3), b(26) - .16, .5, -.2)           # wipe to HOENN
    horn = lp(saw(np.full(int(.32 * SR), mtof(45))) + .5 * saw(np.full(int(.32 * SR), mtof(52))), 900)
    sfx.add(horn * env(len(horn), .02, .2, .7, .08), b(26) - .2, .12, .6)  # S.S. Tidal toot
    sfx.add(impact(.8), b(26), .5)
    sfx.add(whoosh(.26, 300, 3000, 1.2), b(28) - .26, .45)               # ball snaps shut
    for n in (28.5, 28.75):                                               # plates slam on
        sfx.add(metal_clank(300, .3), b(n), .45, (-.4, .4)[n == 28.75])
        sfx.add(kick(120, 50, .12), b(n), .3)
    for i in range(10):                                                   # wordmark letters
        sfx.add(blip(79 + [0, 2, 4, 7, 9][i % 5] + 12 * (i // 5), .05, .5), b(29) + i * .028, .06, -.4 + .08 * i)
    sfx.add(pop(1500, 600, .1), b(30), .35)                               # CTA pops
    sfx.add(bell(100, .5), b(30) + .02, .12)

    # --- mix: sidechain, reverb, glue, limit
    duck = np.ones(N)
    t = np.arange(N) / SR
    for k0 in kicks:
        i0 = int(k0 * SR)
        n = min(N - i0, int(.3 * SR))
        dt = np.arange(n) / SR
        duck[i0:i0 + n] = np.minimum(duck[i0:i0 + n], 1 - .65 * np.exp(-dt / .09))
    bass.x *= duck
    music.x *= duck * .5 + .5

    ir_t = np.arange(int(1.8 * SR)) / SR
    ir = np.stack([lp(noise(len(ir_t)), 3200) * np.exp(-ir_t / .4) for _ in range(2)]) * .06
    wet = np.stack([signal.fftconvolve(verb.x[c] + .3 * music.x[c] + .05 * sfx.x[c], ir[c])[:N] for c in range(2)])

    mix = drums.x * .85 + bass.x * .62 + music.x * .95 + sfx.x * .7 + wet * .45
    mix = hp(mix, 34, 4)
    # gentle bus compression (RMS follower) then a soft limiter
    rms = np.sqrt(signal.sosfilt(signal.butter(1, 8 / (SR / 2), output='sos'), (mix ** 2).mean(0)) + 1e-9)
    gain = np.minimum(1, (.3 / rms) ** .3)
    mix *= gain
    mix *= .7 / np.abs(mix).max()
    mix = np.tanh(mix * 1.1) / np.tanh(1.1) * .95
    fade = np.clip((DUR - t) / .5, 0, 1) ** 1.5
    mix *= fade
    mix *= .89 / np.abs(mix).max()
    return mix


def write_wav(path, x):
    y = (np.clip(x, -1, 1) * 32767).astype('<i2').T.copy()
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(y.tobytes())


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'soundtrack.wav'
    write_wav(out, score())
    print('wrote', out)
