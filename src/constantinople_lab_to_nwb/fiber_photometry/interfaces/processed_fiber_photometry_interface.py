import re
from pathlib import Path
from typing import Union, Optional

import numpy as np
from neuroconv import BaseDataInterface
from pymatreader import read_mat
from pynwb import NWBFile

from constantinople_lab_to_nwb.fiber_photometry.utils import add_fiber_photometry_response_series


def fetch_matching_key_from_mat(mat_data: dict, pattern: str, expected_key: str = None):
    """
    Fetch data from a .mat file based on key matching using regex.

    Parameters:
        mat_data (dict): The data loaded from the .mat file.
        pattern (str): Regex pattern to match keys in the .mat file.

    Returns:
        np.ndarray: The data for the first matching key.

    Raises:
        KeyError: If no keys match the given pattern in the .mat file.
    """

    # Search for matching keys using regex
    matching_keys = [key for key in mat_data.keys() if re.search(pattern, key)]

    if not matching_keys:
        error_message = f"No keys matching the pattern '{pattern}' were found in the .mat file."
        if expected_key is not None:
            error_message = f"Expected data named '{expected_key}' not found in the tmac.mat file."
        raise KeyError(error_message)

    # Fetch the data for the first matched key
    matched_key = matching_keys[0]
    return matched_key


