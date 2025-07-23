import sounddevice as sd
import soundfile as sf
import numpy as np
from scipy.signal import resample

filename = '/home/zemen/house_lo.wav'
device_id = 0

data, samplerate = sf.read(filename, dtype='int16')
target_samplerate = 48000

if samplerate != target_samplerate:
    num_samples = int(len(data) * target_samplerate / samplerate)
    if data.ndim == 1:
        data_resampled = resample(data, num_samples).astype('int16')
    else:
        data_resampled = np.vstack([
            resample(data[:, ch], num_samples) for ch in range(data.shape[1])
        ]).T.astype('int16')
else:
    data_resampled = data

print(f"Playing {filename} on device {device_id} with samplerate {target_samplerate}")
sd.play(data_resampled, samplerate=target_samplerate, device=device_id)
sd.wait()
