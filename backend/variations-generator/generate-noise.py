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

import os
import numpy as np
import pandas as pd
from scipy import signal
from scipy.signal import find_peaks
from scipy.ndimage import uniform_filter1d
from scipy.stats import truncnorm
import matplotlib.pyplot as plt
import argparse
from pathlib import Path
import random

# Noise Scale Constants
NOISE_SCALE_FLOOR = 0.1
NOISE_SCALE_CEILING = 5.1
NOISE_SCALE_INTERVAL = 0.1

class MovementPreservingNoiseGenerator:
    """
    This is the class responsible for generating noise
    for movement, while preserving peaks.
    There is many different mathematical features used
    to normalize the data, find peaks, and create a peak mask.
    Additionally, prominence, thresholds, and smoothing windows
    made for usable noise based on the types of sensor data
    """
    def __init__(self, noise_scale=1.0, plot=False, name=None, random_seed=None, debug=False):
        """Intitialize class instance

        Args:
            noise_scale (float, optional): This is the noise scale to adjust noise globally. Defaults to 1.0.
            plot (bool, optional): This will set the plot boolean. Defaults to False.
            name (str, optional): This is the variant name to assign to images. Defaults to None.
        """
        self.noise_scale = noise_scale
        self.plot = plot
        self.name = name.split('.')[0] if name else None
        self.protection_zone = 5
        self.debug = debug
        
        # Initialize random state
        self.random_seed = random_seed
        if random_seed is not None:
            np.random.seed(random_seed)
            random.seed(random_seed + 1)  # Using different seed for Python's random

        # These are the accelerometer parameters for noise, peak detection, and smoothing
        self.accel_params = {
            'base_std': 0.006 * self.noise_scale, # Base noise floor
            'movement_std_ratio': 0.1,            # Scales noise with movement magnitude
            'prominence_factor': 0.25,            # Used for dynamic peak prominence
            'peak_distance': 25,                  # Minimum distance between peaks
            'peak_prominence': 0.4,               # Minimum height for peaks
            'threshold_multiplier': 1.5,          # Used for adaptive thresholding
            'ma_window_size': 30                  # Smoothing window size
        }
        # These are the gyroscope parameters for noise, peak detection, and smoothing
        self.gyro_params = {
            'base_std': 0.04 * self.noise_scale,  # Base noise floor
            'movement_std_ratio': 0.3,            # Scales noise with movement magnitude
            'prominence_factor': 0.25,            # Used for dynamic peak prominence
            'peak_prominence': 6.0,               # Used for dynamic peak prominence
            'peak_distance': 20,                  # Minimum distance between peaks
            'threshold_multiplier': 1.2,          # Used for adaptive thresholding
            'ma_window_size': 20                  # Smoothing window size
        }
        self.sonar_params = {
            'base_std': 0.2 * self.noise_scale,   # Base noise floor
            'movement_std_ratio': 0.02,           # Scales noise with movement magnitude
            'spike_std_multiplier': 3,
            'dropout_prob': 0.01,
            'spike_prob': 0.005,
            'min_movement_threshold': 5.0,
            'peak_prominence': 6.0,
            'peak_distance': 15,
            'threshold_multiplier': 1.2,
            'ma_window_size': 10,
            'max_noise_fraction': 0.05  # used to clamp noise relative to signal range
        }
        
        # For AccelZ:
        self.accelz_params = {
            # 'base_std': 0.005,             # even smaller base noise for Z
            'movement_std_ratio': 0.05,
            # 'bias_instability': 1e-6,
            # 'min_movement_threshold': 0.15,
            'peak_prominence': 0.4,  # Increased from 0.3
            'max_noise_clip': 0.1,  # optional
            'peak_distance': 15,         # increase minimum distance between peaks
            'peak_width': None,
            'ma_window_size': 30,        # smoother moving average
            'threshold_multiplier': 1.5,   # Increased
            'prominence_factor': 0.3,    # higher prominence
            'base_std': 0.01,
            # 'movement_std_ratio': 0.05,
            'bias_instability': 1e-4,
            'min_movement_threshold': 0.06
        }

    @staticmethod
    def compute_adaptive_threshold(signal, method='percent_max', ratio=0.1):
        """
        Compute an adaptive threshold based on the input signal using a specified method.

        Args:
            signal (np.ndarray): 1D array of signal values (e.g., accelerometer or gyroscope).
            method (str, optional): Method used to compute the threshold. Options are:
                - 'percent_max': ratio × max(abs(signal))
                - 'percent_median': ratio × median(abs(signal))
                - 'std_dev': ratio × standard deviation of signal
                Defaults to 'percent_max'.
            ratio (float, optional): Scaling factor applied to the chosen statistic. Defaults to 0.1.

        Raises:
            ValueError: If an unknown method is specified.

        Returns:
            float: The computed threshold value.
        """
        if method == 'percent_max':
            return ratio * np.max(np.abs(signal))
        elif method == 'percent_median':
            return ratio * np.median(np.abs(signal))
        elif method == 'std_dev':
            return ratio * np.std(signal)
        else:
            raise ValueError(f"Unknown method: {method}")

    def truncated_normal_noise(self, mean, std, size, lower, upper):
        """
        Generate noise from a truncated normal (Gaussian) distribution.

        The noise is sampled from a normal distribution with specified mean and standard deviation,
        but values are limited to lie within [lower, upper].

        Args:
            mean (float): Mean of the normal distribution.
            std (float): Standard deviation of the normal distribution.
            size (int): Number of samples to generate.
            lower (float): Lower bound for truncation.
            upper (float): Upper bound for truncation.

        Returns:
            np.ndarray: Array of `size` samples from the truncated normal distribution.
        """
        a, b = (lower - mean) / std, (upper - mean) / std
        return truncnorm.rvs(a, b, loc=mean, scale=std, size=size, random_state=self.random_seed)

    def get_peaks_and_mask(self, signal, params, protection_zone, normalize=True):
        """
        Detect peaks and create a mask around them with a protection zone.

        Args:
            signal (np.array): 1D sensor data.
            params (dict): Parameter dict with keys like
                - 'peak_prominence'
                - 'prominence_factor'
                - 'peak_distance'
                - 'peak_width'
                - 'ma_window_size'
            protection_zone (int): number of samples to smooth around each peak.
            normalize (bool): If True, apply median-centering to signal.

        Returns:
            filtered_peaks (np.array): Indices of detected peaks (maxima and minima).
            combined_mask (np.array): Float mask around peaks (values 0-1).
            adaptive_thresh (float): Adaptive threshold used.
        """
        # Optional: Normalize signal to address constant bias (e.g. gravity in AccelZ)
        signal_mean = np.mean(signal)
        signal_median = np.median(signal)
        if normalize:
            adjusted_signal = signal - signal_median
        else:
            adjusted_signal = signal.copy()

        # Compute smoothing stats
        ma_window_size = params.get('ma_window_size', 20)
        smoothed_abs = uniform_filter1d(np.abs(adjusted_signal), size=ma_window_size)
        dynamic_prominence = params.get('prominence_factor', 0.1) * np.median(smoothed_abs)

        peak_distance = params.get('peak_distance', 10)
        peak_width = params.get('peak_width', None)

        # Adaptive threshold for base mask
        adaptive_thresh = self.compute_adaptive_threshold(adjusted_signal, method='percent_max', ratio=0.1)

        # Detect peaks
        pos_peaks, _ = find_peaks(adjusted_signal, prominence=dynamic_prominence, distance=peak_distance, width=peak_width)
        neg_peaks, _ = find_peaks(-adjusted_signal, prominence=dynamic_prominence, distance=peak_distance, width=peak_width)
        all_peaks = np.sort(np.concatenate([pos_peaks, neg_peaks]))

        # Filter peaks by height (using absolute values from original signal)
        filtered_peaks = self.filter_peaks_by_height(adjusted_signal, all_peaks, height_factor=0.1)

        # Create boolean and smooth masks
        peak_mask = np.zeros_like(signal, dtype=bool)
        peak_mask[filtered_peaks] = True

        smooth_mask = self.create_smooth_peak_mask(len(signal), filtered_peaks, protection_zone)
        base_mask = np.abs(adjusted_signal - np.mean(adjusted_signal)) > adaptive_thresh

        combined_mask = np.maximum(smooth_mask, base_mask.astype(float))

        if (self.debug):
            # Debug output
            print(f"--- Sensor Axis Debug ---")
            print(f"Signal median: {signal_median:.4f}")
            print(f"Signal mean: {signal_mean:.4f}")
            print(f"Peak count: {len(filtered_peaks)}")
            print(f"Adaptive threshold: {adaptive_thresh:.4f}")
            print(f"Min/Max signal: {np.min(signal):.4f} / {np.max(signal):.4f}")
            print(f"Peak mask (protected samples): {np.sum(combined_mask > 0)}")

        return filtered_peaks, combined_mask, adaptive_thresh

    def filter_peaks_by_height(self, signal, peaks, height_factor=0.1):
        """
        Filter peaks by a minimum height threshold relative to the signal range and mean.

        Args:
            signal (np.array): The signal array.
            peaks (np.array): Indices of detected peaks.
            height_factor (float): Multiplier for signal range to set threshold.

        Returns:
            np.array: Filtered peak indices.
        """
        signal_mean = np.mean(signal)
        signal_range = np.max(signal) - np.min(signal)
        min_peak_height_high = signal_mean + height_factor * signal_range
        min_peak_height_low = signal_mean - height_factor * signal_range

        filtered_peaks = [
            p for p in peaks
            if signal[p] >= min_peak_height_high or signal[p] <= min_peak_height_low
        ]
        return np.array(filtered_peaks, dtype=int)

    def create_smooth_peak_mask(self, length, peaks, protection_zone):
        """
        Generate a smooth mask around peaks with Hanning windows,
        values in [0,1], indicating protected regions where noise is reduced.

        Args:
            length (int): Total length of the signal (e.g., number of samples).
            peaks (np.ndarray): Array of indices (ints) where peaks were detected.
            protection_zone (int): Number of samples to extend on either side of each peak 
                               (the half-width of the Hanning window).

        Returns:
            np.ndarray: A 1D array (same length as signal) containing the smooth peak mask 
                    with values between 0 and 1.
        """
        mask = np.zeros(length)
        window_len = 2 * protection_zone + 1
        window = np.hanning(window_len)

        for p in peaks:
            start = max(0, p - protection_zone)
            end = min(length, p + protection_zone + 1)
            window_slice = window[:end-start]
            mask[start:end] = np.maximum(mask[start:end], window_slice)

        return mask
    
    def adaptive_noise(self, signal, params, peak_mask, axis=None, sensor_type="accel"):
        """Adds adaptive noise to a signal set

        Args:
            signal (np.array): This is the list of values and axes
            params (dict): This is the noise generation parameters
            peak_mask (np.ndarray): An array of peaks and their masks (to protect them)
            axis (str, optional): This is the axis worked on. Defaults to None.
            sensor_type (str, optional): This is the sensor type. Defaults to "accel".

        Returns:
            np.array: This is the adapted noise profile
        """
        n = len(signal)
        base_std = params['base_std']
        movement_std_ratio = params['movement_std_ratio']

        smooth_abs = pd.Series(np.abs(signal)).rolling(window=5, center=True, min_periods=1).mean().values
        movement_mag = smooth_abs * movement_std_ratio

        noise_std = base_std + movement_mag
        noise_std *= (1.0 - peak_mask)
        noise_std = np.clip(noise_std, 1e-6, None)

        # Use symmetric truncation for all axes, including AccelZ
        lower_bound = -3 * noise_std
        upper_bound = 3 * noise_std

        a = (lower_bound - 0) / noise_std
        b = (upper_bound - 0) / noise_std

        noise = truncnorm.rvs(a, b, loc=0, scale=noise_std, size=n, random_state=self.random_seed)

        if hasattr(self, 'noise_scale'):
            noise *= self.noise_scale

        return noise
    
    def add_imu_noise(self, imu_data, params, sensor_type='accel'):
        """Adds noise to the IMU data

        Args:
            imu_data (np.array): List of IMU data by axis
            params (dict): This is a dictionary of noise parameters
            sensor_type (str, optional): Type of sensor. Defaults to 'accel'.

        Returns:
            np.array: A numpy of the noise values by axis
        """
        noisy_data = np.zeros_like(imu_data)
        protection_zone = self.protection_zone
        # Iterate through the axes
        for axis in range(3):
            signal = imu_data[:, axis]

            # Median-center if accelerometer
            if sensor_type == 'accel':
                signal_median = np.median(signal)
                signal_centered = signal - signal_median
            else:
                signal_centered = signal
                signal_median = 0.0

            # Get peaks based on centered signal
            peaks, peak_mask, adaptive_thresh = self.get_peaks_and_mask(
                signal_centered, params, protection_zone
            )

            # Generate noise based on centered signal (for better scaling)
            noise = self.adaptive_noise(signal_centered, params, peak_mask)

            # Add noise back to the *original* signal
            noisy_signal = signal + noise
            noisy_data[:, axis] = noisy_signal

            if (self.debug):
                # Debug output
                print(f"--- Sensor: {sensor_type}, Axis: {axis} ---")
                print(f"Signal median: {np.median(signal):.4f}")
                print(f"Peak count: {len(peaks)}")
                print(f"Adaptive threshold: {adaptive_thresh:.4f}")
                print(f"Base signal min/max: {np.min(signal):.4f} / {np.max(signal):.4f}")
                print(f"Noisy signal min/max: {np.min(noisy_signal):.4f} / {np.max(noisy_signal):.4f}")
                print(f"Noise std (mean): {np.std(noise):.4f}")
                print(f"Bias noise (mean/std): {np.mean(noise):.4f} / {np.std(noise):.4f}")
                print(f"Peak mask sum (protected samples): {np.sum(peak_mask > 0)}")

        return noisy_data

    def add_sonar_noise(self, clean_sonar):
        """This will add noise a template of sonar values

        Args:
            clean_sonar (np.array): This is a list of values from the sonar

        Returns:
            np.array: This is a numpy of the noise values
        """
        clean_sonar = np.asarray(clean_sonar)
        n_samples = clean_sonar.shape[0]
        noisy = clean_sonar.copy()
        params = self.sonar_params

        # Normalize for peak detection
        signal_median = np.median(clean_sonar)
        centered_signal = clean_sonar - signal_median
        # Get peak data from normalized values
        peaks, peak_mask, adaptive_thresh = self.get_peaks_and_mask(
            centered_signal, params, self.protection_zone
        )

        diff = np.abs(np.diff(clean_sonar, prepend=clean_sonar[0]))
        significant_changes = diff > (3 * params['base_std'])
        # Smooth the peakss
        smooth_abs = pd.Series(np.abs(centered_signal)).rolling(window=10, center=True, min_periods=1).mean().values
        movement_std_ratio = params.get('movement_std_ratio', 0.1)
        movement_mag = smooth_abs * movement_std_ratio
        
        noise_std = params['base_std'] + movement_mag
        signal_range = np.max(clean_sonar) - np.min(clean_sonar)
        max_noise_std = signal_range * 0.1
        noise_std = np.minimum(noise_std, max_noise_std)

        # Suppress noise near peaks and strong transitions
        noise_std *= (1.0 - peak_mask)
        noise_std[significant_changes] *= 0.3
        noise_std = np.clip(noise_std, 1e-6, None)

        noise = self.truncated_normal_noise(
            mean=0,
            std=noise_std * self.noise_scale,
            size=clean_sonar.shape,
            lower=-2.5 * noise_std * self.noise_scale,
            upper=2.5 * noise_std * self.noise_scale
        )

        # Add occasional spikes
        spike_mask = (~significant_changes) & (np.random.RandomState(self.random_seed).random(n_samples) < params['spike_prob'])
        noise[spike_mask] += np.random.normal(
            0, params['base_std'] * params['spike_std_multiplier'], np.sum(spike_mask)
        ) * self.noise_scale
        
        # Dropout: simulate missing returns but keep some floor
        dropout_mask = np.random.RandomState(self.random_seed).random(n_samples) > params['dropout_prob']
        noisy = (noisy + noise) * dropout_mask + (1.0 - dropout_mask) * np.clip(clean_sonar * 0.3, 5.0, None)

        # Clamp extreme low values (valleys)
        min_floor = np.percentile(clean_sonar, 1) * 0.5
        noisy = np.clip(noisy, min_floor, None)

        if (self.debug):
            print(f"Sonar axis 0 - Peaks: {len(peaks)}, RepThresh: {adaptive_thresh:.3f}, "
                f"Min: {np.min(noisy):.3f}, Max: {np.max(noisy):.3f}, Mean: {np.mean(noisy):.3f}")

        return noisy

    def process_csv(self, input_file, output_file):
        """This function processes the CSV file

        Args:
            input_file (str): This is the name of the input file
            output_file (str): This is the name of the output file

        Returns:
            DataFrane: The DataFrame of the noise file
        """
        # Read the CSV file and parse it
        df = pd.read_csv(input_file)
        self.original_data = {
            'accel': df[['AccelX(g)', 'AccelY(g)', 'AccelZ(g)']].values,
            'gyro': df[['GyroX(deg/s)', 'GyroY(deg/s)', 'GyroZ(deg/s)']].values,
            'sonar': df[['DistanceLeft(cm)', 'DistanceRight(cm)']].values
        }
        
        # Process IMU data
        if all(col in df.columns for col in ['AccelX(g)','AccelY(g)','AccelZ(g)']):
            accel_data = df[['AccelX(g)','AccelY(g)','AccelZ(g)']].values
            df[['AccelX(g)','AccelY(g)','AccelZ(g)']] = self.add_imu_noise(accel_data, self.accel_params)
        
        if all(col in df.columns for col in ['GyroX(deg/s)','GyroY(deg/s)','GyroZ(deg/s)']):
            gyro_data = df[['GyroX(deg/s)','GyroY(deg/s)','GyroZ(deg/s)']].values
            df[['GyroX(deg/s)','GyroY(deg/s)','GyroZ(deg/s)']] = self.add_imu_noise(gyro_data, self.gyro_params, sensor_type="gyro")
        
        # Process sonar data (handles multiple sonars)
        sonar_cols = [c for c in df.columns if 'sonar' in c.lower() or 'dist' in c.lower()]
        for col in sonar_cols:
            df[col] = self.add_sonar_noise(df[col].values)
        
        # Convert distance columns back to int
        if 'DistanceLeft(cm)' in df.columns:
            df['DistanceLeft(cm)'] = df['DistanceLeft(cm)'].round().astype(int)
        if 'DistanceRight(cm)' in df.columns:
            df['DistanceRight(cm)'] = df['DistanceRight(cm)'].round().astype(int)
        
        # Round all other float columns to 3 decimal places
        float_cols = df.select_dtypes(include=['float64']).columns
        df[float_cols] = df[float_cols].round(3)
        
        df.to_csv(output_file, index=False)
        
        # If plotting is enabled, generate the visualization
        if self.plot:
            self._plot_results_compare_all_with_noise(df, self.original_data, )
        
        # Return the DataFrame of the updated data adjusted with noise
        return df
    
    def _plot_results_compare_all_with_noise(self, df, original_data=None):
        """Plot the results for all sensors with noise

        Args:
            df (DataFrame): This is the DataFrame of the noise
            original_data (DataFrame, optional): DataFrame of original data (for comparison).
            Defaults to None.
        """
        # Create sensor data from the DataFrame
        sensors = {
            'accel': df[['AccelX(g)', 'AccelY(g)', 'AccelZ(g)']].values,
            'gyro': df[['GyroX(deg/s)', 'GyroY(deg/s)', 'GyroZ(deg/s)']].values,
            'sonar': df[['DistanceLeft(cm)', 'DistanceRight(cm)']].values
        }
        # Threshold specific style
        threshold_line_style = {
            'color': 'purple',
            'linestyle': '--',
            'alpha': 0.3,
            'label': 'Adaptive Threshold'
        }

        fig, axs = plt.subplots(8, 1, figsize=(14, 24), sharex=True)

        original_style = {'color': 'blue', 'alpha': 0.5, 'linewidth': 1.5, 'label': 'Original'}
        noisy_style = {'color': 'red', 'alpha': 0.7, 'linewidth': 1.0, 'label': 'Noisy with Movement Preservation'}

        accel_labels = ['X', 'Y', 'Z']
        gyro_labels = ['X', 'Y', 'Z']
        sonar_labels = ['Left', 'Right']

        for i in range(3):
            signal = sensors['accel'][:, i]
            if original_data is not None:
                original_signal = original_data['accel'][:, i]
                axs[i].plot(original_signal, **original_style)
            else:
                original_signal = signal  # fallback if no original

            axs[i].plot(signal, **noisy_style)

            # Peak detection for original_signal
            peaks, peak_mask, adaptive_thresh = self.get_peaks_and_mask(original_signal, self.accel_params, self.protection_zone)

            axs[i].plot(peaks, signal[peaks], "rx", label='Detected Peaks')
            # axs[i].axhline(y=self.accel_params['min_movement_threshold'], color='g', linestyle='--', label='Threshold')
            axs[i].plot(peak_mask * np.max(signal), 'k--', alpha=0.3, label='Peak Mask')
            # axs[i].axhline(adaptive_thresh, **threshold_line_style)

            # Add plot for adaptive threshold (as a separate line)
            # axs[i].plot(adaptive_thresh * np.ones_like(signal), linestyle=':', color='purple', alpha=0.4, label='Adaptive Thresh Line')

            axs[i].set_title(f'Accelerometer {accel_labels[i]}-Axis with Movement-Preserving Noise')
            axs[i].set_ylabel('Acceleration (g)')
            axs[i].legend(fontsize=8, framealpha=0.4)
            axs[i].grid(True, linestyle='--', alpha=0.6)

        # Gyroscope plotting (same as you have) with added peak mask plotting
        for i in range(3):
            idx = i + 3
            signal = sensors['gyro'][:, i]
            if original_data is not None:
                original_signal = original_data['gyro'][:, i]
                axs[idx].plot(original_signal, **original_style)
            else:
                original_signal = signal

            axs[idx].plot(signal, **noisy_style)

            peaks, peak_mask, adaptive_thresh = self.get_peaks_and_mask(original_signal, self.gyro_params, self.protection_zone)

            axs[idx].plot(peaks, signal[peaks], "rx", label='Detected Peaks')
            # axs[idx].axhline(y=self.gyro_params['min_movement_threshold'], color='g', linestyle='--', label='Threshold')
            axs[idx].plot(peak_mask * np.max(signal), 'k--', alpha=0.3, label='Peak Mask')

            axs[idx].set_title(f'Gyroscope {gyro_labels[i]}-Axis with Movement-Preserving Noise')
            axs[idx].set_ylabel('Angular Velocity (deg/s)')
            axs[idx].legend(fontsize=8, framealpha=0.4)
            axs[idx].grid(True, linestyle='--', alpha=0.6)

        # Sonar plotting
        for i in range(2):
            idx = i + 6
            if sensors['sonar'].shape[1] > i:
                signal = sensors['sonar'][:, i]
                if original_data is not None and 'sonar' in original_data:
                    original_signal = original_data['sonar'][:, i]
                    axs[idx].plot(original_signal, **original_style)
                else:
                    original_signal = signal

                axs[idx].plot(signal, **noisy_style)

                peaks, peak_mask, adaptive_thresh = self.get_peaks_and_mask(original_signal, self.sonar_params, self.protection_zone)

                axs[idx].plot(peaks, signal[peaks], "rx", label='Detected Peaks')
                # axs[idx].axhline(y=self.sonar_params['min_movement_threshold'], color='g', linestyle='--', label='Threshold')
                axs[idx].plot(peak_mask * np.max(signal), 'k--', alpha=0.3, label='Peak Mask')

                axs[idx].set_title(f'Ultrasonic Sensor ({sonar_labels[i]}) with Movement-Preserving Noise')
                axs[idx].set_ylabel('Distance (cm)')
                axs[idx].legend(fontsize=8, framealpha=0.4)
                axs[idx].grid(True, linestyle='--', alpha=0.6)

        axs[-1].set_xlabel('Sample Number')

        plt.tight_layout()
        plt.savefig(f'{self.name}.png', dpi=300)
        #plt.show()
        plt.close()

