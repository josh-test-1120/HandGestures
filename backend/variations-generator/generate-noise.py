# Noise generation tool for MPU-6050 and HC-SR04s
# Accelerometer data and Gyroscopic data
# As well as the SR-HC04s distance data
#
# This will generate noise based on a guassian curve
# this will read an existing CSV file of raw data
# and use this data to generate a new CSV file
# with update values that have injected noise
# into the original values
#
#
# Author: Joshua Summers

import numpy as np
import pandas as pd
from scipy import signal
import matplotlib.pyplot as plt
import argparse

class SensorNoiseGenerator:
    def __init__(self):
        # MPU-6050 typical noise parameters (adjust based on your observations)
        self.mpu_params = {
            'accelerometer': {
                'std_dev': 0.004,  # ±4mg RMS noise
                'bias_instability': 0.0005,  # 0.5mg
                'temp_coeff': 0.001  # 1mg/°C
            },
            'gyroscope': {
                'std_dev': 0.05,  # ±0.05 dps RMS
                'bias_instability': 0.01,  # 10mdps
                'temp_coeff': 0.1  # 0.1dps/°C
            }
        }
        
        # HC-SR04 typical noise parameters
        self.sonar_params = {
            'std_dev': 0.5,  # cm
            'dropout_prob': 0.01,
            'spike_prob': 0.005,
            'spike_range': (20, 50)  # cm
        }
    
    def load_data(self, csv_path):
        """Load sensor data from CSV"""
        df = pd.read_csv(csv_path)
        
        # Extract sensor data (adjust column names as needed)
        sensors = {
            'accel': df[['ax', 'ay', 'az']].values,
            'gyro': df[['gx', 'gy', 'gz']].values,
            'sonar': df.filter(regex='sonar|ultra|dist').values  # catches various column naming conventions
        }
        
        return df, sensors
    
    def _gaussian_noise(self, shape, std_dev):
        return np.random.normal(0, std_dev, shape)
    
    def _brownian_noise(self, length, scale):
        return np.cumsum(np.random.randn(length)) * scale
    
    def _temperature_drift(self, length, amplitude, period=None):
        x = np.linspace(0, 2*np.pi, length)
        period = period or length/10  # default to 10 cycles over dataset
        return amplitude * np.sin(x/period)
    
    def _cross_axis_coupling(self, data, coupling_factor=0.03):
        coupling_matrix = np.array([
            [1, coupling_factor, coupling_factor],
            [coupling_factor, 1, coupling_factor],
            [coupling_factor, coupling_factor, 1]
        ])
        return data @ coupling_matrix
    
    def add_mpu_noise(self, clean_data, sensor_type='accelerometer'):
        """Add composite noise to IMU data"""
        params = self.mpu_params[sensor_type]
        length = clean_data.shape[0]
        
        # White noise
        noise = self._gaussian_noise(clean_data.shape, params['std_dev'])
        
        # Bias instability (random walk)
        for i in range(clean_data.shape[1]):
            noise[:,i] += self._brownian_noise(length, params['bias_instability'])
        
        # Temperature drift
        noise += self._temperature_drift(length, params['temp_coeff'])[:, np.newaxis]
        
        # Cross-axis coupling (only for 3-axis sensors)
        if clean_data.shape[1] == 3:
            noise = self._cross_axis_coupling(noise)
        
        return clean_data + noise
    
    def add_sonar_noise(self, clean_sonar):
        """Add realistic ultrasonic sensor noise"""
        params = self.sonar_params
        noisy = clean_sonar.copy()
        
        # Gaussian noise
        noisy += self._gaussian_noise(clean_sonar.shape, params['std_dev'])
        
        # Dropout (missed readings)
        mask = np.random.random(clean_sonar.shape) > params['dropout_prob']
        noisy = noisy * mask
        
        # Clip negative values
        noisy = np.clip(noisy, 0, None)
        
        # Add occasional spikes
        spike_mask = np.random.random(clean_sonar.shape) < params['spike_prob']
        spike_size = np.random.uniform(params['spike_range'][0], params['spike_range'][1], 
                                    clean_sonar.shape)
        noisy += spike_mask * spike_size
        
        return noisy
    
    def augment_data(self, input_csv, output_csv, noise_scale=1.0, plot=False):
        """Main function to process CSV and add noise"""
        df, sensors = self.load_data(input_csv)
        
        # Process MPU-6050 data
        sensors['accel'] = self.add_mpu_noise(sensors['accel'], 'accelerometer') * noise_scale
        sensors['gyro'] = self.add_mpu_noise(sensors['gyro'], 'gyroscope') * noise_scale
        
        # Process HC-SR04 data
        if sensors['sonar'].size > 0:
            sensors['sonar'] = self.add_sonar_noise(sensors['sonar'])
        
        # Update dataframe with noisy data
        df[['ax', 'ay', 'az']] = sensors['accel']
        df[['gx', 'gy', 'gz']] = sensors['gyro']
        
        # Update sonar columns (handles variable column names)
        sonar_cols = df.filter(regex='sonar|ultra|dist').columns
        if len(sonar_cols) > 0:
            df[sonar_cols] = sensors['sonar']
        
        # Save results
        df.to_csv(output_csv, index=False)
        
        # Visualization
        if plot:
            self._plot_results(sensors, noise_scale)
        
        return df
    
    def _plot_results(self, sensors, noise_scale):
        """Generate comparison plots"""
        fig, axs = plt.subplots(3, 1, figsize=(12, 12))
        
        # Accelerometer plot
        axs[0].plot(sensors['accel'][:,0], label='Noisy X', alpha=0.7)
        axs[0].set_title(f'Accelerometer Data (Noise Scale: {noise_scale})')
        axs[0].legend()
        
        # Gyroscope plot
        axs[1].plot(sensors['gyro'][:,0], label='Noisy X', alpha=0.7)
        axs[1].set_title('Gyroscope Data')
        axs[1].legend()
        
        # Sonar plot (if available)
        if sensors['sonar'].size > 0:
            axs[2].plot(sensors['sonar'][:,0], label='Noisy Sonar', alpha=0.7)
            axs[2].set_title('Ultrasonic Sensor Data')
            axs[2].legend()
        
        plt.tight_layout()
        plt.show()


