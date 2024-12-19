"""Primary script to run to convert all sessions in a dataset using session_to_nwb."""

import os
import traceback
from concurrent.futures import (
    ProcessPoolExecutor,
    as_completed,
)
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from pprint import pformat
from typing import Union
from warnings import warn

import numpy as np
import pandas as pd
from neuroconv.utils import load_dict_from_file
from tqdm import tqdm

from constantinople_lab_to_nwb.fiber_photometry.fiber_photometry_convert_session import session_to_nwb

from constantinople_lab_to_nwb.utils import get_subject_metadata_from_rat_info_folder

import warnings

# Ignore specific warnings
warnings.filterwarnings("ignore", message="Date is missing timezone information. Updating to local timezone.")
warnings.filterwarnings(
    "ignore",
    message="The linked table for DynamicTableRegion 'event_type' does not share an ancestor with the DynamicTableRegion.",
)
warnings.filterwarnings(
    "ignore",
    message="The linked table for DynamicTableRegion 'state_type' does not share an ancestor with the DynamicTableRegion.",
)
warnings.filterwarnings(
    "ignore",
    message="The linked table for DynamicTableRegion 'action_type' does not share an ancestor with the DynamicTableRegion.",
)


def update_default_fiber_photometry_metadata(
    session_data: pd.DataFrame,
    metadata: dict,
) -> dict:

    indicators_manufacturers = {
        "AAV9-hsyn-GRAB-DA2h": "Addgene",
        "AAV1-CB7-CI-mCherry": "Addgene",
        "AAV9-hSyn-ACh4.3": "WZ Biosciences",
    }

    metadata_copy = deepcopy(metadata)
    fiber_photometry_metadata_copy = metadata_copy["Ophys"]["FiberPhotometry"]

    non_empty_channel_column_names = [
        col for col in session_data.columns if "_name" in col and session_data[col].notnull().all()
    ]
    stream_names = [session_data[col].values[0] for col in non_empty_channel_column_names]

    fiber_photometry_table_region = list(range(len(non_empty_channel_column_names)))
    channel_table_region_mapping = dict(zip(non_empty_channel_column_names, fiber_photometry_table_region))

    # Update the FiberPhotometryResponseSeries metadata
    all_fiber_photometry_response_series_metadata = fiber_photometry_metadata_copy["FiberPhotometryResponseSeries"]
    demodulated_fiber_photometry_signal_metadata = next(
        (
            series
            for series in all_fiber_photometry_response_series_metadata
            if series["name"] == "demodulated_fiber_photometry_signal"
        ),
        None,
    )

    demodulated_fiber_photometry_signal_metadata.update(
        fiber_photometry_table_region=fiber_photometry_table_region,
        stream_names=stream_names,
    )

    indicators_to_add = []
    added_indicators = set()

    excitation_sources_to_add = []
    added_excitation_sources = set()

    default_rows_in_fiber_photometry_table = fiber_photometry_metadata_copy["FiberPhotometryTable"]["rows"]
    fiber_photometry_table_rows = []
    for region, channel_column_name in zip(fiber_photometry_table_region, non_empty_channel_column_names):
        fiber_name, analog_channel_name, _ = channel_column_name.split("_")
        row_metadata = next(
            (row for row in default_rows_in_fiber_photometry_table if row["name"] == region),
            None,
        )
        if row_metadata is None:
            raise ValueError(
                f"FiberPhotometryTable metadata for row name '{region}' not found in metadata['FiberPhotometryTable']['rows']."
            )
        coordinates = [session_data[f"{fiber_name}_{coord}"].values[0] for coord in ["AP", "ML", "DV"]]
        coordinates = [coord if coord is not None else np.nan for coord in coordinates]  # replace None with np.nan

        fiber_region = session_data[f"{fiber_name}_region"].values[0]
        fiber_region = fiber_region if fiber_region is not None else "unknown"
        row_metadata.update(
            location=fiber_region,
            coordinates=coordinates,
        )

        indicator_label_column_name = f"{fiber_name}_{analog_channel_name}_virus"
        if indicator_label_column_name not in session_data.columns:
            raise ValueError(f"Column '{indicator_label_column_name}' not found in '{dataset_excel_file_path}'.")
        indicator_label = session_data[indicator_label_column_name].values[0]
        indicator_label = indicator_label.replace("_", "-")

        idicator_name_column_name = f"{fiber_name}_{analog_channel_name}_Fluorophore"
        if idicator_name_column_name not in session_data.columns:
            raise ValueError(f"Column '{idicator_name_column_name}' not found in '{dataset_excel_file_path}'.")
        indicator_name = session_data[idicator_name_column_name].values[0]
        indicator_name = indicator_name.replace(" ", "_").lower()

        indicator_metadata = dict(
            name=indicator_name,
            description=f"The {indicator_name} fluorophore.",
            label=indicator_label,
            manufacturer=indicators_manufacturers.get(indicator_label, "unknown"),
        )

        if indicator_name not in added_indicators:
            added_indicators.add(indicator_name)
            indicators_to_add.append(indicator_metadata)

        excitation_wavelength_column_name = f"{fiber_name}_{analog_channel_name}_excitation"
        if excitation_wavelength_column_name not in session_data.columns:
            raise ValueError(f"Column '{excitation_wavelength_column_name}' not found in '{dataset_excel_file_path}'.")
        excitation_wavelength = session_data[excitation_wavelength_column_name].values[0]

        try:
            has_interval = "-" in str(excitation_wavelength)
            excitation_wavelength_max_value = (
                excitation_wavelength.split("-")[-1] if has_interval else excitation_wavelength
            )
            excitation_wavelength_nm = float(excitation_wavelength_max_value)
        except ValueError:
            raise ValueError(
                f"The excitation wavelength must be a number (e.g. 470) and not provided as '{excitation_wavelength}'."
            )

        excitation_source_name = f"excitation_source_{indicator_name}"
        excitation_source_metadata = dict(
            name=excitation_source_name,
            description=f"The excitation wavelength for {indicator_name} indicator.",
            excitation_wavelength_in_nm=excitation_wavelength_nm,
            illumination_type="LED",
            manufacturer="Doric Lenses",
        )
        if excitation_source_name not in added_excitation_sources:
            added_excitation_sources.add(excitation_source_name)
            excitation_sources_to_add.append(excitation_source_metadata)

        row_metadata.update(
            indicator=indicator_name,
            excitation_source=excitation_source_name,
        )
        fiber_photometry_table_rows.append(row_metadata)

    # update the motion corrected data table region
    normalized_estimated_signal_default_channel_column_names = [
        "cordA_AnalogCh1_name",  # cord A green
        "cordA_AnalogCh2_name",  # cord A red
        "cordB_AnalogCh1_name",  # cord B green
        "cordB_AnalogCh2_name",  # cord B red
    ]
    normalized_estimated_signal_table_region = [
        channel_table_region_mapping[col]
        for col in normalized_estimated_signal_default_channel_column_names
        if col in channel_table_region_mapping
    ]
    normalized_estimated_signal_metadata = next(
        (
            series
            for series in all_fiber_photometry_response_series_metadata
            if series["name"] == "normalized_estimated_signal"
        ),
        None,
    )
    if normalized_estimated_signal_metadata is None:
        raise ValueError(
            f"Metadata for 'normalized_estimated_signal' not found in the metadata."
            f"Please add it in metadata['Ophys']['FiberPhotometry']['FiberPhotometryResponseSeries']."
        )
    normalized_estimated_signal_metadata.update(
        fiber_photometry_table_region=normalized_estimated_signal_table_region,
    )
    photobleach_corrected_signal_metadata = next(
        (
            series
            for series in all_fiber_photometry_response_series_metadata
            if series["name"] == "photobleach_corrected_signal"
        ),
        None,
    )
    if photobleach_corrected_signal_metadata is None:
        raise ValueError(
            f"Metadata for 'photobleach_corrected_signal' not found in the metadata."
            f"Please add it in metadata['Ophys']['FiberPhotometry']['FiberPhotometryResponseSeries']."
        )
    photobleach_corrected_signal_metadata.update(
        fiber_photometry_table_region=normalized_estimated_signal_table_region,
    )

    # update the estimated signal data table region
    estimated_signal_default_channel_column_names = [
        "cordA_AnalogCh1_name",  # cord A green
        "cordB_AnalogCh1_name",  # cord B green
    ]
    estimated_signal_table_region = [
        channel_table_region_mapping[col]
        for col in estimated_signal_default_channel_column_names
        if col in channel_table_region_mapping
    ]
    estimated_signal_metadata = next(
        (series for series in all_fiber_photometry_response_series_metadata if series["name"] == "estimated_signal"),
        None,
    )
    if estimated_signal_metadata is None:
        raise ValueError(
            f"Metadata for 'estimated_signal' not found in the metadata."
            f"Please add it in metadata['Ophys']['FiberPhotometry']['FiberPhotometryResponseSeries']."
        )
    estimated_signal_metadata.update(
        fiber_photometry_table_region=estimated_signal_table_region,
    )

    fiber_photometry_metadata_copy.update(
        FiberPhotometryResponseSeries=all_fiber_photometry_response_series_metadata,
        Indicators=indicators_to_add,
        ExcitationSources=excitation_sources_to_add,
    )
    fiber_photometry_metadata_copy["FiberPhotometryTable"].update(
        rows=fiber_photometry_table_rows,
    )

    return metadata_copy


