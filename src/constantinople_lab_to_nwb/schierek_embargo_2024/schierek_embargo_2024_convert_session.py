"""Primary script to run to convert an entire session for of data using the NWBConverter."""

import os
from pathlib import Path
from typing import Union, Optional

import numpy as np
import pandas as pd
from dateutil import tz
from neuroconv.datainterfaces import OpenEphysRecordingInterface
from neuroconv.utils import load_dict_from_file, dict_deep_update
from nwbinspector import inspect_nwbfile, save_report, format_messages
from pymatreader import read_mat
from spikeinterface.extractors import OpenEphysBinaryRecordingExtractor

from constantinople_lab_to_nwb.utils import get_subject_metadata_from_rat_info_folder
from constantinople_lab_to_nwb.schierek_embargo_2024 import SchierekEmbargo2024NWBConverter


def update_ephys_device_metadata_for_subject(
    epys_registry_file_path: Union[str, Path],
    subject_id: str,
    metadata: dict,
):
    if not os.path.exists(epys_registry_file_path):
        raise FileNotFoundError(f"File not found: {epys_registry_file_path}")

    ephys_registry = read_mat(epys_registry_file_path)
    if "Registry" not in ephys_registry:
        raise ValueError(f"'Registry' key not found in {epys_registry_file_path}.")
    ephys_registry = pd.DataFrame(ephys_registry["Registry"])
    if "ratname" not in ephys_registry.columns:
        raise ValueError(f"'ratname' column not found in {epys_registry_file_path}.")
    filtered_ephys_registry = ephys_registry[ephys_registry["ratname"] == subject_id]

    if not filtered_ephys_registry.empty:
        ap_value = filtered_ephys_registry["AP"].values[0]
        ml_value = filtered_ephys_registry["ML"].values[0]
        dv_value = filtered_ephys_registry["DV"].values[0]

        coordinates_in_mm = f"AP: {ap_value} mm, ML: {ml_value} mm"
        if not np.isnan(dv_value):
            coordinates_in_mm += f", DV: {dv_value}."

        recording_hemisphere = filtered_ephys_registry["recordinghemisphere"].values[0]
        recording_hemisphere = dict(L="left", R="right").get(recording_hemisphere, recording_hemisphere)
        probe_type = filtered_ephys_registry["probetype"].values[0]

        brain_region = filtered_ephys_registry["recordingsite"].values[0]
        description = f"The {probe_type} probe implanted in {brain_region} brain region, at {coordinates_in_mm}, {recording_hemisphere} hemisphere."
        if "distance2LO" in filtered_ephys_registry.columns:
            distance_to_LO_um = filtered_ephys_registry["distance2LO"].values[0]
            # TODO: confirm unit
            description += f" Distance to LO: {distance_to_LO_um} μm."

        metadata["Ecephys"]["Device"][0].update(
            description=description,
        )

    return metadata


