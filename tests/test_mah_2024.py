from datetime import datetime

import numpy as np
from dateutil import tz
from pynwb.testing.mock.file import mock_NWBFile
from scipy.io import savemat

from constantinople_lab_to_nwb.mah_2024.interfaces import Mah2024ProcessedBehaviorInterface
from constantinople_lab_to_nwb.mah_2024.mah_2024_convert_all_sessions import (
    _get_date_index_per_session,
    _get_session_date,
)
from constantinople_lab_to_nwb.mah_2024.mah_2024_convert_session import COLUMN_DESCRIPTIONS, COLUMN_NAME_MAPPING


def _write_processed_behavior_file(file_path, dates, num_trials_per_session):
    num_trials = int(np.sum(num_trials_per_session))
    trial_columns = dict(
        trainingstage=np.full(num_trials, 9.0),
        catch=np.zeros(num_trials),
        prob_catch=np.full(num_trials, 0.15),
        reward=np.full(num_trials, 20.0),
        reward_delay=np.full(num_trials, 2.5),
        block=np.ones(num_trials),
        hits=np.ones(num_trials),
        vios=np.zeros(num_trials),
        optout=np.zeros(num_trials),
        wait_time=np.full(num_trials, 2.5),
    )
    processed_behavior = dict(
        date=np.array(dates, dtype=object),
        ntrials=np.array(num_trials_per_session, dtype=float),
        **trial_columns,
    )
    savemat(file_path, dict(A=processed_behavior))


def _write_bpod_file(file_path, date, num_trials):
    savemat(file_path, dict(SessionData=dict(nTrials=num_trials, Info=dict(SessionDate=date))))


def test_session_date_is_parsed_as_year_month_day():
    assert _get_session_date(session_id="RWTautowait2-20221004-095612") == "2022-10-04"
    assert _get_session_date(session_id="RWTautowait2-20221231-095612-x") == "2022-12-31"


def test_raw_file_matching_an_already_matched_session_is_skipped(tmp_path):
    a_struct_file_path = tmp_path / "ratTrial_L011.mat"
    _write_processed_behavior_file(
        file_path=a_struct_file_path, dates=["03-Oct-2022", "04-Oct-2022"], num_trials_per_session=[3, 5]
    )
    first_session_file_path = tmp_path / "L011_RWTautowait2_20221003_094730.mat"
    second_session_file_path = tmp_path / "L011_RWTautowait2_20221004_095612.mat"
    copy_of_second_session_file_path = tmp_path / "L011_RWTautowait2_20221004_095612_x.mat"
    not_in_processed_file_path = tmp_path / "L011_RWTautowait2_20221005_095612.mat"
    _write_bpod_file(file_path=first_session_file_path, date="03-Oct-2022", num_trials=3)
    _write_bpod_file(file_path=second_session_file_path, date="04-Oct-2022", num_trials=5)
    _write_bpod_file(file_path=copy_of_second_session_file_path, date="04-Oct-2022", num_trials=5)
    _write_bpod_file(file_path=not_in_processed_file_path, date="05-Oct-2022", num_trials=7)

    date_index_per_session = _get_date_index_per_session(
        bpod_file_paths=[
            copy_of_second_session_file_path,
            not_in_processed_file_path,
            second_session_file_path,
            first_session_file_path,
        ],
        a_struct_file_path=a_struct_file_path,
    )

    assert date_index_per_session == {first_session_file_path: 0, second_session_file_path: 1}


def test_catch_probability_is_added_to_processed_trials(tmp_path):
    a_struct_file_path = tmp_path / "ratTrial_L011.mat"
    _write_processed_behavior_file(
        file_path=a_struct_file_path, dates=["03-Oct-2022", "04-Oct-2022"], num_trials_per_session=[3, 5]
    )
    interface = Mah2024ProcessedBehaviorInterface(file_path=a_struct_file_path, date_index=1)
    nwbfile = mock_NWBFile(session_start_time=datetime(2022, 10, 4, tzinfo=tz.gettz("America/New_York")))

    interface.add_to_nwbfile(
        nwbfile=nwbfile,
        metadata=interface.get_metadata(),
        column_name_mapping=COLUMN_NAME_MAPPING,
        column_descriptions=COLUMN_DESCRIPTIONS,
        trial_start_times=np.arange(5, dtype=float).tolist(),
        trial_stop_times=(np.arange(5, dtype=float) + 1.0).tolist(),
    )

    processed_trials = nwbfile.intervals["processed_trials"]
    assert "catch_percentage" in processed_trials.colnames
    np.testing.assert_array_equal(processed_trials["catch_percentage"][:], np.full(5, 0.15))