def dataset_to_nwb(
    dataset_excel_file_path: Union[str, Path],
    output_folder_path: Union[str, Path],
    rat_info_folder_path: Union[str, Path],
    max_workers: int = 1,
    overwrite: bool = False,
    verbose: bool = True,
):
    """Convert the entire dataset to NWB.

    Parameters
    ----------
    dataset_excel_file_path : Union[str, Path]
        The path to the Excel file containing the dataset information.
    output_folder_path : Union[str, Path]
        The path to the directory where the NWB files will be saved.
    rat_info_folder_path : Union[str, Path]
        The path to the directory containing the rat info files.
    max_workers : int, optional
        The number of workers to use for parallel processing, by default 1
    overwrite : bool, optional
        Whether to overwrite the NWB file if it already exists, by default False.
    verbose : bool, optional
        Whether to print verbose output, by default True
    """
    dataset_excel_file_path = Path(dataset_excel_file_path)
    os.makedirs(output_folder_path, exist_ok=True)

    session_to_nwb_kwargs_per_session = [
        session_to_nwb_kwargs
        for session_to_nwb_kwargs in get_session_to_nwb_kwargs_per_session(
            dataset_excel_file_path=dataset_excel_file_path,
            rat_info_folder_path=rat_info_folder_path,
            overwrite=overwrite,
        )
    ]

    futures = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for session_to_nwb_kwargs in session_to_nwb_kwargs_per_session:
            session_to_nwb_kwargs.update(verbose=verbose, overwrite=overwrite)
            nwbfile_path = Path(session_to_nwb_kwargs["nwbfile_path"])
            nwbfile_name = nwbfile_path.stem
            exception_file_path = nwbfile_path.parent / f"ERROR_{nwbfile_name}.txt"
            futures.append(
                executor.submit(
                    safe_session_to_nwb,
                    session_to_nwb_kwargs=session_to_nwb_kwargs,
                    exception_file_path=exception_file_path,
                )
            )
        for _ in tqdm(
            as_completed(futures),
            total=len(futures),
        ):
            pass


