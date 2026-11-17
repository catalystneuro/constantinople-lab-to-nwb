import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union
from warnings import warn

import pandas as pd
from pymatreader import read_mat
from tqdm import tqdm

from constantinople_lab_to_nwb.mah_2024.mah_2024_convert_session import (
    COLUMN_DESCRIPTIONS,
    COLUMN_NAME_MAPPING,
    session_to_nwb,
)
from constantinople_lab_to_nwb.utils import get_subject_metadata_from_rat_info_folder

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


def _get_date_index_per_session(
    bpod_file_paths: List[Union[str, Path]], a_struct_file_path: Union[str, Path]
) -> Dict[Path, int]:
    """
    Match each raw Bpod file to its session (date index) in the processed behavior file.

    Raw Bpod files that are not found in the processed behavior file are skipped.
    When more than one raw Bpod file matches the same session (e.g. a copy of the file saved with a suffix),
    only the first file in alphabetical order is kept.

    Parameters
    ----------
    bpod_file_paths: List[Union[str, Path]]
        The paths to the raw Bpod output files (.mat) of a single subject.
    a_struct_file_path: Union[str, Path]
        Path to the processed behavior data (.mat file).

    Returns
    -------
    Dict[Path, int]
        The date index in the processed behavior file for each raw Bpod file to convert.
    """
    date_index_per_session = dict()
    bpod_file_path_per_date_index = dict()
    for bpod_file_path in sorted(Path(file_path) for file_path in bpod_file_paths):
        date_index = _get_date_index(bpod_file_path=bpod_file_path, a_struct_file_path=a_struct_file_path)
        if date_index is None:
            print(f"Skipping '{bpod_file_path.name}', session not found in the processed behavior file.")
            continue
        if date_index in bpod_file_path_per_date_index:
            warn(
                f"Skipping '{bpod_file_path.name}', it matches the same session in '{a_struct_file_path}' as "
                f"'{bpod_file_path_per_date_index[date_index].name}'."
            )
            continue
        bpod_file_path_per_date_index[date_index] = bpod_file_path
        date_index_per_session[bpod_file_path] = date_index

    return date_index_per_session


def _get_session_date(session_id: str) -> str:
    """
    Get the date of the session in the format "yyyy-mm-dd" from the session identifier
    (e.g. "RWTautowait2-20221004-095612" returns "2022-10-04").
    """
    date_from_session_id = session_id.split("-")[1]
    return datetime.strptime(date_from_session_id, "%Y%m%d").strftime("%Y-%m-%d")


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
        date_index_per_session = _get_date_index_per_session(
            bpod_file_paths=sessions_to_convert_per_subject[subject_id],
            a_struct_file_path=processed_behavior_file_path,
        )
        raw_bpod_file_paths = list(date_index_per_session.keys())
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

            date_index = date_index_per_session[raw_behavior_file_path]
            subject_metadata = get_subject_metadata_from_rat_info_folder(
                folder_path=rat_info_folder_path,
                subject_id=subject_id,
                date=_get_session_date(session_id=session_id),
            )

            session_to_nwb(
                raw_behavior_file_path=raw_behavior_file_path,
                processed_behavior_file_path=processed_behavior_file_path,
                date_index=date_index,
                nwbfile_path=nwbfile_path,
                column_name_mapping=COLUMN_NAME_MAPPING,
                column_descriptions=COLUMN_DESCRIPTIONS,
                subject_metadata=subject_metadata,
                overwrite=overwrite,
            )


if __name__ == "__main__":

    # Parameters for conversion
    processed_behavior_folder_path = Path(r"/Volumes/T9/Constantinople/published/A_Structs_Final")
    raw_behavior_folder_path = Path(r"/Volumes/T9/Constantinople/raw_Bpod")
    rat_info_folder_path = Path(r"/Volumes/T9/Constantinople/Rat_info")

    nwbfile_folder_path = Path("/Users/weian/data/001169")

    overwrite = False

    sessions_to_nwb(
        raw_behavior_folder_path=raw_behavior_folder_path,
        processed_behavior_folder_path=processed_behavior_folder_path,
        rat_info_folder_path=rat_info_folder_path,
        nwbfile_folder_path=nwbfile_folder_path,
        column_name_mapping=COLUMN_NAME_MAPPING,
        column_descriptions=COLUMN_DESCRIPTIONS,
        overwrite=overwrite,
    )
