"""Primary script to run to convert an entire session for of data using the NWBConverter."""
import os
from pathlib import Path
from typing import Union

from dateutil import tz
from neuroconv.datainterfaces import OpenEphysBinaryRecordingInterface
from neuroconv.utils import load_dict_from_file, dict_deep_update

from constantinople_lab_to_nwb.schierek_embargo_2024 import SchierekEmbargo2024NWBConverter


def session_to_nwb(
        openephys_recording_folder_path: Union[str, Path],
        nwbfile_path: Union[str, Path],
        stub_test: bool = False,
        overwrite: bool = False,
):
    """
    Convert a session of data to NWB format.

    Parameters
    ----------
    openephys_recording_folder_path : str or Path
        The path to the OpenEphys recording folder.
    nwbfile_path : str or Path
        The path to the NWB file to write.
    stub_test : bool, default: False
        Whether to run a stub test conversion.
    overwrite : bool, default: False
        Whether to overwrite an existing NWB file.
    """
    source_data = dict()
    conversion_options = dict()

    # Add Recording
    stream_names = OpenEphysBinaryRecordingInterface.get_stream_names(folder_path=openephys_recording_folder_path)
    stream_name_raw = [stream_name for stream_name in stream_names if "AP" in stream_name][0]
    stream_name_lfp = [stream_name for stream_name in stream_names if "LFP" in stream_name][0]

    source_data.update(
        dict(
            RecordingAP=dict(folder_path=openephys_recording_folder_path, stream_name=stream_name_raw),
            RecordingLFP=dict(folder_path=openephys_recording_folder_path, stream_name=stream_name_lfp),
        ),
    )
    conversion_options.update(
        dict(
            RecordingAP=dict(stub_test=stub_test),
            RecordingLFP=dict(stub_test=stub_test, write_as="lfp"),
        ),
    )

    # Add Sorting
    # source_data.update(dict(Sorting=dict()))
    # conversion_options.update(dict(Sorting=dict()))

    # Add Behavior
    # source_data.update(dict(Behavior=dict()))
    # conversion_options.update(dict(Behavior=dict()))

    recording_folder_name = Path(openephys_recording_folder_path).parent.stem
    subject_id, session_id = recording_folder_name.split("_", maxsplit=1)

    converter = SchierekEmbargo2024NWBConverter(source_data=source_data)

    # Add datetime to conversion
    metadata = converter.get_metadata()
    session_start_time = metadata["NWBFile"]["session_start_time"]
    tzinfo = tz.gettz("America/New_York")
    metadata["NWBFile"].update(
        session_start_time=session_start_time.replace(tzinfo=tzinfo),
        session_id=session_id,
    )

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "schierek_embargo_2024_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

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
    recording_folder_path = Path("/Volumes/t7-ssd/GCP/Constantinople/J076_2023-12-06_13-24-28/Record Node 117")
    nwbfile_path = Path("/Volumes/t7-ssd/GCP/Constantinople/nwbfiles/J076_2023-12-06_13-24-28.nwb")
    if not nwbfile_path.parent.exists():
        os.makedirs(nwbfile_path.parent, exist_ok=True)

    stub_test = True
    overwrite = True

    session_to_nwb(
        openephys_recording_folder_path=recording_folder_path,
        nwbfile_path=nwbfile_path,
        stub_test=stub_test,
        overwrite=overwrite,
    )
