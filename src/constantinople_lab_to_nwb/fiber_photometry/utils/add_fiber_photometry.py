from typing import Literal

import numpy as np
from ndx_fiber_photometry import FiberPhotometryTable, FiberPhotometry, FiberPhotometryResponseSeries
from neuroconv.tools import get_module
from neuroconv.tools.fiber_photometry import add_fiber_photometry_device
from pynwb import NWBFile


def add_fiber_photometry_devices(nwbfile: NWBFile, metadata: dict):
    fiber_photometry_metadata = metadata["Ophys"]["FiberPhotometry"]
    # Add Devices
    device_types = [
        "OpticalFiber",
        "ExcitationSource",
        "Photodetector",
        "BandOpticalFilter",
        "EdgeOpticalFilter",
        "DichroicMirror",
        "Indicator",
    ]
    for device_type in device_types:
        devices_metadata = fiber_photometry_metadata.get(device_type + "s", [])
        for device_metadata in devices_metadata:
            add_fiber_photometry_device(
                nwbfile=nwbfile,
                device_metadata=device_metadata,
                device_type=device_type,
            )


def add_fiber_photometry_table(nwbfile: NWBFile, metadata: dict):
    fiber_photometry_metadata = metadata["Ophys"]["FiberPhotometry"]
    fiber_photometry_table_metadata = fiber_photometry_metadata["FiberPhotometryTable"]

    if "FiberPhotometry" in nwbfile.lab_meta_data:
        return

    fiber_photometry_table = FiberPhotometryTable(
        name=fiber_photometry_table_metadata["name"],
        description=fiber_photometry_table_metadata["description"],
    )
    # fiber_photometry_table.add_column(
    #     name="additional_column_name",
    #     description="additional_column_description",
    # )

    fiber_photometry_lab_meta_data = FiberPhotometry(
        name="FiberPhotometry",
        fiber_photometry_table=fiber_photometry_table,
    )
    nwbfile.add_lab_meta_data(fiber_photometry_lab_meta_data)


def add_fiber_photometry_response_series(
    traces: np.ndarray,
    timestamps: np.ndarray,
    nwbfile: NWBFile,
    metadata: dict,
    fiber_photometry_series_name: str,
    parent_container: Literal["acquisition", "processing/ophys"] = "acquisition",
):

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

    if traces.shape[1] != len(trace_metadata["fiber_photometry_table_region"]):
        raise ValueError(
            f"Number of channels ({traces.shape[1]}) should be equal to the number of rows referenced in the fiber photometry table ({len(trace_metadata['fiber_photometry_table_region'])})."
        )

    fiber_photometry_table_region = fiber_photometry_table.create_fiber_photometry_table_region(
        description=trace_metadata["fiber_photometry_table_region_description"],
        region=trace_metadata["fiber_photometry_table_region"],
    )

    if traces.shape[0] != len(timestamps):
        raise ValueError(f"Length of traces ({len(traces)}) and timestamps ({len(timestamps)}) should be equal.")

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