def safe_session_to_nwb(
    *,
    session_to_nwb_kwargs: dict,
    exception_file_path: Union[Path, str],
):
    """Convert a session to NWB while handling any errors by recording error messages to the exception_file_path.

    Parameters
    ----------
    session_to_nwb_kwargs : dict
        The arguments for session_to_nwb.
    exception_file_path : Path
        The path to the file where the exception messages will be saved.
    """
    exception_file_path = Path(exception_file_path)
    try:
        session_to_nwb(**session_to_nwb_kwargs)
    except Exception as e:
        warn(
            f"There was an error converting this session to NWB. The error message has been saved to '{exception_file_path}'."
        )
        with open(
            exception_file_path,
            mode="w",
        ) as f:
            f.write(f"session_to_nwb_kwargs: \n {pformat(session_to_nwb_kwargs)}\n\n")
            f.write(traceback.format_exc())


def get_session_to_nwb_kwargs_per_session(
    *,
    dataset_excel_file_path: Union[str, Path],
    rat_info_folder_path: Union[str, Path],
    overwrite: bool = False,
):
    """Get the kwargs for session_to_nwb for each session in the dataset.

    Parameters
    ----------
    dataset_excel_file_path : Union[str, Path]
        The path to the directory containing the raw data.
    rat_info_folder_path : Union[str, Path]
        The path to the directory containing the rat info files.
    overwrite : bool, optional
        Whether to overwrite the NWB file if it already exists, by default False.

    Returns
    -------
    list[dict[str, Any]]
        A list of dictionaries containing the kwargs for session_to_nwb for each session.
    """

    dataset = pd.read_excel(dataset_excel_file_path)

    dataset = dataset.replace({np.nan: None})
    # fix possible typos in the column names
    dataset.columns = dataset.columns.str.replace(r"AnlogCh(\d+)", r"AnalogCh\1", regex=True)
    dataset.columns = dataset.columns.str.replace(r"Flourophore", r"Fluorophore", regex=True)

    dataset_grouped = dataset.groupby(["subject_id", "session_id"])
    for (subject_id, session_id), session_data in dataset_grouped:
        nwbfile_path = output_folder_path / f"sub-{subject_id}_ses-{session_id}.nwb"
        if nwbfile_path.exists() and not overwrite:
            warn(f"File '{nwbfile_path}' already exists. Skipping.")
            continue

        if "raw_fiber_photometry_file_path" not in dataset.columns:
            raise ValueError(
                f"The excel table '{dataset_excel_file_path}' must contain a column named 'raw_fiber_photometry_file_path'."
            )
        dataset["raw_fiber_photometry_file_path"] = dataset["raw_fiber_photometry_file_path"].str.strip("'")

        raw_fiber_photometry_file_path = session_data["raw_fiber_photometry_file_path"].values[0]
        raw_fiber_photometry_file_path = Path(raw_fiber_photometry_file_path)
        if not raw_fiber_photometry_file_path.exists():
            raise FileNotFoundError(f"File '{raw_fiber_photometry_file_path}' not found.")

        required_column_names = [
            "dlc_file_path",
            "video_file_path",
            "bpod_file_path",
            "tmac_ch1_file_path",
            "tmac_ch2_file_path",
        ]
        if not all(column in session_data.columns for column in required_column_names):
            missing_columns = [column for column in required_column_names if column not in session_data.columns]
            raise ValueError(
                f"Missing required columns: {', '.join(missing_columns)}. Please add them as columns in"
                f"{dataset_excel_file_path}."
            )

        dlc_file_path = session_data["dlc_file_path"].values[0]
        video_file_path = session_data["video_file_path"].values[0]
        behavior_file_path = session_data["bpod_file_path"].values[0]
        tmac_ch1_file_path = session_data["tmac_ch1_file_path"].values[0]
        tmac_ch2_file_path = session_data["tmac_ch2_file_path"].values[0]

        default_fiber_photometry_metadata_yaml_file_path = (
            Path(__file__).parent / "metadata" / "doric_fiber_photometry_metadata.yaml"
        )
        default_fiber_photometry_metadata = load_dict_from_file(
            file_path=default_fiber_photometry_metadata_yaml_file_path
        )
        fiber_photometry_metadata = update_default_fiber_photometry_metadata(
            session_data=session_data, metadata=default_fiber_photometry_metadata
        )

        try:
            date_obj = datetime.strptime(str(session_id), "%Y%m%d")
            date_str = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            raise ValueError(
                f"Invalid date format received when trying to get subject metadata from '{rat_info_folder_path}', "
                f"in session_id '{session_id}'. Expected format is 'YYYYMMDD' (e.g. '20210528')."
            )

        subject_metadata = get_subject_metadata_from_rat_info_folder(
            folder_path=rat_info_folder_path,
            subject_id=subject_id,
            date=date_str,
        )

        yield dict(
            raw_fiber_photometry_file_path=raw_fiber_photometry_file_path,
            nwbfile_path=nwbfile_path,
            raw_behavior_file_path=behavior_file_path,
            tmac_ch1_file_path=tmac_ch1_file_path,
            tmac_ch2_file_path=tmac_ch2_file_path,
            dlc_file_path=dlc_file_path,
            video_file_path=video_file_path,
            fiber_photometry_metadata=fiber_photometry_metadata,
            subject_metadata=subject_metadata,
        )


if __name__ == "__main__":

    # Parameters for conversion

    # The path to the Excel file containing the fiber photometry table.
    # Each row in the table should contain the information for a single session that will be converted to NWB.
    dataset_excel_file_path = Path("/Users/weian/Desktop/Example_photometry_table.xlsx")
    # The path to the directory where the NWB files will be saved.
    output_folder_path = Path("/Users/weian/data/nwbfiles_test")
    # The path to the directory containing the rat info files. (rat registry, mass registry) required for adding subject metadata.
    rat_registry_folder_path = "/Volumes/T9/Constantinople/Rat_info"

    # The number of workers to use for parallel processing, by default 1
    max_workers = 1
    # Whether to overwrite the NWB file if it already exists.
    overwrite = False
    # Whether to print verbose output.
    verbose = False

    dataset_to_nwb(
        dataset_excel_file_path=dataset_excel_file_path,
        output_folder_path=output_folder_path,
        rat_info_folder_path=rat_registry_folder_path,
        max_workers=max_workers,
        verbose=verbose,
        overwrite=overwrite,
    )
