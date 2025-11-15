# Signal Processing Integration for Django EchoShield

This document describes the integration of advanced signal processing methods from `drone_detection_angle` into the Django EchoShield edge application.

## Overview

The integration adds user-selectable signal processing methods for acoustic drone detection, with real-time configuration management and comprehensive dashboard visualization.

## Features Added

### 1. Signal Processing Methods

Four detection methods are now available:

- **Energy Likelihood Detector**: Multi-evidence detection combining SNR, harmonic integrity, and temporal stability
- **GCC-PHAT Direction of Arrival**: Stereo audio processing for angle estimation using time-difference-of-arrival
- **Harmonic Filter**: Frequency-domain filtering focusing on drone propeller harmonics
- **Combined**: All methods working together for maximum confidence

### 2. Database Models

#### DetectionConfig Model
Stores user-configurable detection parameters:
- Detection method selection
- Fundamental frequency and harmonics settings
- Confidence thresholds
- SNR and temporal parameters
- Evidence weights
- DOA and framing parameters

#### Event Model Extensions
New fields added to Event model:
- `detection_method`: Method used for processing
- `detection_confidence`: Overall confidence score (0.0-1.0)
- `snr_db`: Signal-to-Noise Ratio
- `harmonic_score`: Harmonic integrity score
- `temporal_score`: Temporal stability score
- `doa_angle_deg`: Direction of Arrival angle

### 3. API Endpoints

**Configuration Management:**
- `GET /edge_client/api/detection-config/list` - List all configurations
- `GET /edge_client/api/detection-config/active` - Get active configuration
- `GET /edge_client/api/detection-config/<id>` - Get specific configuration
- `POST /edge_client/api/detection-config/create` - Create new configuration
- `PUT /edge_client/api/detection-config/<id>/update` - Update configuration
- `POST /edge_client/api/detection-config/<id>/activate` - Activate configuration
- `DELETE /edge_client/api/detection-config/<id>/delete` - Delete configuration

### 4. Dashboard Updates

The monitoring dashboard now displays:
- Active detection method selector
- Configuration details (method, frequency, harmonics, threshold)
- Detection confidence and status for each event
- SNR values in dB
- Direction of Arrival angles
- Detection method badges

### 5. Admin Interface

DetectionConfig model is registered in Django admin with:
- List view with key parameters
- Detailed edit form with organized fieldsets
- Automatic `is_active` enforcement (only one active at a time)
- Auto-populated `created_by` field

## Installation & Setup

### Step 1: Install Dependencies

```bash
cd django_echoshield
pip install -r requirements.txt
```

The following packages are required:
- Django >= 4.2
- numpy >= 1.24.0
- scipy >= 1.11.0
- djangorestframework >= 3.14.0

### Step 2: Create Database Migrations

```bash
python manage.py makemigrations core
python manage.py migrate
```

This will create:
- `DetectionConfig` table
- New fields in `Event` table

### Step 3: Initialize Default Configurations

```bash
python manage.py init_detection_configs
```

This creates four default configurations:
1. **Default Combined** (active) - Balanced multi-evidence detection
2. **Energy Likelihood Only** - SNR-focused detection
3. **GCC-PHAT DOA** - Angle estimation focused
4. **High Sensitivity** - Low threshold for weak signals

### Step 4: Start the Server

```bash
python manage.py runserver
```

Access the dashboard at: `http://localhost:8000/monitoring/dashboard`

## Usage Guide

### Selecting a Detection Method

1. Navigate to the dashboard at `/monitoring/dashboard`
2. In the "Detection Configuration" section, use the dropdown to select a method
3. Confirm the activation when prompted
4. The configuration details will update automatically

### Creating Custom Configurations

#### Via Django Admin:

1. Go to `/admin/core/detectionconfig/`
2. Click "Add Detection Configuration"
3. Fill in the parameters:
   - **Config Name**: Unique identifier
   - **Method**: Choose detection method
   - **Is Active**: Check to make this the active config
   - **Fundamental Freq**: Expected drone propeller frequency (Hz)
   - **N Harmonics**: Number of harmonics to analyze (5-10 recommended)
   - **Confidence Threshold**: Detection threshold (0.60-0.90)
   - **Frequency Band**: Analysis frequency range
   - **Evidence Weights**: Adjust SNR/Harmonic/Temporal balance
   - **Mic Spacing**: Distance between microphones for DOA (meters)
4. Save the configuration

#### Via API:

```bash
curl -X POST http://localhost:8000/edge_client/api/detection-config/create \
  -H "Content-Type: application/json" \
  -d '{
    "config_name": "Custom Quadcopter",
    "method": "combined",
    "is_active": false,
    "fundamental_freq_hz": 180.0,
    "n_harmonics": 8,
    "confidence_threshold": 0.80,
    "freq_band_low_hz": 150.0,
    "freq_band_high_hz": 4000.0,
    "harmonic_bandwidth_hz": 35.0,
    "mic_spacing_m": 0.12
  }'
```

