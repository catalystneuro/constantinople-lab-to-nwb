import os
from datetime import datetime
from pathlib import Path
from typing import Union, List

from nwbinspector import inspect_all, format_messages, save_report
from pymatreader import read_mat
from tqdm import tqdm

from constantinople_lab_to_nwb.mah_2024.mah_2024_convert_session import (
    session_to_nwb,
    get_subject_metadata_from_rat_info_folder,
)

import warnings

# Suppress specific UserWarning messages
warnings.filterwarnings(
    "ignore",
    message="The linked table for DynamicTableRegion 'action_type' does not share an ancestor with the DynamicTableRegion.",
)
warnings.filterwarnings(
    "ignore",
    message="The linked table for DynamicTableRegion 'event_type' does not share an ancestor with the DynamicTableRegion.",
)
warnings.filterwarnings(
    "ignore",
    message="The linked table for DynamicTableRegion 'state_type' does not share an ancestor with the DynamicTableRegion.",
)


def _get_sessions_to_convert_from_mat(
    file_path: Union[str, Path],
    default_struct_name: str = "A",
) -> List[str]:
    """
    Get the list of sessions to convert from a .mat file.

    Parameters
    ----------
    file_path : str or Path
        The path to the .mat file.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    if ".mat" not in file_path.suffixes:
        raise ValueError(f"The file {file_path} is not a .mat file.")
    behavior_data = read_mat(str(file_path))
    if default_struct_name not in behavior_data:
        raise ValueError(f"The default struct name '{default_struct_name}' is missing from {file_path}.")

    behavior_data = behavior_data[default_struct_name]
    if "date" not in behavior_data:
        raise ValueError(f"The 'date' key is missing from {file_path}.")

    return behavior_data["date"]


def sessions_to_nwb(
    raw_behavior_folder_path: Union[str, Path],
    processed_behavior_folder_path: Union[str, Path],
    rat_info_folder_path: Union[str, Path],
    nwbfile_folder_path: Union[str, Path],
    column_name_mapping: dict = None,
    column_descriptions: dict = None,
    overwrite: bool = False,
):
    """
    Convert all sessions to NWB format.
    The number of sessions to convert is determined by the processed behavior files.
    Each processed behavior file contains data for multiple days, the 'date' key is used to identify the sessions in the raw Bpod output.

    Parameters
    ----------
    raw_behavior_folder_path: str or Path
        The path to the folder containing the raw Bpod output files.
    processed_behavior_folder_path: str or Path
        The path to the folder containing the processed behavior files.
    rat_info_folder_path: str or Path
        The path to the folder containing the rat info files.
    nwbfile_folder_path: str or Path
        The path to the folder where the NWB files will be saved.
    column_name_mapping: dict, optional
        Dictionary to map the column names in the processed behavior data to more descriptive column names.
    column_descriptions: dict, optional
        Dictionary to add descriptions to the columns in the processed behavior data.
    overwrite
        Whether to overwrite existing NWB files.
    """
    if not nwbfile_folder_path.exists():
        os.makedirs(nwbfile_folder_path, exist_ok=True)

    processed_mat_files = list(processed_behavior_folder_path.glob("*.mat"))
    subject_ids = [
        processed_behavior_file_path.stem.split("_")[-1] for processed_behavior_file_path in processed_mat_files
    ][:10]
    sessions_to_convert_per_subject = {
        subject_id: _get_sessions_to_convert_from_mat(file_path=processed_behavior_file_path)
        for subject_id, processed_behavior_file_path in zip(subject_ids, processed_mat_files)
    }

    for subject_id, processed_behavior_file_path in zip(subject_ids, processed_mat_files):
        dates_from_mat = sessions_to_convert_per_subject[subject_id]
        num_sessions_per_subject = len(dates_from_mat)
        progress_bar = tqdm(
            dates_from_mat,
            desc=f"Converting subject '{subject_id}' with {num_sessions_per_subject} sessions to NWB ...",
            position=0,
            total=num_sessions_per_subject,
            dynamic_ncols=True,
        )

        for date_from_mat in progress_bar:
            date_obj = datetime.strptime(date_from_mat, "%d-%b-%Y")
            formatted_date_str = date_obj.strftime("%Y%m%d")

            raw_behavior_file_paths = list(
                (raw_behavior_folder_path / subject_id / "DataFiles").glob(f"*{formatted_date_str}*.mat")
            )
            if len(raw_behavior_file_paths) != 1:
                # TODO: figure out how to match duplicate dates
                # ntrials from processed then read the raw file and check if the number of trials match
                processed_behavior_data = read_mat(str(processed_behavior_file_path))

                date_index = list(dates_from_mat).index(date_from_mat)
                num_trials = processed_behavior_data["A"]["ntrials"][date_index]
                for behavior_file_path in raw_behavior_file_paths:
                    try:
                        raw_behavior_data = read_mat(str(behavior_file_path))
                    except ValueError as e:
                        print(f"Error reading file: {behavior_file_path} , {e}")
                        continue
                    num_trials_here = raw_behavior_data["SessionData"]["nTrials"]
                    if num_trials_here == num_trials:
                        raw_behavior_file_paths = [behavior_file_path]
                        break

            if len(raw_behavior_file_paths) != 1:
                raise ValueError(
                    f"Expected to find 1 raw behavior file for date {formatted_date_str}, found {len(raw_behavior_file_paths)}."
                )
            raw_behavior_file_path = raw_behavior_file_paths[0]

            session_id = raw_behavior_file_path.stem.split("_", maxsplit=1)[1].replace("_", "-")
            subject_nwb_folder_path = nwbfile_folder_path / f"sub-{subject_id}"
            if not subject_nwb_folder_path.exists():
                os.makedirs(subject_nwb_folder_path, exist_ok=True)
            nwbfile_path = subject_nwb_folder_path / f"sub-{subject_id}_ses-{session_id}.nwb"

            if nwbfile_path.exists() and not overwrite:
                print(f"Skipping existing NWB file: {nwbfile_path}")
                continue

            subject_metadata = get_subject_metadata_from_rat_info_folder(
                folder_path=rat_info_folder_path,
                subject_id=subject_id,
                date=date_obj.strftime("%Y-%m-%d"),
            )

            session_to_nwb(
                raw_behavior_file_path=raw_behavior_file_path,
                processed_behavior_file_path=processed_behavior_file_path,
                date=date_from_mat,
                nwbfile_path=nwbfile_path,
                column_name_mapping=column_name_mapping,
                column_descriptions=column_descriptions,
                subject_metadata=subject_metadata,
                overwrite=overwrite,
            )


if __name__ == "__main__":

    # Parameters for conversion
    processed_behavior_folder_path = Path(r"/Volumes/T9/Constantinople/published/A_Structs_Final")
    raw_behavior_folder_path = Path(r"/Volumes/T9/Constantinople/raw_Bpod")
    rat_info_folder_path = Path(r"/Volumes/T9/Constantinople/Rat_info")

    column_name_mapping = dict(
        hits="is_rewarded",
        vios="is_violation",
        optout="is_opt_out",
        wait_time="wait_time",
        wait_time_unthresholded="wait_time_unthresholded",
        wait_thresh="wait_time_threshold",
        wait_for_cpoke="wait_for_center_poke",
        zwait_for_cpoke="z_scored_wait_for_center_poke",
        side="rewarded_port",
        lpoke="num_left_pokes",
        rpoke="num_right_pokes",
        cpoke="num_center_pokes",
        lpokedur="duration_of_left_pokes",
        rpokedur="duration_of_right_pokes",
        cpokedur="duration_of_center_pokes",
        rt="reaction_time",
        slrt="side_poke_reaction_time",  # side led on = side poke
        ITI="inter_trial_interval",
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
        side="The rewarded port (Left or Right) for each trial.",
        lpoke="The number of left pokes for each trial.",
        rpoke="The number of right pokes for each trial.",
        cpoke="The number of center pokes for each trial.",
        lpokedur="The duration of left pokes for each trial in seconds.",
        rpokedur="The duration of right pokes for each trial in seconds.",
        cpokedur="The duration of center pokes for each trial in seconds.",
        rt="The reaction time in seconds.",
        slrt="The side poke reaction time in seconds.",
        ITI="The time to initiate trial in seconds (the time between the end of the consummatory period and the time to initiate the next trial).",
        wait_time_unthresholded="The wait time for the subject for each trial in seconds without removing outliers.",
        wait_thresh="The threshold in seconds to remove wait-times (mean + 1*std of all cumulative wait-times).",
    )

    nwbfile_folder_path = Path("/Users/weian/data/001169")

    overwrite = False

    sessions_to_nwb(
        raw_behavior_folder_path=raw_behavior_folder_path,
        processed_behavior_folder_path=processed_behavior_folder_path,
        rat_info_folder_path=rat_info_folder_path,
        nwbfile_folder_path=nwbfile_folder_path,
        column_name_mapping=column_name_mapping,
        column_descriptions=column_descriptions,
        overwrite=overwrite,
    )
