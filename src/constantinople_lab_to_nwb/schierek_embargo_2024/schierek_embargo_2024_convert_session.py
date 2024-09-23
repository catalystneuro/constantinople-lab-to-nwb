"""Primary script to run to convert an entire session for of data using the NWBConverter."""

import os
from pathlib import Path
from typing import Union, Optional

from dateutil import tz
from neuroconv.datainterfaces import OpenEphysRecordingInterface
from neuroconv.utils import load_dict_from_file, dict_deep_update
from spikeinterface.extractors import OpenEphysBinaryRecordingExtractor

from constantinople_lab_to_nwb.schierek_embargo_2024 import SchierekEmbargo2024NWBConverter


def session_to_nwb(
    openephys_recording_folder_path: Union[str, Path],
    spike_sorting_folder_path: Union[str, Path],
    processed_spike_sorting_file_path: Union[str, Path],
    raw_behavior_file_path: Union[str, Path],
    nwbfile_path: Union[str, Path],
    column_name_mapping: Optional[dict] = None,
    column_descriptions: Optional[dict] = None,
    stub_test: bool = False,
    overwrite: bool = False,
):
    """
    Convert a session of data to NWB format.

    Parameters
    ----------
    openephys_recording_folder_path : str or Path
        The path to the OpenEphys recording folder.
    spike_sorting_folder_path : str or Path
        The path to the Phy sorting folder.
    processed_spike_sorting_file_path : str or Path
        The path to the processed spike sorting file (.mat).
    nwbfile_path : str or Path
        The path to the NWB file to write.
    stub_test : bool, default: False
        Whether to run a stub test conversion.
    overwrite : bool, default: False
        Whether to overwrite an existing NWB file.
    """
    recording_folder_path = Path(openephys_recording_folder_path)

    source_data = dict()
    conversion_options = dict()

    # Add Recording
    stream_names = OpenEphysRecordingInterface.get_stream_names(folder_path=openephys_recording_folder_path)
    stream_name_raw = [stream_name for stream_name in stream_names if "AP" in stream_name][0]
    stream_name_lfp = [stream_name for stream_name in stream_names if "LFP" in stream_name][0]

    source_data.update(
        dict(
            RecordingAP=dict(folder_path=openephys_recording_folder_path, stream_name=stream_name_raw),
            RecordingLFP=dict(folder_path=openephys_recording_folder_path, stream_name=stream_name_lfp),
        ),
    )
    conversion_options.update(
        dict(
            RecordingAP=dict(stub_test=stub_test),
            RecordingLFP=dict(stub_test=stub_test, write_as="lfp"),
        ),
    )

    # Add Sorting
    source_data.update(dict(PhySorting=dict(folder_path=spike_sorting_folder_path)))
    conversion_options.update(dict(PhySorting=dict(stub_test=False)))

    # Add processed sorting output
    if processed_spike_sorting_file_path is not None:
        # Retrieve the sampling frequency from the raw data
        recording_extractor = OpenEphysBinaryRecordingExtractor(
            folder_path=openephys_recording_folder_path, stream_name=stream_name_raw
        )
        sampling_frequency = recording_extractor.get_sampling_frequency()
        source_data.update(
            dict(
                ProcessedSorting=dict(
                    file_path=processed_spike_sorting_file_path, sampling_frequency=sampling_frequency
                ),
                ProcessedBehavior=dict(
                    file_path=processed_spike_sorting_file_path,
                ),
            )
        )
        conversion_options.update(dict(ProcessedSorting=dict(write_as="processing", stub_test=False)))
        conversion_options.update(
            dict(
                ProcessedBehavior=dict(column_name_mapping=column_name_mapping, column_descriptions=column_descriptions)
            )
        )

    # Add Behavior
    source_data.update(dict(RawBehavior=dict(file_path=raw_behavior_file_path)))
    # Exclude some task arguments from the trials table that are the same for all trials
    task_arguments_to_exclude = [
        "BlockLengthTest",
        "BlockLengthAd",
        "TrialsStage2",
        "TrialsStage3",
        "TrialsStage4",
        "TrialsStage5",
        "TrialsStage6",
        "TrialsStage8",
        "CTrial",
        "HiITI",
    ]
    conversion_options.update(dict(RawBehavior=dict(task_arguments_to_exclude=task_arguments_to_exclude)))

    recording_folder_name = recording_folder_path.stem
    subject_id, session_id = recording_folder_name.split("_", maxsplit=1)

    converter_kwargs = dict(source_data=source_data)

    # Look for probeinterface json file
    probe_group_file_paths = list(recording_folder_path.rglob(f"{subject_id}*.json"))
    if len(probe_group_file_paths) == 1:
        probe_group_file_path = probe_group_file_paths[0]
        converter_kwargs.update(
            probe_group_file_path=str(probe_group_file_path),
            probe_properties=["contact_shapes", "width"],
        )

    converter = SchierekEmbargo2024NWBConverter(**converter_kwargs, verbose=True)

    # Add datetime to conversion
    metadata = converter.get_metadata()
    session_start_time = metadata["NWBFile"]["session_start_time"]
    tzinfo = tz.gettz("America/New_York")
    metadata["NWBFile"].update(
        session_start_time=session_start_time.replace(tzinfo=tzinfo),
        session_id=session_id,
        # TODO: add protocol name for behavior task
    )

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "schierek_embargo_2024_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Update behavior metadata
    behavior_metadata_path = Path(__file__).parent / "metadata" / "schierek_embargo_2024_behavior_metadata.yaml"
    behavior_metadata = load_dict_from_file(behavior_metadata_path)
    metadata = dict_deep_update(metadata, behavior_metadata)

    metadata["Subject"].update(subject_id=subject_id)

    # Run conversion
    converter.run_conversion(
        nwbfile_path=nwbfile_path,
        metadata=metadata,
        conversion_options=conversion_options,
        overwrite=overwrite,
    )


