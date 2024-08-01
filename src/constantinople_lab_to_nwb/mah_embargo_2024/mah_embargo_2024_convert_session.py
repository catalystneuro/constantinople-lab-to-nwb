import os
from pathlib import Path
from typing import Union, List

from dateutil import tz
from neuroconv.utils import load_dict_from_file, dict_deep_update
from pymatreader import read_mat

from constantinople_lab_to_nwb.mah_embargo_2024 import MahEmbargo2024NWBConverter


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
    behavior_data = read_mat(file_path)
    if default_struct_name not in behavior_data:
        raise ValueError(f"The default struct name '{default_struct_name}' is missing from {file_path}.")

    behavior_data = behavior_data[default_struct_name]
    if "date" not in behavior_data:
        raise ValueError(f"The 'date' key is missing from {file_path}.")

    return behavior_data["date"]

def session_to_nwb(
        behavior_file_path: Union[str, Path],
        date: str,
        nwbfile_path: Union[str, Path],
        overwrite: bool = False,
):
    source_data = dict()
    conversion_options = dict()

    # Add Behavior
    source_data.update(dict(Behavior=dict(file_path=behavior_file_path, date=date, sampling_frequency=1.0)))

    converter = MahEmbargo2024NWBConverter(source_data=source_data, verbose=False)

    # Add datetime to conversion
    metadata = converter.get_metadata()
    session_start_time = metadata["NWBFile"]["session_start_time"]
    tzinfo = tz.gettz("America/New_York")
    metadata["NWBFile"].update(
        session_start_time=session_start_time.replace(tzinfo=tzinfo),
    )

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "metadata" / "mah_embargo_2024_general_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Run conversion
    converter.run_conversion(
        nwbfile_path=nwbfile_path,
        metadata=metadata,
        conversion_options=conversion_options,
        overwrite=overwrite,
    )


def sessions_to_nwb(
        behavior_file_path: Union[str, Path],
        nwbfile_folder_path: Union[str, Path],
        overwrite: bool = False,
):
    if not nwbfile_folder_path.exists():
        os.makedirs(nwbfile_folder_path, exist_ok=True)

    session_ids = _get_sessions_to_convert_from_mat(file_path=behavior_file_path)
    subject_id = Path(behavior_file_path).stem.split("_")[-1]
    for session_id in session_ids:
        nwbfile_path = nwbfile_folder_path / f"sub-{subject_id}_ses-{session_id}.nwb"
        session_to_nwb(
            behavior_file_path=behavior_file_path,
            date=session_id,
            nwbfile_path=nwbfile_path,
            overwrite=overwrite,
        )


if __name__ == "__main__":

    # Parameters for conversion
    behavior_file_path = Path(r"/Volumes/t7-ssd/GCP/Constantinople/Behavior Data/ratTrial_C015-new.mat")
    nwbfile_folder_path = Path("/Volumes/t7-ssd/GCP/Constantinople/nwbfiles")

    overwrite = True

    sessions_to_nwb(
        behavior_file_path=behavior_file_path,
        nwbfile_folder_path=nwbfile_folder_path,
        overwrite=overwrite,
    )
