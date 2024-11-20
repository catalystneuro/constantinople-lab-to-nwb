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
`AIn-1 - Raw` - the raw signal from the activity-independent channel
`AIn-2 - Dem (AOut-2)` - the demodulated signal from the activity-dependent channel
`AIn-2 - Raw` - the raw signal from the activity-dependent channel
`AIn-3` - the isosbestic signal

The .doric files contain the following fields:

![doric-example](https://private-user-images.githubusercontent.com/24475788/370304059-9858d9e1-f7d5-484c-b587-1acd093db504.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3MzIwOTcwMDQsIm5iZiI6MTczMjA5NjcwNCwicGF0aCI6Ii8yNDQ3NTc4OC8zNzAzMDQwNTktOTg1OGQ5ZTEtZjdkNS00ODRjLWI1ODctMWFjZDA5M2RiNTA0LnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNDExMjAlMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjQxMTIwVDA5NTgyNFomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTYxOWJmMDk4ZTE4NDdkYTBmMjE0Y2MyNGFmMGE1ODIyYzA2ODRlYTdhMjQzMjU0YTY5M2EzNTUxYzZlMzUxZDEmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.Aqt7bOsIMSGz7GKK_ttIjxpihAuzzUSCxxG3XqpVWPc)

For each channel group (e.g. "AnalogIn", "LockInAOUT") the timestamps for the fluosrescence signals can be accessed using the "Time" field.
The "AnalogIn" channel group contains the raw signals and the "LockIn" channel groups contain the demodulated signals.

`AnalogIn`:
    - `AIN01` - raw mCherry signal
    - `AIN02` - raw green signal
For dual-fiber experiments the following channels are also present:
    - `AIN03` - raw mCherry signal (fiber 2)
    - `AIN04` - raw green signal (fiber 2)

The channels in the "LockIn" channel group can be different from session to session. Here is an example of the channel mapping for a session:

From `J097_rDAgAChDMSDLS_20240820_HJJ_0000.doric`:
`LockInAOUT01`:
    - `Time`: the time in seconds
    - `AIN02`: isosbestic signal (fiber 1)
    - `AIN04`: isobestic signal (fiber 2)

`LockInAOUT02`:
    - `Time`: the time in seconds
    - `AIN02`: motion corrected green signal (fiber 1)
    - `AIN04`: motion corrected green signal (fiber 2)

`LockInAOUT03`:
    - `Time`: the time in seconds
    - `AIN01`: motion corrected mCherry signal (fiber 1)

`LockInAOUT04`:
    - `Time`: the time in seconds
    - `AIN03`: motion corrected mCherry signal (fiber 2)

From `J069_ACh_20230809_HJJ_0002.doric`:

TODO: what is the channel mapping here?
`AIN01xAOUT01-LockIn`:
    - `Time`: the time in seconds
    - `Values`: the isosbestic signal

`AIN01xAOUT02-LockIn`:
    - `Time`: the time in seconds
    - `Values`: motion corrected green signal

`AIN02xAOUT01-LockIn`:
    - `Time`: the time in seconds
    - `Values`: the isosbestic signal

`AIN02xAOUT02-LockIn`:
    - `Time`: the time in seconds
    - `Values`: motion corrected signal

### Fiber photometry metadata

The metadata for the fiber photometry data is stored in a `.yaml` file. The metadata contains information about the
fiber photometry setup, such as the LED wavelengths, dichroic mirror, and filter settings.

The metadata file for the .csv files is named `doric_csv_fiber_photometry_metadata.yaml` and it contains the following fields:

For each `FiberPhotometryResponseSeries` that we add to NWB, we need to specify the following fields:
- `name` - the name of the FiberPhotometryResponseSeries
- `description` - a description of the FiberPhotometryResponseSeries
- `channel_column_names` - the names of the columns in the .csv file that correspond to the fluorescence signals
- `fiber_photometry_table_region` - the region of the FiberPhotometryTable corresponding to the fluorescence signals
- `fiber_photometry_table_region_description` - a description of the region of the FiberPhotometryTable corresponding to the fluorescence signals

Example:
```yaml
    FiberPhotometryResponseSeries:
      - name: fiber_photometry_response_series
        description: The raw fluorescence signal
        channel_column_names: ["AIn-1 - Raw", "AIn-2 - Raw"]
        fiber_photometry_table_region: [0, 1]
        fiber_photometry_table_region_description: The region of the FiberPhotometryTable corresponding to the raw fluorescence signal.
      - name: fiber_photometry_response_series_isosbestic
        description: The isosbestic signal
        channel_column_names: ["AIn-3"]
        fiber_photometry_table_region: [0]
        fiber_photometry_table_region_description: The region of the FiberPhotometryTable corresponding to the isosbestic signal.
      - name: fiber_photometry_response_series_motion_corrected
        description: The motion corrected signal
        channel_column_names: ["AIn-1 - Dem (AOut-1)", "AIn-2 - Dem (AOut-2)"]
        fiber_photometry_table_region: [0, 1]
        fiber_photometry_table_region_description: The region of the FiberPhotometryTable corresponding to the motion corrected signal.
```

The metadata file for the .doric files is named `doric_fiber_photometry_metadata.yaml` and it contains the following fields:

For each `FiberPhotometryResponseSeries` that we add to NWB, we need to specify the following fields:
- `name` - the name of the FiberPhotometryResponseSeries
- `description` - a description of the FiberPhotometryResponseSeries
- `stream_names` - the names of the streams in the .doric file that correspond to the fluorescence signals
- `fiber_photometry_table_region` - the region of the FiberPhotometryTable corresponding to the fluorescence signals
- `fiber_photometry_table_region_description` - a description of the region of the FiberPhotometryTable corresponding to the fluorescence signals

Example:
```yaml
    FiberPhotometryResponseSeries:
      - name: fiber_photometry_response_series
        description: The raw fluorescence signal # TBD
        stream_names: ["AnalogIn/AIN01", "AnalogIn/AIN02", "AnalogIn/AIN03", "AnalogIn/AIN04"]
        fiber_photometry_table_region: [0, 1, 2, 3] #[0, 1]
        fiber_photometry_table_region_description: The region of the FiberPhotometryTable corresponding to the raw fluorescence signal.
      - name: fiber_photometry_response_series_isosbestic
        description: The isosbestic signal # TBD
        stream_names: ["LockInAOUT01/AIN02", "LockInAOUT01/AIN04"]
        fiber_photometry_table_region: [0, 2]
        fiber_photometry_table_region_description: The region of the FiberPhotometryTable corresponding to the isosbestic signal.
      - name: fiber_photometry_response_series_motion_corrected
        description: The motion corrected signal # TBD
        stream_names: ["LockInAOUT03/AIN01", "LockInAOUT04/AIN03", "LockInAOUT02/AIN02", "LockInAOUT02/AIN04"]
        fiber_photometry_table_region: [0, 1, 2, 3]
        fiber_photometry_table_region_description: The region of the FiberPhotometryTable corresponding to the motion corrected signal.
```