### Understanding Detection Results

#### Dashboard Metrics:

- **Method**: The signal processing method used
- **Detected**: YES/NO based on confidence threshold
- **Confidence**: Overall detection confidence (0.0-1.0)
- **SNR (dB)**: Signal-to-Noise Ratio (higher is better)
- **Angle (°)**: Direction of Arrival (-90° to +90°)
  - 0° = broadside (perpendicular to mic array)
  - Positive = right side
  - Negative = left side

#### Confidence Interpretation:

- **0.75-1.00**: High confidence detection (green)
- **0.50-0.75**: Medium confidence (yellow)
- **0.00-0.50**: Low confidence (red)

## Signal Processing Methods Explained

### 1. Energy Likelihood Detector

**Best for**: Robust detection with low false alarms

**How it works**:
- Analyzes SNR in harmonic bands vs. noise bands
- Validates harmonic pattern integrity
- Requires temporal stability across multiple frames
- Combines three weighted evidence scores

**Parameters to tune**:
- `weight_snr`: Emphasize signal strength (0.4 default)
- `weight_harmonic`: Emphasize pattern matching (0.3 default)
- `weight_temporal`: Emphasize persistence (0.3 default)
- `temporal_window`: Frames for smoothing (5-10 recommended)

### 2. GCC-PHAT Direction of Arrival

**Best for**: Stereo audio with angle estimation

**How it works**:
- Computes time-difference-of-arrival between microphones
- Uses phase transform for robustness to reverberation
- Estimates angle from TDOA via arcsin formula

**Parameters to tune**:
- `mic_spacing_m`: Distance between mics (0.10-0.30 m)
  - Smaller spacing: better for high frequencies
  - Larger spacing: better for low frequencies

**Requirements**:
- Stereo audio (2 channels)
- Known microphone spacing
- Far-field sound source (distance >> mic spacing)

### 3. Harmonic Filter

**Best for**: Noise reduction preprocessing

**How it works**:
- Creates band-pass masks around expected harmonics
- Zeros out non-harmonic frequency bins
- Enhances drone signature, suppresses noise

**Parameters to tune**:
- `harmonic_bandwidth_hz`: Width of each harmonic band (20-60 Hz)
  - Wider: more tolerant to RPM variations
  - Narrower: better noise rejection

### 4. Combined Method

**Best for**: Maximum reliability

**How it works**:
- Applies harmonic filtering
- Runs energy likelihood detection
- Estimates DOA if stereo
- Provides comprehensive metrics

**Trade-offs**:
- Highest accuracy
- More computational cost
- Requires tuning multiple parameters

## Configuration Parameters Reference

### Core Parameters

| Parameter | Description | Typical Range | Default |
|-----------|-------------|---------------|---------|
| `fundamental_freq_hz` | Expected propeller frequency | 50-250 Hz | 150 Hz |
| `n_harmonics` | Number of harmonics to analyze | 5-10 | 7 |
| `confidence_threshold` | Detection decision threshold | 0.60-0.90 | 0.75 |

### Frequency Band

| Parameter | Description | Typical Range | Default |
|-----------|-------------|---------------|---------|
| `freq_band_low_hz` | Lower frequency bound | 50-200 Hz | 100 Hz |
| `freq_band_high_hz` | Upper frequency bound | 2000-8000 Hz | 5000 Hz |
| `harmonic_bandwidth_hz` | Bandwidth per harmonic | 20-60 Hz | 40 Hz |

### SNR Parameters

| Parameter | Description | Typical Range | Default |
|-----------|-------------|---------------|---------|
| `snr_min_db` | Minimum SNR for normalization | -5 to 5 dB | 0 dB |
| `snr_max_db` | Maximum SNR for normalization | 25-40 dB | 30 dB |
| `harmonic_min_snr_db` | Minimum SNR per harmonic | 2-6 dB | 3 dB |

### Temporal Parameters

| Parameter | Description | Typical Range | Default |
|-----------|-------------|---------------|---------|
| `temporal_window` | Frames for smoothing | 3-10 | 5 |

### Evidence Weights

| Parameter | Description | Typical Range | Default |
|-----------|-------------|---------------|---------|
| `weight_snr` | Weight for SNR evidence | 0.0-1.0 | 0.4 |
| `weight_harmonic` | Weight for harmonic evidence | 0.0-1.0 | 0.3 |
| `weight_temporal` | Weight for temporal evidence | 0.0-1.0 | 0.3 |

*Note: Weights should sum to approximately 1.0*

### DOA & Framing

| Parameter | Description | Typical Range | Default |
|-----------|-------------|---------------|---------|
| `mic_spacing_m` | Microphone spacing | 0.05-0.30 m | 0.14 m |
| `frame_length_ms` | Frame duration | 32-128 ms | 64 ms |
| `hop_length_ms` | Frame overlap step | 16-64 ms | 32 ms |

