class ProcessCWTSingle():
    def __init__(self, device=None, base_freq=50, target_len=127, **kwargs):
        self.target_len = 127
        self.base_freq = 50
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
        tensor = torch.from_numpy(coeff[:, :target_len]).float().to(self.device)
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
        
        estimated_len = int(duration_s * base_freq)
    
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
            print(f"Processing channel {ch + 1}/{num_channels}")
            for i in tqdm(range(0, num_samples, batch_size)):
                batch = data[i:i + batch_size, :, ch]
                batch_tensor = torch.from_numpy(batch).float().to(self.device)
                for k in range(batch_tensor.shape[0]):
                    result[i + k, :, :, ch] = self._compute_cwt(batch_tensor[k])
        return result.cpu().numpy()