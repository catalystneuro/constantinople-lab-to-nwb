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

#### TimeIntervals

We are adding the processed trials data to the NWB file as [TimeIntervals](https://pynwb.readthedocs.io/en/stable/pynwb.epoch.html).
The `processed_trials` table will be stored in the `intervals` group in the NWB file.

The `schierek_embargo_2024.session_to_nwb()` function uses the `column_name_mapping` and `column_descriptions` dictionaries
to map the processed data to the NWB file. The `column_name_mapping` is used to rename the columns in the processed data
to more descriptive column names. The `column_descriptions` are used to provide a description of each column in the processed data.

```python
# The column name mapping is used to rename the columns in the processed data to more descriptive column names. (optional)
column_name_mapping = dict(
    NoseInCenter="nose_in_center",
    TrainingStage="training_stage",
    Block="block_type",
    BlockLengthAd="num_trials_in_adaptation_blocks",
    BlockLengthTest="num_trials_in_test_blocks",
    ProbCatch="catch_percentage",
    RewardDelay="reward_delay",
    RewardAmount="reward_volume_ul",
    WaitForPoke="wait_for_center_poke",
    hits="is_rewarded",
    vios="is_violation",
    optout="is_opt_out",
    wait_time="wait_time",
    wait_thresh="wait_time_threshold",
    wait_for_cpoke="wait_for_center_poke",
    zwait_for_cpoke="z_scored_wait_for_center_poke",
    RewardedSide="rewarded_port",
    Cled="center_poke_times",
    Lled="left_poke_times",
    Rled="right_poke_times",
    l_opt="left_opt_out_times",
    r_opt="right_opt_out_times",
    ReactionTime="reaction_time",
    slrt="short_latency_reaction_time",
    iti="inter_trial_interval",
)

column_descriptions = dict(
    NoseInCenter="The time in seconds when the animal is required to maintain center port to initiate the trial (uniformly drawn from 0.8 - 1.2 seconds).",
    TrainingStage="The stage of the training.",
    Block="The block type (High, Low or Test). High and Low blocks are high reward (20, 40, or 80μL) or low reward (5, 10, or 20μL) blocks. Test blocks are mixed blocks.",
    BlockLengthAd="The number of trials in each high reward (20, 40, or 80μL) or low reward (5, 10, or 20μL) blocks.",
    BlockLengthTest="The number of trials in each mixed blocks.",
    ProbCatch="The percentage of catch trials.",
    RewardDelay="The delay in seconds to receive reward, drawn from exponential distribution with mean = 2.5 seconds.",
    RewardAmount="The volume of reward in microliters.",
    hits="Whether the subject received reward for each trial.",
    vios="Whether the subject violated the trial by not maintaining center poke for the time required by 'nose_in_center'.",
    optout="Whether the subject opted out for each trial.",
    WaitForPoke="The time (s) between side port poke and center poke.",
    wait_time="The wait time for the subject for for each trial in seconds, after removing outliers."
        " For hit trials (when reward was delivered) the wait time is equal to the reward delay."
        " For opt-out trials, the wait time is equal to the time waited from trial start to opting out.",
    wait_for_cpoke="The time between side port poke and center poke in seconds, includes the time when the subject is consuming the reward.",
    zwait_for_cpoke="The z-scored wait_for_cpoke using all trials.",
    RewardedSide="The rewarded port (Left or Right) for each trial.",
    Cled="The time of center port LED on/off for each trial (2 x ntrials).",
    Lled="The time of left port LED on/off for each trial (2 x ntrials).",
    Rled="The time of right port LED on/off for each trial (2 x ntrials).",
    l_opt="The time of left port entered/exited for each trial (2 x ntrials).",
    r_opt="The time of right port entered/exited for each trial (2 x ntrials).",
    ReactionTime="The reaction time in seconds.",
    slrt="The short-latency reaction time in seconds.",
    iti="The time to initiate trial in seconds (the time between the end of the consummatory period and the time to initiate the next trial).",
    wait_thresh="The threshold in seconds to remove wait-times (mean + 1*std of all cumulative wait-times).",
)
```

### Temporal alignment

1. Align trial-base relative timestamps to Raw Bpod trial start time:
For each trial sum all relative timestamps to the respective trial start time

2. Align TTL signals to Raw Bpod trial times:
Compute the time shift from global center port timestamps (`global_center_port_times`) to the aligned center port timestamps.
The aligned center port times can be accessed from the processed behavior data using the `"Cled"` field.

```python
from ndx_structured_behavior.utils import loadmat

bpod_data = loadmat("path/to/bpod_session.mat")["SessionData"] # should contain "SessionData" named struct
S_struct_data = loadmat("path/to/processed_behavior.mat")["S"] # should contain "S" named struct

bpod_trial_start_times = bpod_data['TrialStartTimestamp']
num_trials = len(bpod_trial_start_times)
global_center_port_times = []
for i in range(num_trials):
  center_port_relative_start_time = bpod_data["RawEvents"]["Trial"][i]["States"]["NoseInCenter"][0]
  bpod_global_start_times = bpod_trial_start_times[i] + center_port_relative_start_time
  global_center_port_times.append(bpod_global_start_times)

# "Cled" field contains the aligned onset and offset times for each trial [2 x ntrials]
center_port_aligned_onset_times = [center_port_times[0] for center_port_times in S_struct_data["Cled"]]
time_shift = global_center_port_times[0] - center_port_aligned_onset_times[0]
```

We are using this computed time shift to shift the ephys timestamps.


### Mapping to NWB

The following UML diagram shows the mapping of source data to NWB.

![nwb mapping](schierek_embargo_2024_uml.png)
