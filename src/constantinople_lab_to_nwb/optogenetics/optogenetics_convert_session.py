from pathlib import Path
from typing import Union

from dateutil import tz
from neuroconv.utils import load_dict_from_file, dict_deep_update

from constantinople_lab_to_nwb.optogenetics import OptogeneticsNWBConverter


def session_to_nwb(
    raw_behavior_file_path: Union[str, Path],
    nwbfile_path: Union[str, Path],
    overwrite: bool = False,
    verbose: bool = False,
):
    """
    Convert a session of data to NWB format.

    Parameters
    ----------
    raw_behavior_file_path : str or Path
        The path to the raw behavior file.
    nwbfile_path : str or Path
        The path to the NWB file to write.
    overwrite : bool, default: False
        Whether to overwrite an existing NWB file.
    verbose : bool, default: False
        Whether to display verbose output.
    """
    source_data = dict()
    conversion_options = dict()

    # Add Behavior
    source_data.update(dict(Behavior=dict(file_path=raw_behavior_file_path)))
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
    conversion_options.update(dict(Behavior=dict(task_arguments_to_exclude=task_arguments_to_exclude)))

    converter = OptogeneticsNWBConverter(source_data=source_data, verbose=verbose)

    subject_id, session_id = Path(raw_behavior_file_path).stem.split("_", maxsplit=1)
    protocol = session_id.split("_")[0]
    session_id = session_id.replace("_", "-")

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
    editable_metadata_path = Path(__file__).parent / "metadata" / "optogenetics_general_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Update behavior metadata
    behavior_metadata_path = Path(__file__).parent / "metadata" / "optogenetics_behavior_metadata.yaml"
    behavior_metadata = load_dict_from_file(behavior_metadata_path)
    metadata = dict_deep_update(metadata, behavior_metadata)

    # Update ogen metadata
    ogen_metadata_path = Path(__file__).parent / "metadata" / "optogenetics_stimulation_metadata.yaml"
    ogen_metadata = load_dict_from_file(ogen_metadata_path)
    metadata = dict_deep_update(metadata, ogen_metadata)

    metadata["Subject"].update(subject_id=subject_id, sex="U", age="P7D")
    # if subject_metadata is not None:
    #     metadata["Subject"].update(subject_metadata)

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
    bpod_file_path = Path(
        "/Volumes/T9/Constantinople/raw_Bpod/L047/DataFiles/L047_RWTautowait2OptoTest_20240816_085658.mat"
    )
    nwbfile_path = "/Volumes/T9/Constantinople/nwbfiles/L047_RWTautowait2OptoTest_20240816_085658k.nwb"
    overwrite = True
    verbose = False

    # Run conversion
    session_to_nwb(
        raw_behavior_file_path=bpod_file_path,
        nwbfile_path=nwbfile_path,
        overwrite=overwrite,
        verbose=verbose,
    )
