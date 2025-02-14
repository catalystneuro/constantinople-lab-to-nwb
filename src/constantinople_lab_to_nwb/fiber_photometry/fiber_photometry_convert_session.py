import os
from pathlib import Path
from typing import Union, Optional

from dateutil import tz
from neuroconv.utils import load_dict_from_file, dict_deep_update

from constantinople_lab_to_nwb.fiber_photometry import FiberPhotometryNWBConverter
from ndx_pose import PoseEstimation

from constantinople_lab_to_nwb.utils import get_subject_metadata_from_rat_info_folder


def session_to_nwb(
    raw_fiber_photometry_file_path: Union[str, Path],
    fiber_photometry_metadata: dict,
    raw_behavior_file_path: Union[str, Path],
    subject_metadata: dict,
    nwbfile_path: Union[str, Path],
    tmac_ch1_file_path: Optional[Union[str, Path]] = None,
    tmac_ch2_file_path: Optional[Union[str, Path]] = None,
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
    fiber_photometry_metadata : dict
        The metadata for the fiber photometry experiment setup.
    subject_metadata: dict
        The dictionary containing the subject metadata. (e.g. {'date_of_birth': '2022-11-22', 'description': 'Vendor: OVR', 'sex': 'M'}
    raw_behavior_file_path : Union[str, Path]
        Path to the raw Bpod output (.mat file).
    nwbfile_path : Union[str, Path]
        Path to the NWB file.
    tmac_ch1_file_path: Union[str, Path]
        Path to the tmac .mat file for Ch1, by default None.
    tmac_ch2_file_path : Union[str, Path], optional
        Path to the tmac .mat file for Ch2, by default None.
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

    subject_id, session_id = Path(raw_behavior_file_path).stem.split("_", maxsplit=1)
    protocol = session_id.split("_")[0]
    session_id = session_id.replace("_", "-")

    # Add fiber photometry data
    file_suffix = raw_fiber_photometry_file_path.suffix
    if file_suffix == ".doric":
        interface_name = "FiberPhotometryDoric"
    elif file_suffix == ".csv":
        interface_name = "FiberPhotometryCsv"
    else:
        raise ValueError(
            f"File '{raw_fiber_photometry_file_path}' extension should be either .doric or .csv and not '{file_suffix}'."
        )

    source_data.update({interface_name: dict(file_path=raw_fiber_photometry_file_path, verbose=verbose)})
    conversion_options.update({interface_name: dict(stub_test=stub_test)})

    # Add processed fiber photometry data
    if tmac_ch1_file_path is None and tmac_ch2_file_path is None:
        raise ValueError("Either 'tmac_ch1_file_path' or 'tmac_ch2_file_path' must be provided.")
    source_data.update(
        ProcessedFiberPhotometry=dict(
            tmac_ch1_file_path=tmac_ch1_file_path,
            tmac_ch2_file_path=tmac_ch2_file_path,
            verbose=verbose,
        ),
    )
    conversion_options.update(
        dict(
            ProcessedFiberPhotometry=dict(
                doric_acquisition_signal_name="demodulated_fiber_photometry_signal",
            )
        )
    )

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
    metadata["NWBFile"].update(session_id=session_id, protocol=protocol)

    session_start_time = metadata["NWBFile"]["session_start_time"]
    tzinfo = tz.gettz("America/New_York")
    metadata["NWBFile"].update(session_start_time=session_start_time.replace(tzinfo=tzinfo))

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "metadata" / "general_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    metadata = dict_deep_update(metadata, fiber_photometry_metadata)

    # Update behavior metadata
    behavior_metadata_path = Path(__file__).parent / "metadata" / "behavior_metadata.yaml"
    behavior_metadata = load_dict_from_file(behavior_metadata_path)
    metadata = dict_deep_update(metadata, behavior_metadata)

    metadata["Subject"].update(subject_id=subject_id, **subject_metadata)

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
    # Update default metadata with the editable in the corresponding yaml file
    fiber_photometry_metadata_file_path = Path(__file__).parent / "metadata" / "doric_fiber_photometry_metadata.yaml"
    fiber_photometry_metadata = load_dict_from_file(fiber_photometry_metadata_file_path)

    # Processed fiber photometry file path(s)
    ch1_tmac_file_path = Path(
        "/Volumes/T9/Constantinople/Preprocessed_data/J069/tmac_ch1/J069_ACh_20230809_HJJ_tmac.mat"
    )
    # When there are two channels, ch2_tmac_file_path should be provided
    ch2_tmac_file_path = Path(
        "/Volumes/T9/Constantinople/Preprocessed_data/J069/tmac_ch2/J069_ACh_20230809_HJJ_tmac.mat"
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
    nwbfile_path = Path("/Users/weian/data/demo/J069_ACh_20230809_HJJ_0002.nwb")
    if not nwbfile_path.parent.exists():
        os.makedirs(nwbfile_path.parent, exist_ok=True)

    stub_test = False
    overwrite = True

    # Get subject metadata from rat registry
    rat_registry_folder_path = "/Volumes/T9/Constantinople/Rat_info"
    subject_metadata = get_subject_metadata_from_rat_info_folder(
        folder_path=rat_registry_folder_path,
        subject_id="J069",
        date="2023-08-09",
    )

    session_to_nwb(
        raw_fiber_photometry_file_path=doric_fiber_photometry_file_path,
        fiber_photometry_metadata=fiber_photometry_metadata,
        tmac_ch1_file_path=ch1_tmac_file_path,
        tmac_ch2_file_path=ch2_tmac_file_path,
        raw_behavior_file_path=bpod_behavior_file_path,
        subject_metadata=subject_metadata,
        nwbfile_path=nwbfile_path,
        dlc_file_path=dlc_file_path,
        video_file_path=behavior_video_file_path,
        stub_test=stub_test,
        overwrite=overwrite,
        verbose=True,
    )
