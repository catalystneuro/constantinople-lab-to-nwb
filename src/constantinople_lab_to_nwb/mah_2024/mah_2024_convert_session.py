from pathlib import Path
from typing import Union

from dateutil import tz
from neuroconv.utils import load_dict_from_file, dict_deep_update

from constantinople_lab_to_nwb.mah_2024 import Mah2024NWBConverter


def session_to_nwb(
        raw_behavior_file_path: Union[str, Path],
        nwbfile_path: Union[str, Path],
        overwrite: bool = False,
        verbose: bool = False,
):
    """
    Convert a single session to NWB format.

    Parameters
    ----------
    raw_behavior_file_path: Union[str, Path]
        Path to the raw Bpod output (.mat file).
    nwbfile_path: Union[str, Path]
        Path to the output NWB file.
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

    # Run conversion
    converter.run_conversion(
        nwbfile_path=nwbfile_path,
        metadata=metadata,
        conversion_options=conversion_options,
        overwrite=overwrite,
    )


if __name__ == "__main__":
    # Parameters for conversion
    bpod_file_path = Path("/Volumes/T9/Constantinople/C005/DataFiles/C005_RWTautowait_20190909_145629.mat")
    nwbfile_path = Path("/Volumes/T9/Constantinople/nwbfiles/C005_RWTautowait_20190909_1456293.nwb")

    overwrite = True
    verbose = True

    session_to_nwb(
        raw_behavior_file_path=bpod_file_path,
        nwbfile_path=nwbfile_path,
        overwrite=overwrite,
        verbose=verbose,
    )