def process_all_csvs(input_dir, floor, ceiling, interval, variant_name='variants', plot=False):
    """
    This will process all the CSVs in a directory and output results to variant
    directory. This performs an OS walk to find CSV files, but ignores the variant output
    directory to avoid recursive walks.

    Args:
        input_dir (str): This is the input directory
        output_dir (str): This is the output directory
        variant_name (str): This is the name of the variant (coding for variants)
        plot (bool): Boolean that defines wether to plot the results or not
    """
    # Get ready to start processing CSVs
    variant_count = 0
    print(f'Starting data variant generation on {input_dir}...')
    # Walk the source directory
    for root, dirs, files in os.walk(input_dir):
        # Skip directories that match our variant_name (case-sensitive)
        if variant_name in dirs:
            dirs.remove(variant_name)  # Don't walk into existing variant dirs
        # Process the rest of the directory files
        for file in files:
            if file.endswith(".csv"):
                input_csv = os.path.join(root, file)
                
                # Create variants directory in same directory as source file
                variants_dir = os.path.join(root, variant_name)
                os.makedirs(variants_dir, exist_ok=True)
                
                # Create a base seed from file path hash for reproducibility
                file_hash = hash(os.path.join(root, file)) & 0xFFFFFFFF
                
                # Iterate through noise scales from 0.1 to 5.0 in 0.1 increments
                for i, noise_scale in enumerate(np.arange(floor, ceiling, interval)):
                    # Create unique seed for this variant
                    current_seed = file_hash + i
                    scale_str = f"{noise_scale:.1f}".replace('.', '_')
                    
                    # Generate variant filename
                    file_base, file_ext = os.path.splitext(file)
                    output_filename = f'{file_base}_{variant_name}_scale{scale_str}'
                    output_base = os.path.join(variants_dir, f'{output_filename}')
                    output_path = os.path.join(variants_dir, f'{output_filename}.{file_ext}')
                    
                    # Process the file
                    processor = MovementPreservingNoiseGenerator(
                        noise_scale=noise_scale,
                        plot=plot,
                        name=output_filename,
                        random_seed=current_seed
                    )
                    
                    result = processor.process_csv(input_csv, output_path)
                    variant_count += 1
    #print(f"Created variant {i+1}/50: {output_path} (scale: {noise_scale:.1f})")
    print(f'Completed variant generation on {input_dir}. Generated {variant_count} variants.')

                    # if plot:
                    #     processor.plot_results_compare_all_with_noise(result, processor.original_data)