class MovementPreservingNoiseGenerator:
    def __init__(self):
        # Noise parameters (tuned for MPU-6050)
        self.accel_params = {
            'base_std': 0.004,       # Baseline noise (g)
            'movement_std_ratio': 0.1, # Noise relative to movement magnitude
            'bias_instability': 0.0005,
            'min_movement_threshold': 0.2,  # g (adjust based on your data)
            'peak_prominence': 0.3     # For peak detection
        }
        
        self.gyro_params = {
            'base_std': 0.05,        # dps
            'movement_std_ratio': 0.1,
            'bias_instability': 0.01,
            'min_movement_threshold': 1.0,  # dps
            'peak_prominence': 2.0
        }
        
        self.sonar_params = {
            'base_std': 0.5,          # cm
            'spike_std_multiplier': 3, # For outlier preservation
            'dropout_prob': 0.01,
            'spike_prob': 0.005
        }

    def _adaptive_gaussian_noise(self, signal, base_std, movement_ratio):
        """Noise that scales with signal amplitude but preserves peaks"""
        # Find significant movements
        peaks, _ = find_peaks(np.abs(signal), 
                             prominence=self.accel_params['peak_prominence'])
        movement_mask = np.zeros_like(signal)
        for peak in peaks:
            # Expand protection zone around peaks
            start = max(0, peak-5)
            end = min(len(signal), peak+5)
            movement_mask[start:end] = 1
        
        # Create adaptive noise
        movement_magnitude = np.abs(signal) * movement_ratio
        protected_zones = movement_mask * np.maximum(0, movement_magnitude - base_std)
        noise = np.random.normal(0, base_std, len(signal))
        noise += protected_zones * np.random.randn(len(signal))
        
        return noise

    def add_imu_noise(self, clean_data, params):
        """Outlier-preserving IMU noise"""
        noisy_data = np.zeros_like(clean_data)
        for i in range(clean_data.shape[1]):
            base_signal = clean_data[:,i]
            
            # Adaptive noise that respects movements
            adaptive_noise = self._adaptive_gaussian_noise(
                base_signal,
                params['base_std'],
                params['movement_std_ratio']
            )
            
            # Add bias instability (low-frequency)
            bias_noise = np.cumsum(np.random.randn(len(base_signal))) * params['bias_instability']
            
            # Combine noise components
            noisy_data[:,i] = base_signal + adaptive_noise + bias_noise
            
            # Preserve extreme values
            peak_mask = np.abs(base_signal) > params['min_movement_threshold']
            noisy_data[:,i][peak_mask] = base_signal[peak_mask] + (
                np.random.normal(0, params['base_std'], sum(peak_mask))
        
        return noisy_data

    def add_sonar_noise(self, clean_sonar):
        """Noise that preserves true distance changes"""
        noisy = clean_sonar.copy()
        params = self.sonar_params
        
        # Find significant distance changes
        diff = np.abs(np.diff(clean_sonar, axis=0, prepend=0))
        significant_changes = diff > (3 * params['base_std'])
        
        # Base noise (reduced at significant changes)
        noise = np.random.normal(0, params['base_std'], clean_sonar.shape)
        noise[significant_changes] *= 0.3  # Reduce noise at important transitions
        
        # Add spike noise only in stable regions
        spike_mask = (~significant_changes) & (
            np.random.random(clean_sonar.shape) < params['spike_prob'])
        noise += spike_mask * np.random.normal(0, params['base_std']*params['spike_std_multiplier'], 
                                             clean_sonar.shape)
        
        # Apply dropout
        dropout_mask = np.random.random(clean_sonar.shape) > params['dropout_prob']
        noisy = (noisy + noise) * dropout_mask
        
        return np.clip(noisy, 0, None)

    def process_csv(self, input_file, output_file):
        df = pd.read_csv(input_file)
        
        # Process IMU data
        if all(col in df.columns for col in ['ax','ay','az']):
            accel_data = df[['ax','ay','az']].values
            df[['ax','ay','az']] = self.add_imu_noise(accel_data, self.accel_params)
        
        if all(col in df.columns for col in ['gx','gy','gz']):
            gyro_data = df[['gx','gy','gz']].values
            df[['gx','gy','gz']] = self.add_imu_noise(gyro_data, self.gyro_params)
        
        # Process sonar data (handles multiple sonars)
        sonar_cols = [c for c in df.columns if 'sonar' in c.lower() or 'dist' in c.lower()]
        for col in sonar_cols:
            df[col] = self.add_sonar_noise(df[col].values)
        
        df.to_csv(output_file, index=False)
        return df

# Example usage
if __name__ == "__main__":
    # No outlier protection
    parser = argparse.ArgumentParser(description='Add realistic noise to sensor data')
    parser.add_argument('input_csv', help='Path to input CSV file')
    parser.add_argument('output_csv', help='Path for output CSV file')
    parser.add_argument('--noise_scale', type=float, default=1.0,
                      help='Scaling factor for noise intensity (0.5-2.0 recommended)')
    parser.add_argument('--plot', action='store_true', help='Show comparison plots')
    
    args = parser.parse_args()
    
    output_csv = 'no-outlier-' + args.output_csv
    
    processor = SensorNoiseGenerator()
    processor.augment_data(args.input_csv, output_csv, 
                         args.noise_scale, args.plot)
    
    print(f"No outlier augmented data saved to 'no-outlier-{args.output_csv}'")
    
    
    processor = MovementPreservingNoiseGenerator()
    
    # Process your data
    output_csv = 'protect-outliers-' + args.output_csv
    result = processor.process_csvargs.input_csv, output_csv)
    
    # Visualize a sample
    plt.figure(figsize=(12,6))
    plt.plot(result['ax'][1000:2000], label='Noisy Accel X')
    plt.title("Accelerometer Data with Movement-Preserving Noise")
    plt.legend()
    plt.show()