## Tuning Guide

### For High Precision (Low False Alarms)

- Increase `confidence_threshold` to 0.85-0.90
- Increase `temporal_window` to 7-10
- Increase `harmonic_min_snr_db` to 5-6 dB
- Use narrower `harmonic_bandwidth_hz` (25-35 Hz)
- Increase `weight_harmonic` to 0.4-0.5

### For High Recall (Catch Weak Signals)

- Decrease `confidence_threshold` to 0.60-0.70
- Decrease `harmonic_min_snr_db` to 2-3 dB
- Widen `harmonic_bandwidth_hz` to 50-60 Hz
- Decrease `temporal_window` to 3-5
- Increase `weight_snr` to 0.5-0.6

### For Specific Drone Types

**Quadcopters (100-200 Hz)**:
- `fundamental_freq_hz`: 150-180 Hz
- `n_harmonics`: 7-8
- `freq_band_high_hz`: 3000-4000 Hz

**Larger Drones (50-120 Hz)**:
- `fundamental_freq_hz`: 80-100 Hz
- `n_harmonics`: 8-10
- `freq_band_high_hz`: 2000-3000 Hz

## Troubleshooting

### No Detections Appearing

1. Check if a configuration is active:
   ```bash
   curl http://localhost:8000/edge_client/api/detection-config/active
   ```

2. Lower the confidence threshold temporarily
3. Check dashboard for SNR values - if consistently low, adjust `snr_min_db`

### Too Many False Alarms

1. Increase `confidence_threshold`
2. Increase `temporal_window`
3. Tune `fundamental_freq_hz` to match actual drone

### Inaccurate Angle Estimates

1. Verify `mic_spacing_m` is correct
2. Ensure stereo audio is properly aligned
3. Check for spatial aliasing (spacing should be < λ/2 at max frequency)

### High CPU Usage

1. Use `energy_likelihood` method instead of `combined`
2. Decrease `n_harmonics`
3. Increase `hop_length_ms` (less overlap)

## File Structure

```
django_echoshield/
├── core/
│   ├── models.py                      # DetectionConfig and Event models
│   ├── admin.py                       # Admin interface registration
│   └── management/commands/
│       └── init_detection_configs.py  # Default config initialization
├── edge_client/
│   ├── detection_processor.py         # Main detection processor
│   ├── energy_likelihood_detector.py  # Multi-evidence detector
│   ├── gcc_phat_doa.py               # DOA estimation
│   ├── framing_windowing.py          # Audio framing
│   ├── fft.py                        # FFT analysis
│   ├── harmonic_filter.py            # Harmonic filtering
│   ├── config_views.py               # Configuration API views
│   ├── views.py                      # Edge client views
│   └── urls.py                       # URL routing
├── monitoring/
│   └── views.py                      # Dashboard view
└── templates/
    └── monitoring/
        └── dashboard.html            # Dashboard template
```

## API Examples

### Get Active Configuration

```bash
curl http://localhost:8000/edge_client/api/detection-config/active
```

Response:
```json
{
  "status": "ok",
  "config": {
    "id": 1,
    "config_name": "Default Combined",
    "method": "combined",
    "method_display": "Combined Multi-Evidence",
    "is_active": true,
    "fundamental_freq_hz": 150.0,
    "n_harmonics": 7,
    "confidence_threshold": 0.75,
    ...
  }
}
```

### Activate a Configuration

```bash
curl -X POST http://localhost:8000/edge_client/api/detection-config/2/activate
```

### List All Configurations

```bash
curl http://localhost:8000/edge_client/api/detection-config/list
```

## Next Steps

To actually use this signal processing in your edge application:

1. **Integrate with Audio Capture**: Modify your edge client to capture audio and pass it to `DetectionProcessor`
2. **Update Event Creation**: When creating events, include detection metrics from the processor
3. **Real-time Processing**: Set up a processing pipeline that runs continuously
4. **Performance Optimization**: Profile and optimize for your target hardware

Example integration:
```python
from edge_client.detection_processor import DetectionProcessor
from core.models import DetectionConfig

# Get active configuration
config = DetectionConfig.objects.get(is_active=True)
config_dict = {
    'method': config.method,
    'fundamental_freq_hz': config.fundamental_freq_hz,
    # ... other parameters
}

# Create processor
processor = DetectionProcessor(config_dict)

# Process audio
result = processor.process_audio(audio_array, sampling_rate, is_stereo=True)

# Use results to create Event
event = Event.objects.create(
    detection_method=result.detection_method,
    detection_confidence=result.confidence,
    snr_db=result.snr_db,
    doa_angle_deg=result.doa_angle_deg,
    # ... other fields
)
```

## References

- Energy Likelihood Detector: See `drone_detection_angle/energy_likelihood_detector.py`
- GCC-PHAT Algorithm: See `drone_detection_angle/gcc_phat_doa.py`
- Main Pipeline: See `drone_detection_angle/main_drone_detector.py`