# Multi File Program
if __name__ == "__main__":
    # Setup the argument parser
    parser = argparse.ArgumentParser(description='Add realistic noise variants to sensor data in multiple CSV files')
    parser.add_argument('input_dir', help='Directory containing input CSV files')
    parser.add_argument('--plot', action='store_true', help='Show comparison plots')
    parser.add_argument('--noise-floor', type=float, default=NOISE_SCALE_FLOOR, help='Lowest noise scale value (start value)')
    parser.add_argument('--noise-ceiling', type=float, default=NOISE_SCALE_CEILING, help='Largest noise scale value (end value)')
    parser.add_argument('--noise-interval', type=float, default=NOISE_SCALE_INTERVAL, help='Interval of change in noise scale')

    args = parser.parse_args()

    process_all_csvs(args.input_dir,
                     floor=args.noise_floor,
                     ceiling=args.noise_ceiling,
                     interval=args.noise_interval,
                     plot=args.plot)


# # Single File Program
# if __name__ == "__main__":
#     # No outlier protection
#     parser = argparse.ArgumentParser(description='Add realistic noise to sensor data')
#     parser.add_argument('input_csv', help='Path to input CSV file')
#     parser.add_argument('output_csv', help='Path for output CSV file')
#     parser.add_argument('--noise_scale', type=float, default=1.0,
#                       help='Scaling factor for noise intensity (0.5-2.0 recommended)')
#     parser.add_argument('--plot', action='store_true', help='Show comparison plots')
    
#     args = parser.parse_args()
    
#     # Create an instance of the noise generator
#     processorPreserve = MovementPreservingNoiseGenerator(args.noise_scale, args.plot, args.output_csv)
    
#     # Process your data
#     result = processorPreserve.process_csv(args.input_csv, args.output_csv)
    
#     print(f"Protect Outlier augmented data saved to '{args.output_csv}'")
    
#     # Plot if option selected
#     if args.plot:
#         #processorPreserve.plot_results_compare_all(result, processor.original_data)
#         processorPreserve.plot_results_compare_all_with_noise(result, processorPreserve.original_data)
