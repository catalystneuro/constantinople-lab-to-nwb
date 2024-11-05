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

### Processed behavior data

The processed behavior data is stored in custom .mat files (e.g. `J076_2023-12-12.mat`) with the following fields:

- `S`
  - `NoseInCenter` – time (s) rat was required to maintain center port to initiate the trial- uniformly drawn from [0.8 - 1.2] s (1 x ntrials). (same as `nose_in_center` in the trials table)
  - `TrainingStage` - vector for the training stage for each trial included. Value of 9 corresponds to stage 8 described in methods (1 x ntrials)
  - `Block` – block on that trial. 1: Mix block, 2: High block, 3: Low block (1 x ntrials).
  - `BlockLengthAd` - number of trials in each high or low blocks. Uniformly 40. (1 x ntrials). Same as adapt_block in A_Structs BlockLengthTest - number of trials in each mixed blocks Uniformly 40. (1 x ntrials). Same as test_block in A_Structs
  - `ProbCatch` - catch probability for that trial (1 x ntrials). Same as prob-catch in the A_Struct
  - `RewardDelay` - delay (s) on that trial to receive reward. Set to 100 for catch trials. Drawn from exponential distribution with mean = 2.5 s (1 x ntrials). Same as reward_delay in the A_struct.
  - `RewardAmount` - reward offered (uL) on that trial. [5 10 20 40 80] for males and some females, [4 8 16 32 64] for some females (1 x ntrials). Same as reward in A_struct.
  - `RewardedSide` – side of the offered reward (1 x ntrials)
  - `Hits` - logical vector for whether the rat received reward on that trial. True = reward was delivered. False = catch trials or violation trials (1 x ntrials). Same as hits in the A_struct.
  - `ReactionTime` - The reaction time in seconds
  - `Vios` - logical vector for whether the rat violated on that trial - did not maintain center poke for time required by nic. (1 x ntrials). Same as vios in the A_struct.
  - `Optout` – logical vector for whether the rat opted out of that trial. May be catch trial or optional opt outs (ntrials x 1). Same as optout in A_Struct
  - `WaitForPoke` - The time (s) between side port poke and center poke.
  - `wait_time` - wait time for the rat on that trial, after removing outliers (set by wait_thresh). For hit trials (reward was delivered), wait_time = reward_delay. For opt-out trials, wait_time = time waited from trial start to opt-ing out (1 x ntrials)
  - `iti` - time to initiate trial (s). Time between the end of the consummatory period and the time to initiate the next trial (1 x ntrials). Same as ITI in A_struct.
  - `Cled` – Time of center light on/off for each trial (2 x ntrials)
  - `Lled` – Time of reft light on/off for each trial (n x ntrials)
  - `l_opt` – Time of left port entered/exited for each trial (n x ntrials)
  - `Rled` – Time of right light on/off for each trial (n x ntrials)
  - `r_opt` – Time of left port entered/exited for each trial (n x ntrials)
  - `recordingLength` – time duration of the entire recording
  - `wait_thresh` – time threshold for wait times of engagement for this session.

### Mapping to NWB

The following UML diagram shows the mapping of the raw Bpod output to NWB.

![nwb mapping](schierek_embargo_2024_uml.png)
