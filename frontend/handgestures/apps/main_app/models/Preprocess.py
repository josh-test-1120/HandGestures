import torch
import torch.nn.functional as F
import numpy as np
import pandas as pd
import pywt
from tqdm import tqdm
from scipy.interpolate import interp1d
from pathlib import Path

class ProcessCWTSingle():
    def __init__(self, device=None, base_freq=50, target_len=127, **kwargs):
        self.target_len = target_len
        self.base_freq = base_freq
        self.scales=range(1, 128)
        self.waveletname = 'morl'
        
        if torch.backends.mps.is_available(): device = torch.device("mps")
        elif torch.cuda.is_available(): device = torch.device("cuda")
        else: device = torch.device("cpu")
        self.device = device
    
    def _normalize_signal(self, data):
        return (data - np.median(data, axis=0)) / (np.std(data, axis=0) + 1e-6)
    
    def _compute_cwt(self, signal_1d):
        signal_1d = signal_1d - signal_1d.median()
        coeff, _ = pywt.cwt(signal_1d.cpu().numpy(), self.scales, self.waveletname, 1)
        tensor = torch.from_numpy(coeff[:, :self.target_len]).float().to(self.device)
        return self._normalize_cwt_tensor(tensor)
    
    def process_single_csv_cwt(self, csv_path):
        # Load and resample
        df = pd.read_csv(csv_path)
        signal, _ = self._resample_to_uniform(df)
    
        # Ensure proper shape: (1, time, channels)
        signal = signal.astype(np.float32)[None, :, :]  # Add batch dimension
    
        # Compute CWT
        cwt_tensor = self._process_dataset_tensor(signal)
    
        return cwt_tensor  # shape: (1, target_len, target_len, channels)
    
    def _resample_to_uniform(self, df):
        timestamps = df['Timestamp(ms)'].values.astype(np.float64)
        cols = ['AccelX(g)', 'AccelY(g)', 'AccelZ(g)', 
                'GyroX(deg/s)', 'GyroY(deg/s)', 'GyroZ(deg/s)']
        signals = df[cols].values
    
        # Unique timestamps
        timestamps, unique_indices = np.unique(timestamps, return_index=True)
        signals = signals[unique_indices]
    
        duration_ms = timestamps[-1] - timestamps[0]
        duration_s = duration_ms / 1000.0
        est_freq = len(timestamps) / duration_s if duration_s > 0 else base_freq
        est_freq = np.clip(est_freq, 10, 200)
    
        if self.target_len is None:
            target_len = int(duration_s * base_freq)
            target_len = np.clip(target_len, 80, 160)
        else:
            target_len = self.target_len
    
        uniform_timestamps = np.linspace(timestamps[0], timestamps[-1], num=target_len)
        resampled = np.zeros((target_len, len(cols)))
        
        # After removing duplicates
        timestamps, unique_indices = np.unique(df['Timestamp(ms)'].values.astype(np.float64), return_index=True)

        duration_ms = timestamps[-1] - timestamps[0]
        duration_s = duration_ms / 1000.0
        
        estimated_len = int(duration_s * self.base_freq)
    
        for i in range(len(cols)):
            interp_func = interp1d(timestamps, signals[:, i], kind='linear', fill_value="extrapolate")
            resampled[:, i] = interp_func(uniform_timestamps)
    
        return self._normalize_signal(resampled), 0  # Adjust start_index if needed
    
    def _normalize_cwt_tensor(self, cwt_tensor):
        mean = cwt_tensor.mean()
        std = cwt_tensor.std()
        return (cwt_tensor - mean) / (std + 1e-6)
    
    def _process_dataset_tensor(self, data, batch_size=32, target_len=127):
        num_samples, signal_length, num_channels = data.shape
        result = torch.zeros((num_samples, target_len, target_len, num_channels), device=self.device)
    
        for ch in range(num_channels):
            for i in (range(0, num_samples, batch_size)):
                batch = data[i:i + batch_size, :, ch]
                batch_tensor = torch.from_numpy(batch).float().to(self.device)
                for k in range(batch_tensor.shape[0]):
                    result[i + k, :, :, ch] = self._compute_cwt(batch_tensor[k])
        return result.cpu().numpy()

    def predict_from_csv(self, csv_path, model, label_dict, index_to_label_id, label_id_to_index, id_to_label_name):
        # Process CSV to get CWT tensor
        cwt_tensor = self.process_single_csv_cwt(csv_path)  # shape: (1, 127, 127, 6)
        x_single = torch.from_numpy(cwt_tensor).permute(0, 3, 1, 2).float().to(self.device)  # (1, 6, 127, 127)
        x_single = x_single.unsqueeze(1)  # (1, 1, 6, 127, 127)

        # Infer label from path (ignoring 'variants')
        p = Path(csv_path)
        parts = list(p.parents)
        label_parts = []
        for part in parts:
            if part.name.lower() != 'variants':
                label_parts.append(part.name.lower())
            if len(label_parts) == 2:
                break
        if len(label_parts) < 2:
            label_name = "unknown"
        else:
            label_name = label_parts[1]
        
        # Map true label
        true_label_id = label_dict.get(label_name)
        true_idx = label_id_to_index.get(true_label_id, -1)
        true_label_name = label_name if true_label_id is not None else "UNKNOWN"

        # Inference
        model.to(self.device)
        model.eval()
        with torch.no_grad():
            outputs = model(x_single)
            probs = F.softmax(outputs, dim=1)[0].cpu().numpy()

        pred_idx = int(probs.argmax())
        pred_label_id = index_to_label_id.get(pred_idx, None)
        pred_label_name = id_to_label_name.get(pred_label_id, "UNKNOWN")

        # Build probability dict
        prob_dict = {}
        for i, p in enumerate(probs):
            label_id = index_to_label_id[i]
            label = id_to_label_name.get(label_id, f"ID_{label_id}")
            prob_dict[label] = float(p)

        return {
            "predicted_label": pred_label_name,
            "predicted_label_id": pred_label_id,
            "predicted_index": pred_idx,
            "true_label": true_label_name,
            "true_label_id": true_label_id,
            "true_index": true_idx,
            "probabilities": prob_dict
        }