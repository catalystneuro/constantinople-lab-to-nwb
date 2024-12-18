from warnings import warn

from pynwb import NWBFile
from pynwb.ogen import OptogeneticStimulusSite, OptogeneticSeries
from neuroconv.tools.optogenetics import create_optogenetic_stimulation_timeseries


def add_optogenetics_series(nwbfile: NWBFile, metadata: dict):
    """
    Add optogenetics series to the NWB file.

    Parameters
    ----------
    nwbfile: NWBFile
        The NWB file where the optogenetics series will be added as stimulus.
    metadata: dict
        The metadata to use for adding the optogenetics series. The metadata should be located in the "Stimulus" key,
        with the "OptogeneticSeries" and "OptogeneticStimulusSite" keys containing the metadata for the optogenetic
        series and stimulus site, respectively.

    """

    if nwbfile.trials is None:
        warn("No trials found in the NWB file. Please add trials before adding optogenetics series.")

    trials = nwbfile.trials[:]
    if "is_opto" not in trials.columns:
        return
    # %1 = CPIn, 2=SideOff, 3=Reward/OptOut 4=SON, 5=Delay
    opto_trials = trials[(trials["is_opto"] == True) & (trials["opto_event_type"] == 4)]
    if opto_trials.empty:
        return

    bpod_device = nwbfile.devices.get("bpod")
    if bpod_device is None:
        raise ValueError(
            "No Bpod device found in the NWB file. Please add a Bpod device before adding optogenetics series."
        )

    optogenetics_metadata = metadata["Stimulus"]
    optogenetic_series_metadata = optogenetics_metadata["OptogeneticSeries"]
    optogenetic_stimulus_sites_metadata = optogenetics_metadata["OptogeneticStimulusSite"]
    optogenetic_site_name = optogenetic_series_metadata["site"]

    optogenetic_stimulus_site_metadata = next(
        (
            site_metadata
            for site_metadata in optogenetic_stimulus_sites_metadata
            if site_metadata["name"] == optogenetic_site_name
        ),
        None,
    )
    if optogenetic_stimulus_site_metadata is None:
        raise ValueError(f"Optogenetic stimulus site {optogenetic_site_name} not found in metadata.")

    ogen_stim_site = OptogeneticStimulusSite(
        name=optogenetic_site_name,
        description=optogenetic_stimulus_site_metadata["description"],
        device=bpod_device,
        excitation_lambda=optogenetic_stimulus_site_metadata["excitation_lambda"],
        location=optogenetic_stimulus_site_metadata["location"],
    )

    nwbfile.add_ogen_site(ogen_stim_site)

    timestamps, data = create_optogenetic_stimulation_timeseries(
        stimulation_onset_times=opto_trials["start_time"].values,
        duration=optogenetic_series_metadata["duration"],
        frequency=optogenetic_series_metadata["frequency"],
        pulse_width=optogenetic_series_metadata["pulse_width"],
        power=optogenetic_series_metadata["power"],
    )

    optogenetic_series = OptogeneticSeries(
        name=optogenetic_series_metadata["name"],
        description=optogenetic_series_metadata["description"],
        site=ogen_stim_site,
        data=data,
        timestamps=timestamps,
    )

    nwbfile.add_stimulus(optogenetic_series)