class ProcessedFiberPhotometryInterface(BaseDataInterface):
    """Data interface for converting processed fiber photometry data."""

    def __init__(
        self,
        tmac_ch1_file_path: Optional[Union[str, Path]] = None,
        tmac_ch2_file_path: Optional[Union[str, Path]] = None,
        verbose: bool = True,
    ) -> None:
        """
        Data interface for motion corrected fiber photometry data.

        Parameters
        ----------
        tmac_ch1_file_path: Optional[Union[str, Path]]
            The path to tmac_ch1 .mat file. Either 'tmac_ch1_file_path' or 'tmac_ch2_file_path' must be provided.
        tmac_ch2_file_path: Optional[Union[str, Path]]
            The path to the tmac_ch2 .mat file. (optional)
        verbose: bool
            Controls verbosity.
        """
        if tmac_ch1_file_path is None and tmac_ch2_file_path is None:
            raise ValueError("Either 'tmac_ch1_file_path' or 'tmac_ch2_file_path' must be provided.")

        self._has_tmac_ch1_file_path = False
        self._has_tmac_ch2_file_path = False

        if tmac_ch1_file_path is not None:
            tmac_ch1_file_path = Path(tmac_ch1_file_path)
            assert tmac_ch1_file_path.exists(), f"The file '{tmac_ch1_file_path}' does not exist."
            assert tmac_ch1_file_path.suffix == ".mat", f"Expected .mat file, got {tmac_ch1_file_path.suffix}."
            self._has_tmac_ch1_file_path = True

        if tmac_ch2_file_path is not None:
            tmac_ch2_file_path = Path(tmac_ch2_file_path)
            assert tmac_ch2_file_path.exists(), f"The file '{tmac_ch2_file_path}' does not exist."
            assert tmac_ch2_file_path.suffix == ".mat", f"Expected .mat file, got {tmac_ch2_file_path.suffix}."
            self._has_tmac_ch2_file_path = True

        super().__init__(tmac_ch1_file_path=tmac_ch1_file_path, tmac_ch2_file_path=tmac_ch2_file_path, verbose=verbose)

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        timestamps: Optional[list] = None,
        doric_acquisition_signal_name: str = "demodulated_fiber_photometry_signal",
    ) -> None:
        """
        Add processed fiber photometry data to the NWB file.

        Parameters
        ----------
        nwbfile : NWBFile
            The NWB file to which the data will be added.
        metadata : dict
            Dictionary containing metadata required for adding the FiberPhotometryResponseSeries.
            The metadata for the FiberPhotometryResponseSeries should be located in metadata["Ophys"]["FiberPhotometry"]["FiberPhotometryResponseSeries"].
        timestamps : list, optional
            The timestamps for the fiber photometry data. If not provided, the timestamps from the raw signal (Doric) will be used.
        doric_acquisition_signal_name : str, optional
            The name of the raw signal from Doric. Default is "demodulated_fiber_photometry_signal".
        """
        # find the source data file path that is not None
        # Consider sessions that might have only ch2 tmac file
        tmac_channels_data = []
        if self._has_tmac_ch1_file_path:
            tmac_channels_data.append(read_mat(filename=self.source_data["tmac_ch1_file_path"]))
        if self._has_tmac_ch2_file_path:
            tmac_channels_data.append(read_mat(filename=self.source_data["tmac_ch2_file_path"]))
        if len(tmac_channels_data) == 0:
            raise ValueError("No tmac file paths were provided.")

        # Not all tmac files have the same signal names, so we need to fetch them using regex matching
        estimated_motion_pattern = r"^estimated_motion"
        estimated_motion_column_name = fetch_matching_key_from_mat(
            tmac_channels_data[0],
            pattern=estimated_motion_pattern,
            expected_key="estimated_motion",
        )

        estimated_signal_pattern = r"^estimated_signal"
        estimated_signal_column_name = fetch_matching_key_from_mat(
            tmac_channels_data[0],
            pattern=estimated_signal_pattern,
            expected_key="estimated_signal",
        )

        mc_pattern = r"^g.*_mc$"
        mc_column_name = fetch_matching_key_from_mat(
            tmac_channels_data[0],
            pattern=mc_pattern,
            expected_key="green_mc",
        )

        photobleach_green_pattern = r"^(gfp|green)$"
        photobleach_green_column_name = fetch_matching_key_from_mat(
            tmac_channels_data[0],
            pattern=photobleach_green_pattern,
            expected_key="green",
        )
        photobleach_red_pattern = r"^(red|mcherry)$"
        photobleach_red_column_name = fetch_matching_key_from_mat(
            tmac_channels_data[0],
            pattern=photobleach_red_pattern,
            expected_key="red",
        )

        tmac_signal_name_mapping = dict(
            # The name of the normalized estimated signals in the tmac files
            normalized_estimated_signal=[estimated_signal_column_name, estimated_motion_column_name],
            # The name of the un-normalized estimated signals in the tmac files
            estimated_signal=[mc_column_name],
            # The name of the photobleach corrected signals in the tmac files
            photobleach_corrected_signal=[photobleach_green_column_name, photobleach_red_column_name],
        )

        raw_signal = nwbfile.get_acquisition(doric_acquisition_signal_name)
        timestamps = raw_signal.timestamps[:] if raw_signal is not None else timestamps
        if timestamps is None:
            raise ValueError(
                "When the raw signal from Doric is not added to the NWB file as acquisition, timestamps must be provided."
                "Use the 'timestamps' argument to provide the timestamps."
            )

        all_fiber_photometry_series_metadata = metadata["Ophys"]["FiberPhotometry"]["FiberPhotometryResponseSeries"]

        for (
            fiber_photometry_series_name,
            tmac_signal_names,
        ) in tmac_signal_name_mapping.items():
            fiber_photometry_series_metadata = next(
                (
                    series_metadata
                    for series_metadata in all_fiber_photometry_series_metadata
                    if series_metadata["name"] == fiber_photometry_series_name
                ),
                None,
            )
            if fiber_photometry_series_metadata is None:
                raise ValueError(
                    f"Metadata for '{fiber_photometry_series_name}' not found in the metadata."
                    f"Please add it in metadata['Ophys']['FiberPhotometry']['FiberPhotometryResponseSeries']."
                )

            traces_to_add = []
            for tmac_signal_name in tmac_signal_names:
                for tmac_data in tmac_channels_data:
                    tmac_data_keys = list(tmac_data.keys())
                    if tmac_signal_name not in tmac_data_keys:
                        raise ValueError(f"Trace '{tmac_signal_name}' not found in '{tmac_data_keys}'.")
                    trace = tmac_data[tmac_signal_name]
                    traces_to_add.append(trace)

            traces = np.vstack(traces_to_add).T

            if len(timestamps) != traces.shape[0]:
                raise ValueError(
                    f"Length of timestamps ({len(timestamps)}) and traces ({traces.shape[0]}) should be equal."
                )

            add_fiber_photometry_response_series(
                traces=traces,
                timestamps=timestamps,
                nwbfile=nwbfile,
                metadata=metadata,
                fiber_photometry_series_name=fiber_photometry_series_name,
                parent_container="processing/ophys",
            )
