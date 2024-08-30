from pathlib import Path
from typing import Union, Optional

import pandas as pd
from dateutil import tz
from neuroconv.utils import load_dict_from_file, dict_deep_update
from pymatreader import read_mat

from constantinople_lab_to_nwb.mah_2024 import Mah2024NWBConverter


def get_subject_metadata_from_rat_info_folder(
    folder_path: Union[str, Path],
    subject_id: str,
    date: str,
) -> dict:
    """
    Load subject metadata from the rat info files.
    The "registry.mat" file contains information about the subject such as date of birth, sex, and vendor.
    The "Mass_registry.mat" file contains information about the weight of the subject.

    Parameters
    ----------
    folder_path: Union[str, Path]
        The folder path containing the rat info files.
    subject_id: str
        The subject ID.
    date: str
        The date of the session in the format "yyyy-mm-dd".
    """

    folder_path = Path(folder_path)
    rat_registry_file_path = folder_path / "registry.mat"

    subject_metadata = dict()
    if rat_registry_file_path.exists():
        rat_registry = read_mat(str(rat_registry_file_path))
        rat_registry = pd.DataFrame(rat_registry["Registry"])

        filtered_rat_registry = rat_registry[rat_registry["RatName"] == subject_id]
        if not filtered_rat_registry.empty:
            date_of_birth = filtered_rat_registry["DOB"].values[0]
            # convert date of birth to datetime with format "yyyy-mm-dd"
            date_of_birth = pd.to_datetime(date_of_birth, format="%Y-%m-%d")
            sex = filtered_rat_registry["sex"].values[0]
            subject_metadata.update(
                date_of_birth=date_of_birth,
                sex=sex,
            )
            vendor = filtered_rat_registry["vendor"].values[0]
            if vendor:
                subject_metadata.update(vendor=f"Vendor: {vendor}")

    mass_registry_file_path = folder_path / "Mass_registry.mat"
    if mass_registry_file_path.exists():
        mass_registry = read_mat(str(mass_registry_file_path))
        mass_registry = pd.DataFrame(mass_registry["Mass_registry"])

        filtered_mass_registry = mass_registry[(mass_registry["rat"] == subject_id) & (mass_registry["date"] == date)]
        if not filtered_mass_registry.empty:
            weight_g = filtered_mass_registry["mass"].values[0]  # in grams
            # convert mass to kg
            weight_kg = weight_g / 1000
            subject_metadata.update(weight=weight_kg)

    return subject_metadata


def session_to_nwb(
    raw_behavior_file_path: Union[str, Path],
    processed_behavior_file_path: Union[str, Path],
    date: str,
    nwbfile_path: Union[str, Path],
    column_name_mapping: Optional[dict] = None,
    column_descriptions: Optional[dict] = None,
    subject_metadata: Optional[dict] = None,
    overwrite: bool = False,
    verbose: bool = False,
):
    """
    Convert a single session to NWB format.

    Parameters
    ----------
    raw_behavior_file_path: Union[str, Path]
        Path to the raw Bpod output (.mat file).
    processed_behavior_file_path: Union[str, Path]
        Path to the processed behavior data (.mat file).
    date: str
        Date of the session in the format "dd-mmm-yyyy" (e.g. 09-Sep-2019). The date is used to identify the session
        in the processed behavior file, as it contains data for multiple days.
    nwbfile_path: Union[str, Path]
        Path to the output NWB file.
    column_name_mapping: dict, optional
        Dictionary to map the column names in the processed behavior data to more descriptive column names.
    column_descriptions: dict, optional
        Dictionary to add descriptions to the columns in the processed behavior data.
    subject_metadata: dict, optional
        Metadata about the subject.
    overwrite: bool, optional
        Whether to overwrite the NWB file if it already exists.
    verbose: bool, optional
        Controls verbosity.
    """
    source_data = dict()
    conversion_options = dict()

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
    ]
    conversion_options.update(dict(RawBehavior=dict(task_arguments_to_exclude=task_arguments_to_exclude)))

    # Add Processed Behavior
    source_data.update(dict(ProcessedBehavior=dict(file_path=processed_behavior_file_path, date=date)))
    conversion_options.update(
        dict(ProcessedBehavior=dict(column_name_mapping=column_name_mapping, column_descriptions=column_descriptions))
    )

    converter = Mah2024NWBConverter(source_data=source_data, verbose=verbose)

    subject_id, session_id = Path(raw_behavior_file_path).stem.split("_", maxsplit=1)
    session_id = session_id.replace("_", "-")

    # Add datetime to conversion
    metadata = converter.get_metadata()
    session_start_time = metadata["NWBFile"]["session_start_time"]
    tzinfo = tz.gettz("America/New_York")
    metadata["NWBFile"].update(
        session_start_time=session_start_time.replace(tzinfo=tzinfo),
        session_id=session_id,
    )

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "metadata" / "mah_2024_general_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Update behavior metadata
    behavior_metadata_path = Path(__file__).parent / "metadata" / "mah_2024_behavior_metadata.yaml"
    behavior_metadata = load_dict_from_file(behavior_metadata_path)
    metadata = dict_deep_update(metadata, behavior_metadata)

    metadata["Subject"].update(subject_id=subject_id)
    if subject_metadata is not None:
        metadata["Subject"].update(subject_metadata)

    # Run conversion
    converter.run_conversion(
        nwbfile_path=nwbfile_path,
        metadata=metadata,
        conversion_options=conversion_options,
        overwrite=overwrite,
    )


if __name__ == "__main__":
    # Parameters for conversion

    # The raw behavior data is stored in a .mat file (contains data for a single session)
    bpod_file_path = Path("/Volumes/T9/Constantinople/raw_Bpod/C005/DataFiles/C005_RWTautowait_20190909_145629.mat")
    # The processed behavior data is stored in a .mat file (contains data for multiple days)
    processed_behavior_file_path = Path("/Volumes/T9/Constantinople/A_Structs/ratTrial_C005.mat")
    # The date is used to identify the session to convert from the processed behavior file
    date = "09-Sep-2019"
    # The column name mapping is used to rename the columns in the processed data to more descriptive column names. (optional)
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
        slrt="short_latency_reaction_time",
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
        slrt="The short-latency reaction time in seconds.",
        ITI="The time to initiate trial in seconds (the time between the end of the consummatory period and the time to initiate the next trial).",
        wait_time_unthresholded="The wait time for the subject for each trial in seconds without removing outliers.",
        wait_thresh="The threshold in seconds to remove wait-times (mean + 1*std of all cumulative wait-times).",
    )

    # Add subject metadata
    subject_metadata = get_subject_metadata_from_rat_info_folder(
        folder_path="/Volumes/T9/Constantinople/Rat_info",
        subject_id="C005",
        date="2019-09-09",
    )

    # Path to the output NWB file
    nwbfile_path = Path("/Volumes/T9/Constantinople/nwbfiles/C005_RWTautowait_20190909_145629.nwb")

    # Whether to overwrite the NWB file if it already exists
    overwrite = True
    # Controls verbosity
    verbose = True

    session_to_nwb(
        raw_behavior_file_path=bpod_file_path,
        processed_behavior_file_path=processed_behavior_file_path,
        date=date,
        column_name_mapping=column_name_mapping,
        column_descriptions=column_descriptions,
        nwbfile_path=nwbfile_path,
        subject_metadata=subject_metadata,
        overwrite=overwrite,
        verbose=verbose,
    )
