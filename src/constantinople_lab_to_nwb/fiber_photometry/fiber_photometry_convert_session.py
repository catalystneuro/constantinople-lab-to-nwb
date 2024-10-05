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
        Path to the raw fiber photometry file.
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
        raw_stream_name = "/DataAcquisition/FPConsole/Signals/Series0001/AnalogIn"
    elif file_suffix == ".csv":
        raw_stream_name = "Raw"
    else:
        raise ValueError(
            f"File '{raw_fiber_photometry_file_path}' extension should be either .doric or .csv and not '{file_suffix}'."
        )

    source_data.update(
        dict(
            FiberPhotometry=dict(
                file_path=raw_fiber_photometry_file_path,
                stream_name=raw_stream_name,
            )
        )
    )
    conversion_options.update(
        dict(
            FiberPhotometry=dict(
                stub_test=stub_test,
                fiber_photometry_series_name="fiber_photometry_response_series_green",
            )
        )
    )

    if dlc_file_path is not None:
        source_data.update(dict(DeepLabCut=dict(file_path=dlc_file_path)))

    if video_file_path is not None:
        source_data.update(dict(Video=dict(file_paths=[video_file_path])))

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
    editable_metadata_path = Path(__file__).parent / "metadata" / "fiber_photometry_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

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
        nwbfile_path=nwbfile_path,
        dlc_file_path=dlc_file_path,
        video_file_path=behavior_video_file_path,
        stub_test=stub_test,
        overwrite=overwrite,
        verbose=True,
    )
