from pathlib import Path
from typing import Union

import h5py
import numpy as np
import pandas as pd
from neuroconv import BaseTemporalAlignmentInterface
from pynwb import NWBFile

from constantinople_lab_to_nwb.fiber_photometry.utils import add_fiber_photometry_response_series


class DoricFiberPhotometryInterface(BaseTemporalAlignmentInterface):
    """Behavior interface for fiber photometry conversion"""

    def __init__(
        self,
        file_path: Union[str, Path],
        time_column_name: str = "Time",
        verbose: bool = True,
    ):
        super().__init__(file_path=file_path, verbose=verbose)
        self._timestamps = None
        self._time_column_name = time_column_name

    def load(self):
        file_path = Path(self.source_data["file_path"])
        # check if suffix is .doric
        if file_path.suffix != ".doric":
            raise ValueError(f"File '{file_path}' is not a .doric file.")

        return h5py.File(file_path, mode="r")

    def get_original_timestamps(self, stream_name=str) -> np.ndarray:
        channel_group = self.load()[stream_name]
        if self._time_column_name not in channel_group:
            raise ValueError(f"Time column '{self._time_column_name}' not found in '{stream_name}'.")
        return channel_group[self._time_column_name][:]

    def get_timestamps(self, stream_name=str, stub_test: bool = False) -> np.ndarray:
        timestamps = (
            self._timestamps if self._timestamps is not None else self.get_original_timestamps(stream_name=stream_name)
        )
        if stub_test:
            return timestamps[:100]
        return timestamps

    def set_aligned_timestamps(self, aligned_timestamps: np.ndarray) -> None:
        self._timestamps = np.array(aligned_timestamps)

    def _get_traces(self, stream_name: str, channel_ids: list, stub_test: bool = False):
        traces_to_add = []
        data = self.load()
        if stream_name not in data:
            raise ValueError(f"Stream '{stream_name}' not found in '{self.source_data['file_path']}'.")
        channel_group = data[stream_name]
        all_channel_names = list(channel_group.keys())
        for channel_name in channel_ids:
            if channel_name not in all_channel_names:
                raise ValueError(f"Channel '{channel_name}' not found in '{stream_name}'.")
            trace = channel_group[channel_name]
            trace = trace[:100] if stub_test else trace[:]
            traces_to_add.append(trace)

        traces = np.vstack(traces_to_add).T
        return traces

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: bool = False,
    ) -> None:

        fiber_photometry_metadata = metadata["Ophys"]["FiberPhotometry"]
        for trace_metadata in fiber_photometry_metadata["FiberPhotometryResponseSeries"]:
            fiber_photometry_series_name = trace_metadata["name"]
            stream_name = trace_metadata["stream_name"]
            channel_ids = trace_metadata["channel_ids"]

            traces = self._get_traces(stream_name=stream_name, channel_ids=channel_ids, stub_test=stub_test)
            # Get the timing information
            timestamps = self.get_timestamps(stream_name=stream_name, stub_test=stub_test)

            parent_container = "processing/ophys"
            if fiber_photometry_series_name == "fiber_photometry_response_series":
                parent_container = "acquisition"

            add_fiber_photometry_response_series(
                traces=traces,
                timestamps=timestamps,
                nwbfile=nwbfile,
                metadata=metadata,
                fiber_photometry_series_name=fiber_photometry_series_name,
                parent_container=parent_container,
            )


class DoricCsvFiberPhotometryInterface(BaseTemporalAlignmentInterface):

    def __init__(
        self,
        file_path: Union[str, Path],
        time_column_name: str = "Time(s)",
        verbose: bool = True,
    ):
        super().__init__(file_path=file_path, verbose=verbose)
        self._time_column_name = time_column_name
        self._timestamps = None

    def get_original_timestamps(self) -> np.ndarray:
        df = self.load()
        return df[self._time_column_name].values

    def get_timestamps(self, stub_test: bool = False) -> np.ndarray:
        timestamps = self._timestamps if self._timestamps is not None else self.get_original_timestamps()
        if stub_test:
            return timestamps[:100]
        return timestamps

    def set_aligned_timestamps(self, aligned_timestamps: np.ndarray) -> None:
        self._timestamps = np.array(aligned_timestamps)

    def load(self):
        file_path = Path(self.source_data["file_path"])
        # check if suffix is .doric
        if file_path.suffix != ".csv":
            raise ValueError(f"File '{file_path}' is not a .csv file.")

        df = pd.read_csv(
            file_path,
            header=1,
            index_col=False,
        )
        if self._time_column_name not in df.columns:
            raise ValueError(f"Time column not found in '{file_path}'.")
        return df

    def _get_traces(self, channel_column_names: list, stub_test: bool = False):
        traces_to_add = []
        data = self.load()
        for channel_name in channel_column_names:
            if channel_name not in data.columns:
                raise ValueError(f"Channel '{channel_name}' not found in '{self.source_data['file_path']}'.")
            trace = data[channel_name]
            trace = trace[:100] if stub_test else trace
            traces_to_add.append(trace)

        traces = np.vstack(traces_to_add).T
        return traces

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: bool = False,
    ) -> None:

        fiber_photometry_metadata = metadata["Ophys"]["FiberPhotometry"]

        for trace_metadata in fiber_photometry_metadata["FiberPhotometryResponseSeries"]:
            fiber_photometry_series_name = trace_metadata["name"]
            channel_column_names = trace_metadata["channel_column_names"]

            parent_container = "processing/ophys"
            if fiber_photometry_series_name == "fiber_photometry_response_series":
                parent_container = "acquisition"

            add_fiber_photometry_response_series(
                traces=self._get_traces(channel_column_names=channel_column_names, stub_test=stub_test),
                timestamps=self.get_timestamps(stub_test=stub_test),
                nwbfile=nwbfile,
                metadata=metadata,
                fiber_photometry_series_name=fiber_photometry_series_name,
                parent_container=parent_container,
            )
