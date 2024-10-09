# Notes concerning the schierek_embargo_2024 conversion

## Neuropixels project

In this project, the same behavior task is performed (as in mah_2024 conversion, see [notes](https://github.com/catalystneuro/constantinople-lab-to-nwb/blob/58892fa996e0310c9a3047731484bed3ba0a111d/src/constantinople_lab_to_nwb/mah_2024/mah_2024_notes.md)) while
 Neuropixels records extracellular electrophysiology from ~20 rats.

Synchronization is performed with an Arduino that
sends bar codes to both the B-Pod system and the OpenEphys system.

This experiment type includes:
* Electrophysiology recordings from the OpenEphys acquisition system
* Output from Kilosort for automated spike sorting and Phy for manual curation

### Processed Ephys data

The processed ephys data is stored in custom .mat files (e.g. `J076_2023-12-12.mat`) with the following fields:

The "SU" struct is a cell array of all individual cells simultaneously recorded by neuropixels in this session.

- `SU` (1 x num_units)
  - `cluster_id` – The cluster ID denoted by Phy (matches `original_cluster_id` in the units table)
  - `st` – The times of each spike in seconds
  - `rec_channel` – The channel on the neuropixels probe that the cell was recorded on (1-indexed)
  - `probe_channel` - The channel on the neuropixels probe that the cell was recorded on (1-indexed)
  - `channel_depth` – The distance of the channel from the tip of the neuropixels probe in micrometers
  - `hmat` – struct of task event aligned firing rates. CON: center light on, COFF: center light off, SON: side light on, SOFF: side light off, Rew: reward port poke after reward delivery, Opt: opt out port poked. (ntrials x ntime bins)
  - `xvec` – struct of task event aligned time bins in seconds. (1 x ntime)
  - `location` – denotes whether the cell is located within the LO or elsewhere in the frontal cortex.
  - `umDistFromL1` – distance from L1 in microns
  - `AP` – anterior/posterior neuropixels probe location relative to Bregma
  - `ML` – medial/lateral neuropixels probe location relative to Bregma
