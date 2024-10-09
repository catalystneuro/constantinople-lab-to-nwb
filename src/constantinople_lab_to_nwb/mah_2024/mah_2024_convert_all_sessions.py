import os
from datetime import datetime
from pathlib import Path
from typing import Union, List
from warnings import warn

import pandas as pd
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
    bpod_folder_path: Union[str, Path],
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

    dates = behavior_data["date"]

    subject_id = file_path.stem.split("_")[-1]
    bpod_files_to_convert = []
    for date in dates:
        date_obj = datetime.strptime(date, "%d-%b-%Y")
        formatted_date_str = date_obj.strftime("%Y%m%d")

        raw_behavior_file_paths = list(
            (bpod_folder_path / subject_id / "DataFiles").glob(f"*{formatted_date_str}*.mat")
        )
        bpod_files_to_convert.extend(raw_behavior_file_paths)

    return bpod_files_to_convert


def _get_date_index(bpod_file_path: Union[str, Path], a_struct_file_path: Union[str, Path]) -> Union[int, None]:
    """
    Figure out the date index for the processed behavior file.

    Parameters
    ----------
    bpod_file_path: Union[str, Path]
        Path to the raw Bpod output (.mat file).
    a_struct_file_path: Union[str, Path]
        Path to the processed behavior data (.mat file).

    Returns
    -------
    int
        The date index for the processed behavior file.
    """
    bpod_data = read_mat(str(bpod_file_path))
    try:
        bpod_session_data = bpod_data["SessionData"]
    except KeyError:
        warn(
            f"'SessionData' key not found in '{bpod_file_path}'. The date index could not be determined from the file."
        )
        return None

    num_trials = bpod_session_data["nTrials"]
    date = bpod_session_data["Info"]["SessionDate"]

    a_struct_data = read_mat(str(a_struct_file_path))
    dates = a_struct_data["A"]["date"]
    num_trials_per_day = a_struct_data["A"]["ntrials"]

    dates_and_trials = pd.DataFrame(dict(date=dates, num_trials=num_trials_per_day))
    filtered_dates_and_trials = dates_and_trials[
        (dates_and_trials["date"] == date) & (dates_and_trials["num_trials"] == num_trials)
    ]

    if filtered_dates_and_trials.empty:
        warn(f"Date index for '{date}' not found in '{a_struct_file_path}'.")
        return None

    return filtered_dates_and_trials.index[0]


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

    processed_mat_files = list(processed_behavior_folder_path.glob("ratTrial*.mat"))
    subject_ids = [
        processed_behavior_file_path.stem.split("_")[-1] for processed_behavior_file_path in processed_mat_files
    ]
    sessions_to_convert_per_subject = {
        subject_id: _get_sessions_to_convert_from_mat(
            file_path=processed_behavior_file_path, bpod_folder_path=raw_behavior_folder_path
        )
        for subject_id, processed_behavior_file_path in zip(subject_ids, processed_mat_files)
    }

    for subject_id, processed_behavior_file_path in zip(subject_ids, processed_mat_files):
        raw_bpod_file_paths = sessions_to_convert_per_subject[subject_id]
        num_sessions_per_subject = len(raw_bpod_file_paths)
        progress_bar = tqdm(
            raw_bpod_file_paths,
            desc=f"Converting subject '{subject_id}' with {num_sessions_per_subject} sessions to NWB ...",
            position=0,
            total=num_sessions_per_subject,
            dynamic_ncols=True,
        )

        for raw_behavior_file_path in progress_bar:
            session_id = Path(raw_behavior_file_path).stem.split("_", maxsplit=1)[1].replace("_", "-")
            subject_nwb_folder_path = nwbfile_folder_path / f"sub-{subject_id}"
            if not subject_nwb_folder_path.exists():
                os.makedirs(subject_nwb_folder_path, exist_ok=True)
            nwbfile_path = subject_nwb_folder_path / f"sub-{subject_id}_ses-{session_id}.nwb"

            if nwbfile_path.exists() and not overwrite:
                continue

            date_index = _get_date_index(
                bpod_file_path=raw_behavior_file_path, a_struct_file_path=processed_behavior_file_path
            )
            if date_index is None:
                print(
                    f"Skipping '{subject_id}' session '{session_id}', session not found in the processed behavior file."
                )
                continue

            date_from_mat = session_id.split("-")[1]
            date_obj = datetime.strptime(date_from_mat, "%Y%d%M")
            subject_metadata = get_subject_metadata_from_rat_info_folder(
                folder_path=rat_info_folder_path,
                subject_id=subject_id,
                date=date_obj.strftime("%Y-%m-%d"),
            )

            session_to_nwb(
                raw_behavior_file_path=raw_behavior_file_path,
                processed_behavior_file_path=processed_behavior_file_path,
                date_index=date_index,
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