if __name__ == "__main__":

    # Parameters for conversion
    openephys_recording_folder_path = Path("/Volumes/T9/Constantinople/Ephys Data/J076_2023-12-12_14-52-04/")
    phy_sorting_folder_path = (
        openephys_recording_folder_path / "Record Node 117/experiment1/recording1/continuous/Neuropix-PXI-119.ProbeA-AP"
    )
    processed_sorting_file_path = Path("/Volumes/T9/Constantinople/Ephys Data/J076_2023-12-12.mat")
    bpod_file_path = Path("/Volumes/T9/Constantinople/raw_Bpod/J076/DataFiles/J076_RWTautowait2_20231212_145250.mat")

    # The column name mapping is used to rename the columns in the processed data to more descriptive column names. (optional)
    column_name_mapping = dict(
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
    # The column descriptions are used to add descriptions to the columns in the processed data. (optional)
    column_descriptions = dict(
        hits="Whether the subject received reward for each trial.",
        vios="Whether the subject violated the trial by not maintaining center poke for the time required by 'nose_in_center'.",
        optout="Whether the subject opted out for each trial.",
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

    nwbfile_path = Path("/Volumes/T9/Constantinople/nwbfiles/J076_2023-12-12_14-52-04.nwb")
    if not nwbfile_path.parent.exists():
        os.makedirs(nwbfile_path.parent, exist_ok=True)

    stub_test = True
    overwrite = True

    session_to_nwb(
        openephys_recording_folder_path=openephys_recording_folder_path,
        spike_sorting_folder_path=phy_sorting_folder_path,
        processed_spike_sorting_file_path=processed_sorting_file_path,
        raw_behavior_file_path=bpod_file_path,
        column_name_mapping=column_name_mapping,
        column_descriptions=column_descriptions,
        nwbfile_path=nwbfile_path,
        stub_test=stub_test,
        overwrite=overwrite,
    )
