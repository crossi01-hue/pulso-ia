import numpy as np, wave, sys

out_wav = sys.argv[1]
sr = 44100
T = 1.8
n = int(sr * T)
audio = np.zeros(n)

def tone(freq, start, dur, amp, harmonics=(1.0,), decay=6.0, attack=0.01):
    i0 = int(start * sr); i1 = min(n, int((start + dur) * sr))
    if i1 <= i0: return
    tt = np.linspace(0, (i1 - i0) / sr, i1 - i0, endpoint=False)
    env = np.exp(-decay * tt)
    a = int(attack * sr)
    if 0 < a < len(env):
        env[:a] *= np.linspace(0, 1, a)
    w = np.zeros_like(tt)
    for k, h in enumerate(harmonics, start=1):
        w += h * np.sin(2 * np.pi * freq * k * tt)
    audio[i0:i1] += amp * env * w

# Cama grave suave (calidez, sobriedad)
tone(146.83, 0.00, 1.8, 0.12, harmonics=(1.0, 0.3), decay=2.2, attack=0.08)   # D3
tone(220.00, 0.00, 1.8, 0.08, harmonics=(1.0, 0.2), decay=2.2, attack=0.10)   # A3
# Dos notas limpias ascendentes (tech, moderno)
tone(587.33, 0.05, 1.2, 0.33, harmonics=(1.0, 0.5, 0.25), decay=4.5, attack=0.005)  # D5
tone(880.00, 0.30, 1.4, 0.30, harmonics=(1.0, 0.4, 0.20), decay=4.0, attack=0.005)  # A5
# Chispa alta sutil
tone(1760.0, 0.32, 0.5, 0.06, harmonics=(1.0,), decay=10.0, attack=0.002)     # A6

# Fade in/out para evitar clics en las uniones
fin = int(0.012 * sr); fout = int(0.30 * sr)
audio[:fin] *= np.linspace(0, 1, fin)
audio[-fout:] *= np.linspace(1, 0, fout)

peak = np.max(np.abs(audio))
if peak > 0:
    audio = audio / peak * 0.5  # -6 dB, sobrio (debajo de la voz)

data = (audio * 32767).astype(np.int16)
with wave.open(out_wav, 'w') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(data.tobytes())
print("WAV OK", out_wav, len(data), "muestras")