def session_to_nwb(
    openephys_recording_folder_path: Union[str, Path],
    ap_stream_name: str,
    lfp_stream_name: str,
    processed_spike_sorting_file_path: Union[str, Path],
    raw_behavior_file_path: Union[str, Path],
    nwbfile_path: Union[str, Path],
    subject_metadata: dict,
    column_name_mapping: Optional[dict] = None,
    column_descriptions: Optional[dict] = None,
    ephys_registry_file_path: Optional[Union[str, Path]] = None,
    stub_test: bool = False,
    overwrite: bool = False,
    verbose: bool = True,
):
    """
    Convert a session of data to NWB format.

    Parameters
    ----------
    openephys_recording_folder_path : str or Path
        The path to the OpenEphys recording folder.
    ap_stream_name: str
        The name of the recording stream containing the raw data.
    lfp_stream_name: str, optional
        The name of the recording stream containing the processed data.
    processed_spike_sorting_file_path : str or Path
        The path to the processed spike sorting file (.mat).
    raw_behavior_file_path : str or Path
        The path to the Bpot output file (.mat).
    nwbfile_path : str or Path
        The path to the NWB file to write.
    column_name_mapping : dict
        A dictionary to rename the columns in the processed behavior data to more descriptive column names.
    column_descriptions : dict
        A dictionary to add descriptions to the columns in the processed behavior data.
    ephys_registry_file_path: str or Path
        The path to the ephys registry (.mat) file.
    subject_metadata: dict
        Additional subject metadata. e.g. dict(date_of_birth="2020-05-27T00:00:00+02:00", sex="F")
    stub_test : bool, default: False
        Whether to run a stub test conversion.
    overwrite : bool, default: False
        Whether to overwrite an existing NWB file.
    verbose : bool, default: True
        Whether to print verbose output.
    """
    recording_folder_path = Path(openephys_recording_folder_path)

    record_node_name = recording_folder_path.stem
    if "Record Node" not in record_node_name:
        raise ValueError(
            f"The recording folder path should contain the Record Node number. E.g. '{recording_folder_path}/Record Node 117'."
        )

    source_data = dict()
    conversion_options = dict()

    # Add Recording
    stream_names = OpenEphysRecordingInterface.get_stream_names(folder_path=recording_folder_path)
    raw_stream_names = [stream_name for stream_name in stream_names if ap_stream_name in stream_name]
    if len(raw_stream_names) != 1:
        raise ValueError(f"Could not find '{ap_stream_name}' recording stream in {stream_names}. ")
    raw_stream_name = raw_stream_names[0]

    lfp_stream_names = [stream_name for stream_name in stream_names if lfp_stream_name in stream_name]
    if len(lfp_stream_names) != 1:
        raise ValueError(f"Could not find '{lfp_stream_name}' stream in {stream_names}. ")
    processed_stream_name = lfp_stream_names[0]

    source_data.update(
        dict(
            RecordingAP=dict(
                folder_path=str(recording_folder_path), stream_name=raw_stream_name, es_key="electrical_series"
            ),
            RecordingLFP=dict(
                folder_path=str(recording_folder_path),
                stream_name=processed_stream_name,
                es_key="lfp_electrical_series",
            ),
        ),
    )
    conversion_options.update(
        dict(
            RecordingAP=dict(stub_test=stub_test),
            RecordingLFP=dict(stub_test=stub_test, write_as="lfp"),
        ),
    )

    # Add Sorting
    ap_folder_name = raw_stream_name.replace(f"{record_node_name}#", "")
    phy_sorting_folder_path = recording_folder_path / f"experiment1/recording1/continuous/{ap_folder_name}"
    if not phy_sorting_folder_path.exists():
        raise FileNotFoundError(
            f"The folder '{phy_sorting_folder_path}' where the Phy output should be located does not exist."
        )
    source_data.update(dict(PhySorting=dict(folder_path=phy_sorting_folder_path)))
    conversion_options.update(
        dict(
            PhySorting=dict(
                stub_test=False,
                units_description="Units table with spike times from Kilosort 2.5 and manually curated using Phy.",
            )
        )
    )

    # Add processed sorting output
    # The processed spike sorting file also contains the processed trials data.
    recording_extractor = OpenEphysBinaryRecordingExtractor(
        folder_path=openephys_recording_folder_path,
        stream_name=raw_stream_name,
    )
    sampling_frequency = recording_extractor.get_sampling_frequency()
    source_data.update(
        dict(
            ProcessedSorting=dict(file_path=processed_spike_sorting_file_path, sampling_frequency=sampling_frequency),
            ProcessedBehavior=dict(
                file_path=processed_spike_sorting_file_path,
            ),
        )
    )
    conversion_options.update(
        dict(
            ProcessedSorting=dict(
                write_as="processing", stub_test=False, units_description="The curated single-units from Phy."
            ),
        ),
    )
    conversion_options.update(
        dict(ProcessedBehavior=dict(column_name_mapping=column_name_mapping, column_descriptions=column_descriptions))
    )

    # Add Behavior
    source_data.update(dict(RawBehavior=dict(file_path=raw_behavior_file_path)))
    # Exclude some task arguments from the trials table that are the same for all trials
    task_arguments_to_exclude = [
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

    subject_id, session_id = Path(raw_behavior_file_path).stem.split("_", maxsplit=1)
    protocol = session_id.split("_")[0]

    converter_kwargs = dict(source_data=source_data)

    # Look for probeinterface json file
    probe_group_file_paths = list(recording_folder_path.rglob(f"{subject_id}*.json"))
    if len(probe_group_file_paths) == 1:
        probe_group_file_path = probe_group_file_paths[0]
        converter_kwargs.update(
            probe_group_file_path=str(probe_group_file_path),
            probe_properties=["contact_shapes", "width"],
        )

    converter = SchierekEmbargo2024NWBConverter(**converter_kwargs, verbose=verbose)

    # Add datetime to conversion
    metadata = converter.get_metadata()
    session_start_time = metadata["NWBFile"]["session_start_time"]
    tzinfo = tz.gettz("America/New_York")
    metadata["NWBFile"].update(
        session_start_time=session_start_time.replace(tzinfo=tzinfo),
        session_id=session_id,
        protocol=protocol,
    )

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "metadata" / "schierek_embargo_2024_general_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Update behavior metadata
    behavior_metadata_path = Path(__file__).parent / "metadata" / "schierek_embargo_2024_behavior_metadata.yaml"
    behavior_metadata = load_dict_from_file(behavior_metadata_path)
    metadata = dict_deep_update(metadata, behavior_metadata)

    # Update ecephys metadata
    ephys_metadata_path = Path(__file__).parent / "metadata" / "schierek_embargo_2024_ecephys_metadata.yaml"
    ephys_metadata = load_dict_from_file(ephys_metadata_path)
    metadata = dict_deep_update(metadata, ephys_metadata)

    if "opto" in protocol.lower():
        # Load optogenetics_stimulation_metadata
        ogen_metadata_path = (
            Path(__file__).parent / "metadata" / "schierek_embargo_2024_optogenetics_stimulation_metadata.yaml"
        )
        ogen_metadata = load_dict_from_file(ogen_metadata_path)
        metadata = dict_deep_update(metadata, ogen_metadata)

    if ephys_registry_file_path is not None:
        metadata = update_ephys_device_metadata_for_subject(
            epys_registry_file_path=ephys_registry_file_path,
            subject_id=subject_id,
            metadata=metadata,
        )

    if subject_metadata is not None:
        metadata["Subject"].update(subject_id=subject_id, **subject_metadata)

    # Run conversion
    converter.run_conversion(
        nwbfile_path=nwbfile_path,
        metadata=metadata,
        conversion_options=conversion_options,
        overwrite=overwrite,
    )

    results = list(inspect_nwbfile(nwbfile_path=nwbfile_path))
    report_path = Path(nwbfile_path).parent / f"{subject_id}-{session_id}_nwbinspector_result.txt"
    if not report_path.exists():
        save_report(
            report_file_path=report_path,
            formatted_messages=format_messages(
                results,
                levels=["importance", "file_path"],
            ),
        )


if __name__ == "__main__":

    # Parameters for conversion
    openephys_recording_folder_path = Path(
        "/Volumes/T9/Constantinople/Ephys Data/J076_2023-12-12_14-52-04/Record Node 117"
    )
    # The name of the raw recording stream
    ap_stream_name = "Neuropix-PXI-119.ProbeA-AP"
    # The name of the LFP stream
    lfp_stream_name = "Neuropix-PXI-119.ProbeA-LFP"

    processed_sorting_file_path = Path("/Volumes/T9/Constantinople/Ephys Data/J076_2023-12-12.mat")
    bpod_file_path = Path("/Volumes/T9/Constantinople/raw_Bpod/J076/DataFiles/J076_RWTautowait2_20231212_145250.mat")

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
    # The column descriptions are used to add descriptions to the columns in the processed data. (optional)
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

    nwbfile_path = Path("/Users/weian/data/001264/sub-J076_ses-2023-12-12.nwb")
    if not nwbfile_path.parent.exists():
        os.makedirs(nwbfile_path.parent, exist_ok=True)

    # Ephys registry file path (constains metadata for the neuropixels probe)
    ephys_registry_file_path = "/Volumes/T9/Constantinople/Ephys Data/Ephys_registry.mat"

    stub_test = False
    overwrite = True

    # Get subject metadata from rat registry
    rat_registry_folder_path = "/Volumes/T9/Constantinople/Rat_info"
    # Query for subject_id and date of experiment.
    subject_metadata = get_subject_metadata_from_rat_info_folder(
        folder_path=rat_registry_folder_path,
        subject_id="J076",
        date="2023-12-12",
    )

    session_to_nwb(
        openephys_recording_folder_path=openephys_recording_folder_path,
        ap_stream_name=ap_stream_name,
        lfp_stream_name=lfp_stream_name,
        processed_spike_sorting_file_path=processed_sorting_file_path,
        raw_behavior_file_path=bpod_file_path,
        column_name_mapping=column_name_mapping,
        column_descriptions=column_descriptions,
        ephys_registry_file_path=ephys_registry_file_path,
        subject_metadata=subject_metadata,
        nwbfile_path=nwbfile_path,
        stub_test=stub_test,
        overwrite=overwrite,
    )
