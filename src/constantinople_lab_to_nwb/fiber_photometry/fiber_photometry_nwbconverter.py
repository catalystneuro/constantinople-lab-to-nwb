from pathlib import Path

from neuroconv import NWBConverter
from neuroconv.datainterfaces import DeepLabCutInterface, VideoInterface

from constantinople_lab_to_nwb.fiber_photometry.interfaces import (
    DoricFiberPhotometryInterface,
    DoricCsvFiberPhotometryInterface,
)
from constantinople_lab_to_nwb.general_interfaces import BpodBehaviorInterface
from neuroconv.datainterfaces.behavior.deeplabcut._dlc_utils import _get_movie_timestamps
from neuroconv.tools.signal_processing import get_rising_frames_from_ttl


class FiberPhotometryNWBConverter(NWBConverter):
    """Primary conversion class for converting the Fiber photometry dataset from the Constantinople Lab."""

    data_interface_classes = dict(
        DeepLabCut=DeepLabCutInterface,
        FiberPhotometryDoric=DoricFiberPhotometryInterface,
        FiberPhotometryCsv=DoricCsvFiberPhotometryInterface,
        Video=VideoInterface,
        Behavior=BpodBehaviorInterface,
    )

    def temporally_align_data_interfaces(self):
        if "FiberPhotometryDoric" in self.data_interface_objects:
            fiber_photometry_interface = self.data_interface_objects["FiberPhotometryDoric"]
            digital_stream_names = ["DigitalIO/DIO01", "DigitalIO/DIO02"]
            ttl_signals = fiber_photometry_interface._get_traces(stream_names=digital_stream_names)
            timestamps = fiber_photometry_interface.get_original_timestamps(stream_name=digital_stream_names[0])

        else:
            fiber_photometry_interface = self.data_interface_objects["FiberPhotometryCsv"]
            digital_stream_names = ["DI/O-1", "DI/O-2"]
            ttl_signals = fiber_photometry_interface._get_traces(channel_column_names=digital_stream_names)
            timestamps = fiber_photometry_interface.get_original_timestamps()

        raw_behavior_interface = self.data_interface_objects["Behavior"]
        trial_start_times_from_bpod, _ = raw_behavior_interface.get_trial_times()
        bpod_first_trial_start_time = trial_start_times_from_bpod[0]
        center_port_relative = raw_behavior_interface._bpod_struct["RawEvents"]["Trial"][0]["Events"]["Port2In"]
        center_port_relative = (
            center_port_relative[0] if isinstance(center_port_relative, list) else center_port_relative
        )

        # we are aligning the ttl signals to the raw bpod trial start times
        rising_frames_from_center_port_ttl = get_rising_frames_from_ttl(ttl_signals[:, 1])
        center_port_aligned_times = timestamps[rising_frames_from_center_port_ttl]

        time_shift = (bpod_first_trial_start_time + center_port_relative) - center_port_aligned_times[0]
        fiber_photometry_interface.set_aligned_starting_time(aligned_starting_time=time_shift)

        has_deep_lab_cut = "DeepLabCut" in self.data_interface_objects
        has_video = "Video" in self.data_interface_objects
        if has_deep_lab_cut and has_video:
            video_interface = self.data_interface_objects["Video"]
            movie_file_path = video_interface.source_data["file_paths"][0]

            rising_frames_from_camera_ttl = get_rising_frames_from_ttl(ttl_signals[:, 0])
            timestamps_from_camera_ttl = timestamps[rising_frames_from_camera_ttl]
            aligned_timestamps_camera = timestamps_from_camera_ttl + time_shift
            video_interface.set_aligned_segment_starting_times([aligned_timestamps_camera[0]])

            dlc_interface = self.data_interface_objects["DeepLabCut"]
            movie_timestamps = _get_movie_timestamps(movie_file=str(movie_file_path))
            aligned_dlc_timestamps = movie_timestamps + aligned_timestamps_camera[0]
            dlc_interface.set_aligned_timestamps(aligned_timestamps=aligned_dlc_timestamps)
