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

import numpy as np
import pandas as pd
from neuroconv.utils import load_dict_from_file
from tqdm import tqdm

from constantinople_lab_to_nwb.fiber_photometry.fiber_photometry_convert_session import session_to_nwb

from constantinople_lab_to_nwb.utils import get_subject_metadata_from_rat_info_folder


def update_default_fiber_photometry_metadata(
    session_data: pd.DataFrame,
):

    session_data = session_data.reset_index(drop=True)
    raw_fiber_photometry_file_path = session_data["raw_fiber_photometry_file_path"].values[0]
    raw_fiber_photometry_file_path = Path(raw_fiber_photometry_file_path)

    if raw_fiber_photometry_file_path.suffix == ".csv":
        default_fiber_photometry_metadata_yaml_file_path = (
            Path(__file__).parent / "metadata" / "doric_csv_fiber_photometry_metadata.yaml"
        )
    elif raw_fiber_photometry_file_path.suffix == ".doric":
        default_fiber_photometry_metadata_yaml_file_path = (
            Path(__file__).parent / "metadata" / "doric_fiber_photometry_metadata.yaml"
        )

    session_data["fiber_photometry_table_region"] = session_data.groupby(
        ["emission_wavelength_nm", "excitation_wavelength_nm"]
    ).ngroup()
    session_data.sort_values(by=["fiber_photometry_table_region"], inplace=True)

    # For debugging print the DataFrame
    # pd.set_option('display.max_rows', None)  # Show all rows
    # pd.set_option('display.max_columns', None)  # Show all columns
    # pd.set_option('display.width', 1000)  # Set display width to avoid wrapping
    # pd.set_option('display.max_colwidth', None)  # Show full column content
    #
    # # Your code to create and print the DataFrame
    # print(session_data[["emission_wavelength_nm", "excitation_wavelength_nm", "fiber_photometry_table_region"]])

    default_fiber_photometry_metadata = load_dict_from_file(file_path=default_fiber_photometry_metadata_yaml_file_path)
    fiber_photometry_metadata_copy = deepcopy(default_fiber_photometry_metadata)

    series_metadata = fiber_photometry_metadata_copy["Ophys"]["FiberPhotometry"]["FiberPhotometryResponseSeries"]
    default_fiber_photometry_table_metadata = fiber_photometry_metadata_copy["Ophys"]["FiberPhotometry"][
        "FiberPhotometryTable"
    ]

    indicators_metadata = fiber_photometry_metadata_copy["Ophys"]["FiberPhotometry"]["Indicators"]
    excitation_sources_metadata = fiber_photometry_metadata_copy["Ophys"]["FiberPhotometry"]["ExcitationSources"]

    default_rows_in_fiber_photometry_table = default_fiber_photometry_table_metadata["rows"]

    fiber_photometry_table_rows = []
    indicators_to_add = []
    excitation_sources_to_add = []
    for region, region_data in session_data.groupby("fiber_photometry_table_region"):
        row_metadata = next(
            (row for row in default_rows_in_fiber_photometry_table if row["name"] == region),
            None,
        )
        if row_metadata is None:
            raise ValueError(
                f"FiberPhotometryTable metadata for row name '{region}' not found in '{default_fiber_photometry_metadata_yaml_file_path}'."
            )
        # if any(~region_data[["fiber_position_AP", "fiber_position_ML", "fiber_position_DV"]].isna().values[0]):
        #     row_metadata.update(coordinates=region_data[["fiber_position_AP", "fiber_position_ML", "fiber_position_DV"]].values[0])
        #
        coordinates = region_data[["fiber_position_AP", "fiber_position_ML", "fiber_position_DV"]].values[0]

        indicator_label = region_data["indicator_label"].values[0]
        indicator_label = indicator_label.replace("_", "-")
        indicator_metadata = next(
            (indicator for indicator in indicators_metadata if indicator["label"] == indicator_label),
            None,
        )
        if indicator_metadata is None:
            raise ValueError(
                f"Indicator metadata for '{indicator_label}' not found in '{default_fiber_photometry_metadata_yaml_file_path}'."
            )
        indicators_to_add.append(indicator_metadata)

        excitation_wavelength_nm = region_data["excitation_wavelength_nm"].values[0]
        if np.isnan(excitation_wavelength_nm):
            raise ValueError(
                f"Excitation wavelength in nm is missing for indicator '{indicator_label}'. Please provide it in the xlsx file."
            )

        indicator_name = indicator_metadata["name"].lower()
        excitation_source_metadata = next(
            (
                source
                for source in excitation_sources_metadata
                if indicator_name in source["name"]
                and source["excitation_wavelength_in_nm"] == float(excitation_wavelength_nm)
            ),
            None,
        )
        if excitation_source_metadata is None:
            raise ValueError(
                f"Excitation source metadata for excitation wavelength '{excitation_wavelength_nm}' and indicator {indicator_name} not found in '{default_fiber_photometry_metadata_yaml_file_path}'."
                f"Please provide it in the yaml file."
            )
        excitation_sources_to_add.append(excitation_source_metadata)

        row_metadata.update(
            location=region_data["fiber_location"].values[0],
            coordinates=coordinates,
            indicator=indicator_name,
            excitation_source=excitation_source_metadata["name"],
        )
        fiber_photometry_table_rows.append(row_metadata)

    fiber_photometry_series_metadata = []
    for series_name, series_data in session_data.groupby("fiber_photometry_series_name"):
        series_metadata_to_update = next(
            (series for series in series_metadata if series["name"] == series_name),
            None,
        )
        if series_metadata_to_update is None:
            raise ValueError(
                f"Series metadata for '{series_name}' not found in '{default_fiber_photometry_metadata_yaml_file_path}'."
            )

        fiber_photometry_table_region = series_data["fiber_photometry_table_region"].values
        series_metadata_to_update.update(fiber_photometry_table_region=fiber_photometry_table_region)

        if "channel_column_names" in series_metadata_to_update:
            series_metadata_to_update.update(channel_column_names=series_data["doric_csv_column_name"].values)

        elif "stream_names" in series_metadata_to_update:
            series_metadata_to_update.update(stream_names=series_data["doric_stream_name"].values)
        else:
            raise ValueError(
                "Either 'channel_column_names' or 'stream_names' should be present in the series metadata."
            )
        fiber_photometry_series_metadata.append(series_metadata_to_update)

    fiber_photometry_metadata_copy["Ophys"]["FiberPhotometry"].update(
        FiberPhotometryResponseSeries=fiber_photometry_series_metadata,
        Indicators=indicators_to_add,
        ExcitationSources=excitation_sources_to_add,
    )
    fiber_photometry_metadata_copy["Ophys"]["FiberPhotometry"]["FiberPhotometryTable"].update(
        rows=fiber_photometry_table_rows,
    )

    return fiber_photometry_metadata_copy


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
        )
    ]

    futures = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for session_to_nwb_kwargs in session_to_nwb_kwargs_per_session:
            session_to_nwb_kwargs["verbose"] = verbose
            session_to_nwb_kwargs["overwrite"] = overwrite
            nwbfile_name = Path(session_to_nwb_kwargs["nwbfile_path"]).stem
            exception_file_path = (
                dataset_excel_file_path.parent / f"ERROR_{nwbfile_name}.txt"
            )  # Add error file path here
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
):
    """Get the kwargs for session_to_nwb for each session in the dataset.

    Parameters
    ----------
    dataset_excel_file_path : Union[str, Path]
        The path to the directory containing the raw data.
    rat_info_folder_path : Union[str, Path]
        The path to the directory containing the rat info files.

    Returns
    -------
    list[dict[str, Any]]
        A list of dictionaries containing the kwargs for session_to_nwb for each session.
    """

    dataset = pd.read_excel(dataset_excel_file_path)

    dataset_grouped = dataset.groupby(["subject_id", "session_id"])
    for (subject_id, session_id), session_data in dataset_grouped:
        raw_fiber_photometry_file_path = session_data["raw_fiber_photometry_file_path"].values[0]
        raw_fiber_photometry_file_path = Path(raw_fiber_photometry_file_path)
        if not raw_fiber_photometry_file_path.exists():
            raise FileNotFoundError(f"File '{raw_fiber_photometry_file_path}' not found.")

        nwbfile_path = output_folder_path / f"sub-{subject_id}_ses-{session_id}.nwb"
        dlc_file_path = session_data["dlc_file_path"].values[0]
        video_file_path = session_data["video_file_path"].values[0]
        behavior_file_path = session_data["bpod_file_path"].values[0]

        fiber_photometry_metadata = update_default_fiber_photometry_metadata(session_data=session_data)

        try:
            date_obj = datetime.strptime(str(session_id), "%Y%m%d")
            date_str = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            raise ValueError(
                f"Invalid date format in session_id '{session_id}'. Expected format is 'YYYYMMDD' (e.g. '20210528')."
            )

        subject_metadata = get_subject_metadata_from_rat_info_folder(
            folder_path=rat_registry_folder_path,
            subject_id=subject_id,
            date=date_str,
        )

        yield dict(
            raw_fiber_photometry_file_path=raw_fiber_photometry_file_path,
            nwbfile_path=nwbfile_path,
            raw_behavior_file_path=behavior_file_path,
            dlc_file_path=dlc_file_path if not pd.isna(dlc_file_path) else None,
            video_file_path=video_file_path if not pd.isna(video_file_path) else None,
            fiber_photometry_metadata=fiber_photometry_metadata,
            subject_metadata=subject_metadata,
        )


if __name__ == "__main__":

    # Parameters for conversion
    dataset_excel_file_path = Path("all_sessions_table.xlsx")
    output_folder_path = Path("/Users/weian/data/nwbfiles/test")
    rat_registry_folder_path = "/Volumes/T9/Constantinople/Rat_info"

    max_workers = 1
    overwrite = True
    verbose = False

    dataset_to_nwb(
        dataset_excel_file_path=dataset_excel_file_path,
        output_folder_path=output_folder_path,
        rat_info_folder_path=rat_registry_folder_path,
        max_workers=max_workers,
        verbose=verbose,
        overwrite=overwrite,
    )
