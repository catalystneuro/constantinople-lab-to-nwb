# Notes concerning the fiber_photometry conversion

## Fiber photometry project

In this project, the same behavior task is performed (as in mah_2024 conversion, see [notes](https://github.com/catalystneuro/constantinople-lab-to-nwb/blob/58892fa996e0310c9a3047731484bed3ba0a111d/src/constantinople_lab_to_nwb/mah_2024/mah_2024_notes.md)) while
 video and fiber photometry is recorded. Video data were  acquired using cameras attached to the ceiling of behavior
rigs to capture the top-down view of the arena (Doric USB3 behavior camera, Sony IMX290, recorded with Doric Neuroscience
Studio v6 software).

To synchronize with neural recordings and Bpod task events, the camera  was connected to a digital I/O channel of a
fiber photometry console (FPC) and triggered at 30 Hz via a TTL pulse train. The remaining 3 digital I/O channels of
the FPC were connected to the 3 behavior ports to obtain TTL pulses from port LEDs turning on. The analog channels were
used to record fluorescence. Fluorescence from activity-dependent (GRABDA and GRABACh) and activity-independent
(isosbestic or mCherry) signals was acquired simultaneously via demodulation and downsampled on-the-fly by a factor of 25
to ~481.9 Hz. The recorded demodulated fluorescence was corrected for photobleaching and motion using Two-channel motion
artifact correction with mCherry or isosbestic signal as the activity-independent channel.

### Raw fiber photometry data

The raw fiber photometry data is stored in either .csv files (older version) or .doric files.

The .csv files contain the following columns:

`Time(s)` - the time in seconds
`AIn-1 - Dem (AOut-1)` - the demodulated signal from the activity-independent channel
`AIn-2 - Dem (AOut-2)` - the demodulated signal from the activity-dependent channel

The .doric files contain the following fields:

From `J097_rDAgAChDMSDLS_20240820_HJJ_0000.doric`:
`LockInAOUT01`:
    - `Time`: the time in seconds
    - `AIN02`: isosbestic signal (cord A)
    - `AIN04`: isobestic signal (cord B)

`LockInAOUT02`:
    - `Time`: the time in seconds
    - `AIN02`: demodulated signal for green indicator (cord A)
    - `AIN04`: demodulated signal for green indicator (cord B)

`LockInAOUT03`:
    - `Time`: the time in seconds
    - `AIN01`: demodulated signal for mCherry (cord A)

`LockInAOUT04`:
    - `Time`: the time in seconds
    - `AIN03`: demodulated signal for mCherry (cord B)

We are adding the demodulated signals from the .doric files to NWB as `FiberPhotometryResponseSeries`.
See the tutorial how these signals can be accessed in the NWB file [here](https://github.com/catalystneuro/constantinople-lab-to-nwb/blob/158a51dbcaa9b41d556acab39fe3a137754fedfe/src/constantinople_lab_to_nwb/fiber_photometry/tutorials/fiber_photometry_example_notebook.ipynb).

### Processed fiber photometry data

The processed fiber photometry data are stored in a `tmac.mat` files (separately for ch1 and ch2). The processed data contains the following fields:

`estimated_motion` – output of tmac, normalized and motion corrected red signal (1 x session time points)
`estimated_signal` – output of tmac, normalized signal from green, z-scored (1 x session time points)
`green` – photobleached-corrected green signal
`green_mc` – estimated_signal un-normalized
`red` – photobleached-correct red signal

The processed data is added to NWB as `FiberPhotometryProcessedSeries`.
The photobleach-corrected signals (`green` and `red`) are added as `photobleach_corrected_signal`, the un-normalized
estimated signal (`green_mc`) is added as `estimated_signal`, and the normalized and motion-corrected signals (`estimated_signal`, `estimated_motion`) are added as `normalized_estimated_signals`.
See the tutorial how these signals can be accessed in the NWB file  [here](https://github.com/catalystneuro/constantinople-lab-to-nwb/blob/158a51dbcaa9b41d556acab39fe3a137754fedfe/src/constantinople_lab_to_nwb/fiber_photometry/tutorials/fiber_photometry_example_notebook.ipynb).

### Fiber photometry metadata

The metadata for the fiber photometry data is stored in a `.yaml` file. The metadata contains information about the
fiber photometry setup, such as the LED wavelengths, dichroic mirror, and filter settings.

The metadata file is named `doric_fiber_photometry_metadata.yaml` and it contains the following fields:

For each `FiberPhotometryResponseSeries` that we add to NWB, we need to specify the following fields:
- `name` - the name of the FiberPhotometryResponseSeries
- `description` - a description of the FiberPhotometryResponseSeries
- `fiber_photometry_table_region` - the region of the FiberPhotometryTable corresponding to the signals
- `fiber_photometry_table_region_description` - a description of the region of the FiberPhotometryTable corresponding to the fluorescence signals
- `stream_names` - the names of the streams in the .doric file that correspond to the fluorescence signals (should only be specified for the demodulated signal)

Example:
```yaml
    FiberPhotometryResponseSeries:
      - name: demodulated_fiber_photometry_signal
        description: The demodulated signals from Doric.
        stream_names: ["LockInAOUT03/AIN01", "LockInAOUT04/AIN03", "LockInAOUT02/AIN02", "LockInAOUT02/AIN04"]
        fiber_photometry_table_region: [0, 1, 2, 3]
        fiber_photometry_table_region_description: The region of the FiberPhotometryTable corresponding to the estimated signal.
        unit: a.u.
```

Other example (G006_DA_20200616_CEG_0.csv)
Example:
```yaml
    FiberPhotometryResponseSeries:
      - name: demodulated_fiber_photometry_signal
        description: The demodulated (estimated) signal from light stimulation using a proprietary algorithm from Doric.
        stream_names: ["AIn-1 - Dem (AOut-1)", "AIn-2 - Dem (AOut-2)"]
        unit: a.u.
        fiber_photometry_table_region: [0, 1]
        fiber_photometry_table_region_description: The region of the FiberPhotometryTable corresponding to the estimated signal.
```

### Session start time

The session start time is the reference time for all timestamps in the NWB file. We are using `session_start_time` from the Bpod output. (The start time of the session in the Bpod data can be accessed from the "Info" struct, with "SessionDate" and "SessionStartTime_UTC" fields.)

### Bpod trial start time

We are extracting the trial start times from the Bpod output using the "TrialStartTimestamp" field.

```python
 from pymatreader import read_mat

 bpod_data = read_mat("raw_Bpod/J069/DataFiles/J069_RWTautowait2_20230809_131216.mat")["SessionData"] # should contain "SessionData" named struct

 # The trial start times from the Bpod data
 bpod_trial_start_times = bpod_data['TrialStartTimestamp']
 ```

```python
bpod_trial_start_times[:7]
>>> [ 11.4261, 104.5276, 146.0112, 203.5646, 211.7232, 215.3226, 224.041 ]
```

### Doric trial start time

The trial start times from the Doric acquisition can be obtained from one of the digital signals ("DigitalIO/DIO02" in .doric file, "DI/O-2" in .csv file).

```python
import h5py
from neuroconv.tools.signal_processing import get_rising_frames_from_ttl

doric_file = h5py.File("J069_ACh_20230809_HJJ_0002.doric", mode="r")
ttl_signal = doric_file["/DataAcquisition/FPConsole/Signals/Series0001/DigitalIO/DIO02"][:]
timestamps = doric_file["/DataAcquisition/FPConsole/Signals/Series0001/DigitalIO/Time"][:]

rising_frames_from_center_port_ttl = get_rising_frames_from_ttl(ttl_signal)
num_trials = len(rising_frames_from_center_port_ttl)
doric_trial_start_times = [timestamps[rising_frames_from_center_port_ttl][i] for i in range(num_trials)]
```

```python
doric_trial_start_times[:7]
>>> [17.11626, 110.21736, 151.702835, 209.255035, 217.41393499999998, 221.01406, 229.73321]
```

## Alignment

We are aligning the starting time of the fiber photometry (Doric), video and DLC interfaces to the Bpod interface.

We are computing the time shift from the Bpod trial start time to the Doric trial start time.

For example, the computed time shift for this session:
```python
time_shift = bpod_trial_start_times[0] - doric_trial_start_times[0]
>>> -5.6901600000000006
```

We are applying this time_shift to the timestamps for the raw fluorescence signals as:

```python
doric_timestamps = doric_file["/DataAcquisition/FPConsole/Signals/Series0001/AnalogIn/Time"][:]
aligned_timestamps = doric_timestamps + time_shift
```

1) When the time shift is negative and the first aligned timestamp of the doric trace is negative:
- shift back bpod (from every column that has a timestamp they have to be shifted back)
- shift back session start time
- don't have to move doric or video
2) When the time shift is negative and the first aligned timestamp of the doric trace is positive
- we move the doric and video backward
3) When time shift is positive
- we move the doric and video forward
