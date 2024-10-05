from ndx_fiber_photometry import FiberPhotometryTable, FiberPhotometry
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
