import os
import re
from datetime import datetime
from pathlib import Path
from typing import Union, Optional

from dateutil import tz
from neuroconv.utils import load_dict_from_file, dict_deep_update

from constantinople_lab_to_nwb.fiber_photometry import FiberPhotometryNWBConverter
from ndx_pose import PoseEstimation


def session_to_nwb(
    raw_fiber_photometry_file_path: Union[str, Path],
    raw_behavior_file_path: Union[str, Path],
    nwbfile_path: Union[str, Path],
    dlc_file_path: Optional[Union[str, Path]] = None,
    video_file_path: Optional[Union[str, Path]] = None,
    stub_test: bool = False,
    overwrite: bool = False,
    verbose: bool = False,
):
    """Converts a fiber photometry session to NWB.

    Parameters
    ----------
    raw_fiber_photometry_file_path : Union[str, Path]
        Path to the raw fiber photometry file (.doric or .csv).
    raw_behavior_file_path : Union[str, Path]
        Path to the raw Bpod output (.mat file).
    nwbfile_path : Union[str, Path]
        Path to the NWB file.
    dlc_file_path : Union[str, Path], optional
        Path to the DLC file, by default None.
    video_file_path : Union[str, Path], optional
        Path to the video file, by default None.
    overwrite : bool, optional
        Whether to overwrite the NWB file if it already exists, by default False.
    verbose : bool, optional
        Controls verbosity.
    """
    source_data = dict()
    conversion_options = dict()

    raw_fiber_photometry_file_path = Path(raw_fiber_photometry_file_path)
    raw_fiber_photometry_file_name = raw_fiber_photometry_file_path.stem
    subject_id, session_id = raw_fiber_photometry_file_name.split("_", maxsplit=1)
    session_id = session_id.replace("_", "-")

    # Add fiber photometry data
    file_suffix = raw_fiber_photometry_file_path.suffix
    if file_suffix == ".doric":
        fiber_photometry_metadata_file_name = "doric_fiber_photometry_metadata.yaml"
        interface_name = "FiberPhotometryDoric"
    elif file_suffix == ".csv":
        fiber_photometry_metadata_file_name = "doric_csv_fiber_photometry_metadata.yaml"
        interface_name = "FiberPhotometryCsv"
    else:
        raise ValueError(
            f"File '{raw_fiber_photometry_file_path}' extension should be either .doric or .csv and not '{file_suffix}'."
        )

    source_data.update({interface_name: dict(file_path=raw_fiber_photometry_file_path, verbose=verbose)})
    conversion_options.update({interface_name: dict(stub_test=stub_test)})

    if dlc_file_path is not None:
        source_data.update(dict(DeepLabCut=dict(file_path=dlc_file_path)))

    if video_file_path is not None:
        source_data.update(dict(Video=dict(file_paths=[video_file_path])))

    # Add behavior data
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

    converter = FiberPhotometryNWBConverter(source_data=source_data, verbose=verbose)

    # Add datetime to conversion
    metadata = converter.get_metadata()
    metadata["NWBFile"].update(session_id=session_id)

    date_pattern = r"(?P<date>\d{8})"

    match = re.search(date_pattern, raw_fiber_photometry_file_name)
    if match:
        date_str = match.group("date")
        date_obj = datetime.strptime(date_str, "%Y%m%d")
        session_start_time = date_obj
        tzinfo = tz.gettz("America/New_York")
        metadata["NWBFile"].update(session_start_time=session_start_time.replace(tzinfo=tzinfo))

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "metadata" / fiber_photometry_metadata_file_name
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Update behavior metadata
    behavior_metadata_path = Path(__file__).parent / "metadata" / "behavior_metadata.yaml"
    behavior_metadata = load_dict_from_file(behavior_metadata_path)
    metadata = dict_deep_update(metadata, behavior_metadata)

    # Run conversion
    converter.run_conversion(
        nwbfile_path=nwbfile_path,
        metadata=metadata,
        conversion_options=conversion_options,
        overwrite=overwrite,
    )


if __name__ == "__main__":
    # Parameters for conversion
    # Fiber photometry file path
    doric_fiber_photometry_file_path = Path(
        "/Volumes/T9/Constantinople/Preprocessed_data/J069/Raw/J069_ACh_20230809_HJJ_0002.doric"
    )

    # The raw behavior data from Bpod (contains data for a single session)
    bpod_behavior_file_path = Path(
        "/Volumes/T9/Constantinople/raw_Bpod/J069/DataFiles/J069_RWTautowait2_20230809_131216.mat"
    )

    # DLC file path (optional)
    dlc_file_path = Path(
        "/Volumes/T9/Constantinople/DeepLabCut/J069/J069-2023-08-09_rig104cam01_0002compDLC_resnet50_GRAB_DA_DMS_RIG104DoricCamera_J029May12shuffle1_500000.h5"
    )
    # Behavior video file path (optional)
    behavior_video_file_path = Path(
        "/Volumes/T9/Constantinople/Compressed Videos/J069/J069-2023-08-09_rig104cam01_0002comp.mp4"
    )
    # NWB file path
    nwbfile_path = Path("/Volumes/T9/Constantinople/nwbfiles/J069_ACh_20230809_HJJ_0002.nwb")
    if not nwbfile_path.parent.exists():
        os.makedirs(nwbfile_path.parent, exist_ok=True)

    stub_test = False
    overwrite = True

    session_to_nwb(
        raw_fiber_photometry_file_path=doric_fiber_photometry_file_path,
        raw_behavior_file_path=bpod_behavior_file_path,
        nwbfile_path=nwbfile_path,
        dlc_file_path=dlc_file_path,
        video_file_path=behavior_video_file_path,
        stub_test=stub_test,
        overwrite=overwrite,
        verbose=True,
    )
