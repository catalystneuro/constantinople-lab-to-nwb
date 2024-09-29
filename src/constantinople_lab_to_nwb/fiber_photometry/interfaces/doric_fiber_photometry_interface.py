from pathlib import Path
from typing import Union, Literal

import h5py
import numpy as np
from ndx_fiber_photometry import FiberPhotometryResponseSeries
from neuroconv import BaseTemporalAlignmentInterface
from neuroconv.tools import get_module
from pynwb import NWBFile

from constantinople_lab_to_nwb.fiber_photometry.utils import add_fiber_photometry_table, add_fiber_photometry_devices


class DoricFiberPhotometryInterface(BaseTemporalAlignmentInterface):
    """Behavior interface for fiber photometry conversion"""

    def __init__(
        self,
        file_path: Union[str, Path],
        stream_name: str,
        verbose: bool = True,
    ):
        self._timestamps = None
        super().__init__(file_path=file_path, stream_name=stream_name, verbose=verbose)

    def load(self, stream_name: str):
        file_path = Path(self.source_data["file_path"])
        # check if suffix is .doric
        if file_path.suffix != ".doric":
            raise ValueError(f"File '{file_path}' is not a .doric file.")

        channel_group = h5py.File(file_path, mode="r")[stream_name]
        if "Time" not in channel_group.keys():
            raise ValueError(f"Time not found in '{stream_name}'.")
        return channel_group

    def get_original_timestamps(self) -> np.ndarray:
        channel_group = self.load(stream_name=self.source_data["stream_name"])
        return channel_group["Time"][:]

    def get_timestamps(self, stub_test: bool = False) -> np.ndarray:
        timestamps = self._timestamps if self._timestamps is not None else self.get_original_timestamps()
        if stub_test:
            return timestamps[:100]
        return timestamps

    def set_aligned_timestamps(self, aligned_timestamps: np.ndarray) -> None:
        self._timestamps = np.array(aligned_timestamps)

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        fiber_photometry_series_name: str,
        parent_container: Literal["acquisition", "processing/ophys"] = "acquisition",
        stub_test: bool = False,
    ) -> None:

        add_fiber_photometry_devices(nwbfile=nwbfile, metadata=metadata)

        fiber_photometry_metadata = metadata["Ophys"]["FiberPhotometry"]
        traces_metadata = fiber_photometry_metadata["FiberPhotometryResponseSeries"]
        trace_metadata = next(
            (trace for trace in traces_metadata if trace["name"] == fiber_photometry_series_name),
            None,
        )
        if trace_metadata is None:
            raise ValueError(f"Trace metadata for '{fiber_photometry_series_name}' not found.")

        add_fiber_photometry_table(nwbfile=nwbfile, metadata=metadata)
        fiber_photometry_table = nwbfile.lab_meta_data["FiberPhotometry"].fiber_photometry_table

        row_indices = trace_metadata["fiber_photometry_table_region"]
        device_fields = [
            "optical_fiber",
            "excitation_source",
            "photodetector",
            "dichroic_mirror",
            "indicator",
            "excitation_filter",
            "emission_filter",
        ]
        for row_index in row_indices:
            row_metadata = fiber_photometry_metadata["FiberPhotometryTable"]["rows"][row_index]
            row_data = {field: nwbfile.devices[row_metadata[field]] for field in device_fields if field in row_metadata}
            row_data["location"] = row_metadata["location"]
            if "coordinates" in row_metadata:
                row_data["coordinates"] = row_metadata["coordinates"]
            if "commanded_voltage_series" in row_metadata:
                row_data["commanded_voltage_series"] = nwbfile.acquisition[row_metadata["commanded_voltage_series"]]
            fiber_photometry_table.add_row(**row_data)

        stream_name = trace_metadata["stream_name"]
        stream_indices = trace_metadata["stream_indices"]

        traces_to_add = []
        data = self.load(stream_name=stream_name)
        channel_names = list(data.keys())
        for stream_index in stream_indices:
            trace = data[channel_names[stream_index]]
            trace = trace[:100] if stub_test else trace[:]
            traces_to_add.append(trace)

        traces = np.vstack(traces_to_add).T

        fiber_photometry_table_region = fiber_photometry_table.create_fiber_photometry_table_region(
            description=trace_metadata["fiber_photometry_table_region_description"],
            region=trace_metadata["fiber_photometry_table_region"],
        )

        # Get the timing information
        timestamps = self.get_timestamps(stub_test=stub_test)

        fiber_photometry_response_series = FiberPhotometryResponseSeries(
            name=trace_metadata["name"],
            description=trace_metadata["description"],
            data=traces,
            unit=trace_metadata["unit"],
            fiber_photometry_table_region=fiber_photometry_table_region,
            timestamps=timestamps,
        )

        if parent_container == "acquisition":
            nwbfile.add_acquisition(fiber_photometry_response_series)
        elif parent_container == "processing/ophys":
            ophys_module = get_module(
                nwbfile,
                name="ophys",
                description="Contains the processed fiber photometry data.",
            )
            ophys_module.add(fiber_photometry_response_series)
