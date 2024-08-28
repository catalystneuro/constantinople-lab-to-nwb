from datetime import datetime
from pathlib import Path
from typing import List, Union
from warnings import warn

import numpy as np
from ndx_structured_behavior import (
    StateTypesTable,
    StatesTable,
    EventTypesTable,
    EventsTable,
    TaskRecording,
    TrialsTable,
    Task,
    ActionTypesTable,
    ActionsTable,
    TaskArgumentsTable,
)
from neuroconv import BaseDataInterface
from neuroconv.utils import DeepDict

from ndx_structured_behavior.utils import loadmat
from pynwb import NWBFile


class Mah2024BpodInterface(BaseDataInterface):
    """Behavior interface for mah_2024 conversion"""

    def __init__(
            self,
            file_path: Union[str, Path],
            default_struct_name: str = "SessionData",
            verbose: bool = True,
    ):
        """
        Interface for converting raw Bpod data to NWB.

        Parameters
        ----------
        file_path: FilePathType
            Path to the raw Bpod data file (.mat).
        default_struct_name: str
            The name of the struct in the .mat file that contains the Bpod data, default is 'SessionData'.
        verbose: bool
            Controls verbosity.
        """
        self.default_struct_name = default_struct_name
        self.file_path = file_path
        self._bpod_struct = self._read_file()
        super().__init__(file_path=file_path, verbose=verbose)

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()

        default_device_metadata = dict(
            name="bpod",
            manufacturer="Sanworks",
        )

        if "Info" in self._bpod_struct:
            info_dict = self._bpod_struct["Info"]
            date_string = info_dict["SessionDate"] + info_dict["SessionStartTime_UTC"]
            session_start_time = datetime.strptime(date_string, '%d-%b-%Y%H:%M:%S')
            metadata["NWBFile"].update(session_start_time=session_start_time)

            # Device info
            state_machine_version = info_dict["StateMachineVersion"]
            if state_machine_version:
                description = "State Machine Version: " + state_machine_version
                default_device_metadata.update(
                    description=description,
                )

        metadata["Behavior"] = dict(
            Device=default_device_metadata,
            StateTypesTable=dict(description="Contains the name of the states in the task."),
            StatesTable=dict(description="Contains the start and end times of each state in the task."),
            ActionsTable=dict(description="Contains the onset times of the task output actions."),
            ActionTypesTable=dict(description="Contains the name of the task output actions."),
            EventTypesTable=dict(description="Contains the name of the events in the task."),
            EventsTable=dict(description="Contains the onset times of events in the task."),
            TrialsTable=dict(description="Contains the start and end times of each trial in the task."),
        )

        task_arguments = dict(
            RewardAmount=dict(
                name="reward_volume_ul",
                description="The volume of reward in microliters.",
                expression_type="integer",
                output_type="numeric",
            ),
            NoseInCenter=dict(
                name="nose_in_center",
                description="The time in seconds when the animal is required to maintain center port to initiate the trial (uniformly drawn from 0.8 - 1.2 seconds).",
                expression_type="double",
                output_type="numeric",
            ),
            NICincrement=dict(
                name="time_increment_for_nose_in_center",
                description="The time increment for nose in center in seconds.",
                expression_type="double",
                output_type="numeric",
            ),
            TargetNIC=dict(
                name="target_duration_for_nose_in_center",
                description="The goal for how long the animal must poke center in seconds.",
                expression_type="double",
                output_type="numeric",
            ),
            TrainingStage=dict(
                name="training_stage",
                description="The stage of the training.",
                expression_type="integer",
                output_type="numeric",
            ),
            DelayToReward=dict(
                name="delay_to_reward",
                description="The delay in seconds from the end of NoseInCenter to the reward port. Drawn from exponential distribution with mean = 2.5 seconds.",
                expression_type="double",
                output_type="numeric",
            ),
            TargetDelayToReward=dict(
                name="target_delay_to_reward",
                description="The target delay in seconds from the end of NoseInCenter to the reward port.",
                expression_type="double",
                output_type="numeric",
            ),
            DTRincrement=dict(
                name="time_increment_for_delay_to_reward",
                description="The time increment during monotonic increase of reward delay.",
                expression_type="double",
                output_type="numeric",
            ),
            ViolationTO=dict(
                name="violation_time_out",
                description="The time-out if nose is center is not satisfied in seconds.",
                expression_type="double",
                output_type="numeric",
            ),
            Block=dict(
                name="block_type",
                description="The block type (High, Low or Test).",
                expression_type="string",
                output_type="string",
            ),
            BlockLengthTest=dict(
                name="num_trials_in_test_blocks",
                description="The number of trials in test blocks.",
                expression_type="integer",
                output_type="numeric",
            ),
            BlockLengthAd=dict(
                name="num_trials_in_adaptation_blocks",
                description="The number of trials in adaptation blocks.",
                expression_type="integer",
                output_type="numeric",
            ),
            PunishSound=dict(
                name="punish_sound_enabled",
                description="Whether to play a white noise pulse on error.",
                expression_type="boolean",
                output_type="boolean",
            ),
            ProbCatch=dict(
                name="catch_percentage",
                description="The percentage of catch trials.",
                expression_type="double",
                output_type="numeric",
            ),
            IsCatch=dict(
                name="is_catch",
                description="Whether the trial is a catch trial.",
                expression_type="boolean",
                output_type="boolean",
            ),
            CTrial=dict(
                name="current_trial",
                description="The current trial number.",
                expression_type="integer",
                output_type="numeric",
            ),
            VolumeDelivered=dict(
                name="cumulative_reward_volume_ul",
                description="The cumulative volume received during session in microliters.",
                expression_type="double",
                output_type="numeric",
            ),
            WarmUp=dict(
                name="is_warm_up",
                description="Whether the trial is warm-up.",
                expression_type="boolean",
                output_type="boolean",
            ),
            OverrideNIC=dict(
                name="override_nose_in_center",
                description="Whether the required time for maintaining center port is overridden.",
                expression_type="boolean",
                output_type="boolean",
            ),
            TrialsInStage=dict(
                name="trials_in_stage",
                description="The cumulative number of trials in the stages.",
                expression_type="integer",
                output_type="numeric",
            ),
            MinimumVol=dict(
                name="min_reward_volume_ul",
                description="The minimum volume of reward in microliters. (The minimum volume is 4 ul for females and 6 ul for males.)",
                expression_type="double",
                output_type="numeric",
            ),
            AutoProbCatch=dict(
                name="auto_change_catch_probability",
                description="Whether to change the probability automatically after a certain number of trials.",
                expression_type="boolean",
                output_type="boolean",
            ),
            PrevWasViol=dict(
                name="previous_was_violation",
                description="Whether the previous trial was a violation.",
                expression_type="boolean",
                output_type="boolean",
            ),
            changed=dict(
                name="changed",
                description="Whether a block transition occurred for the trial.",
                expression_type="boolean",
                output_type="boolean",
            ),
            CPCue=dict(
                name="center_port_cue",
                description="Task parameter.",  # no description in the original code
                expression_type="boolean",
                output_type="boolean",
            ),
            CycleBlocks=dict(
                name="cycle_blocks",
                description="Task parameter.",  # no description in the original code
                expression_type="boolean",
                output_type="boolean",
            ),
            HitFrac=dict(
                name="hit_percentage",
                description="The percentage of hit trials.",
                expression_type="double",
                output_type="numeric",
            ),
            hits=dict(
                name="hits",
                description="The number of trials where reward was delivered.",
                expression_type="integer",
                output_type="numeric",
            ),
            TrialsStage2=dict(
                name="num_trials_in_stage_2",
                description="Determines how many trials occur in stage 2 before transition.",
                expression_type="integer",
                output_type="numeric",
            ),
            TrialsStage3=dict(
                name="num_trials_in_stage_3",
                description="Determines how many trials occur in stage 3 before transition.",
                expression_type="integer",
                output_type="numeric",
            ),
            TrialsStage4=dict(
                name="num_trials_in_stage_4",
                description="Determines how many trials occur in stage 4 before transition.",
                expression_type="integer",
                output_type="numeric",
            ),
            TrialsStage5=dict(
                name="num_trials_in_stage_5",
                description="Determines how many trials occur in stage 5 before transition.",
                expression_type="integer",
                output_type="numeric",
            ),
            TrialsStage6=dict(
                name="num_trials_in_stage_6",
                description="Determines how many trials occur in stage 6 before transition.",
                expression_type="integer",
                output_type="numeric",
            ),
            TrialsStage8=dict(
                name="num_trials_in_stage_8",
                description="Determines how many trials occur in stage 8 before transition.",
                expression_type="integer",
                output_type="numeric",
            ),
        )

        metadata["Behavior"]["TaskArgumentsTable"] = task_arguments

        return metadata

    def _read_file(self) -> dict:
        mat_file = loadmat(self.file_path)
        if self.default_struct_name not in mat_file:
            raise ValueError(f"The '{self.default_struct_name}' struct is not in '{self.file_path}'.")
        return mat_file[self.default_struct_name]

    def get_trial_times(self) -> (List[float], List[float]):
        return self._bpod_struct["TrialStartTimestamp"], self._bpod_struct["TrialEndTimestamp"]

    def create_states_table(self, metadata: dict, trial_start_times: List[float]) -> tuple[StateTypesTable, StatesTable]:
        state_types_metadata = metadata["Behavior"]["StateTypesTable"]
        states_table_metadata = metadata["Behavior"]["StatesTable"]

        state_types_description = state_types_metadata.pop("description")
        state_types = StateTypesTable(description=state_types_description)
        states_table = StatesTable(description=states_table_metadata["description"], state_types_table=state_types)

        trials_data = self._bpod_struct["RawEvents"]["Trial"]
        for state_name in trials_data[0]["States"]:
            state_types.add_row(
                state_name=state_types_metadata[state_name]["name"],
                check_ragged=False,
            )

        for trial_states_and_events, trial_start_time in zip(trials_data, trial_start_times):
            states = trial_states_and_events["States"]
            for state_name in states:
                state_relative_start_time = states[state_name][0]
                state_relative_stop_time = states[state_name][1]
                if np.isnan(state_relative_start_time) and np.isnan(state_relative_stop_time):
                    continue
                states_table.add_row(
                    state_type=state_types.state_name[:].index(state_types_metadata[state_name]["name"]),
                    start_time=trial_start_time + state_relative_start_time,
                    stop_time=trial_start_time + state_relative_stop_time,
                    check_ragged=False,
                )

        return state_types, states_table

    def create_actions_table(self, metadata: dict, trial_start_times: List[float]) -> tuple[ActionTypesTable, ActionsTable]:
        action_types_metadata = metadata["Behavior"]["ActionTypesTable"]
        actions_table_metadata = metadata["Behavior"]["ActionsTable"]

        action_types_description = action_types_metadata.pop("description")
        action_types = ActionTypesTable(description=action_types_description)
        actions_table = ActionsTable(description=actions_table_metadata["description"], action_types_table=action_types)

        action_types.add_row(
            action_name=action_types_metadata["SoundOutput"]["name"],
            check_ragged=False,
        )

        trials_data = self._bpod_struct["RawEvents"]["Trial"]
        for trial_states_and_events, trial_start_time in zip(trials_data, trial_start_times):
            events = trial_states_and_events["Events"]

            sound_events = [event_name for event_name in events if "AudioPlayer" in event_name or "WavePlayer" in event_name]
            if not len(sound_events):
                continue

            for sound_event in sound_events:
                timestamps = events[sound_event]
                if isinstance(timestamps, float):
                    timestamps = [timestamps]
                for timestamp in timestamps:
                    actions_table.add_row(
                        action_type=0,
                        timestamp=trial_start_time + timestamp,
                        value="On",
                        check_ragged=False,
                    )

        return action_types, actions_table

    def create_events_table(self, metadata: dict, trial_start_times: List[float]) -> tuple[EventTypesTable, EventsTable]:
        event_types_metadata = metadata["Behavior"]["EventTypesTable"]
        events_table_metadata = metadata["Behavior"]["EventsTable"]

        event_types_description = event_types_metadata.pop("description")
        event_types = EventTypesTable(description=event_types_description)
        events_table = EventsTable(description=events_table_metadata["description"], event_types_table=event_types)

        for event_name in event_types_metadata.keys():
            event_type = event_types_metadata[event_name]["name"]
            # avoid adding duplicate event types
            if event_type in event_types[:].event_name.values.tolist():
                continue
            event_types.add_row(
                event_name=event_type,
                check_ragged=False,
            )

        event_value_mapping = dict(
            Port1In="In",
            Port1Out="Out",
            Port2In="In",
            Port2Out="Out",
            Port3In="In",
            Port3Out="Out",
            Tup="Expired",
            GlobalTimer1_Start="On",
            GlobalTimer1_End="Off",
        )

        trials_data = self._bpod_struct["RawEvents"]["Trial"]
        for trial_states_and_events, trial_start_time in zip(trials_data, trial_start_times):
            events = trial_states_and_events["Events"]
            for event_name in events:
                if event_name not in event_value_mapping:
                    continue
                relative_timestamps = events[event_name]
                if isinstance(relative_timestamps, float):
                    relative_timestamps = [relative_timestamps]
                event_type = event_types.event_name[:].index(event_types_metadata[event_name]["name"])
                for timestamp in relative_timestamps:
                    events_table.add_row(
                        event_type=event_type,
                        timestamp=trial_start_time + timestamp,
                        value=event_value_mapping[event_name],
                        check_ragged=False,
                    )

        return event_types, events_table

    def create_task_arguments_table(self, metadata: dict) -> TaskArgumentsTable:
        task_arguments_metadata = metadata["Behavior"]["TaskArgumentsTable"]
        task_settings = self._bpod_struct["SettingsFile"]["GUI"]

        task_arguments = TaskArgumentsTable(description="Task arguments for the task.")

        for task_argument_name in task_settings.keys():
            if task_argument_name not in task_arguments_metadata:
                warn(f"Task argument '{task_argument_name}' not in metadata. Skipping.")
                continue

            expression_type = task_arguments_metadata[task_argument_name]["expression_type"]
            task_argument_value = task_settings[task_argument_name]
            if expression_type == "boolean":
                task_argument_value = bool(task_argument_value)
            if task_argument_name == "Block":
                block_name_mapping = {1: "Test", 2: "High", 3: "Low"}
                task_argument_value = block_name_mapping[task_argument_value]

            task_arguments.add_row(
                argument_name=task_arguments_metadata[task_argument_name]["name"],
                argument_description=task_arguments_metadata[task_argument_name]["description"],
                expression=str(task_argument_value),
                expression_type=expression_type,
                output_type=task_arguments_metadata[task_argument_name]["output_type"],
            )

        return task_arguments

    def add_task(self, nwbfile: NWBFile, metadata: dict) -> None:
        trial_start_times, trial_stop_times = self.get_trial_times()

        state_types_table, states_table = self.create_states_table(
            metadata=metadata,
            trial_start_times=trial_start_times,
        )
        action_types_table, actions_table = self.create_actions_table(
            metadata=metadata,
            trial_start_times=trial_start_times,
        )
        event_types_table, events_table = self.create_events_table(
            metadata=metadata,
            trial_start_times=trial_start_times,
        )

        task_arguments_table = self.create_task_arguments_table(metadata=metadata)

        task = Task(
            event_types=event_types_table,
            state_types=state_types_table,
            action_types=action_types_table,
            task_arguments=task_arguments_table,
        )
        # Add the task
        nwbfile.add_lab_meta_data(task)

        # To add these tables to acquisitions in an NWBFile, they are stored within TaskRecording.
        recording = TaskRecording(events=events_table, states=states_table, actions=actions_table)
        nwbfile.add_acquisition(recording)

    def add_trials(self, nwbfile: NWBFile, metadata: dict) -> None:
        trial_start_times, trial_stop_times = self.get_trial_times()

        if "task_recording" not in nwbfile.acquisition:
            self.add_task(nwbfile=nwbfile, metadata=metadata)
        task_recording = nwbfile.acquisition["task_recording"]

        states_table = task_recording.states
        events_table = task_recording.events
        actions_table = task_recording.actions

        trials_metadata = metadata["Behavior"]["TrialsTable"]
        trials = TrialsTable(
            description=trials_metadata["description"],
            states_table=states_table,
            events_table=events_table,
            actions_table=actions_table,
        )
        trial_stop_times = trial_start_times[1:] + [np.nan]
        for start, stop in zip(trial_start_times, trial_stop_times):
            states_table_df = states_table[:]
            states_index_mask = (states_table_df["start_time"] >= start) & (states_table_df["stop_time"] < stop)
            states_index_ranges = states_table_df[states_index_mask].index

            events_table_df = events_table[:]
            events_index_mask = (events_table_df["timestamp"] >= start) & (events_table_df["timestamp"] < stop)
            events_index_ranges = events_table_df[events_index_mask].index

            actions_table_df = actions_table[:]
            actions_index_mask = (actions_table_df["timestamp"] >= start) & (actions_table_df["timestamp"] < stop)
            actions_index_ranges = actions_table_df[actions_index_mask].index
            trials.add_trial(
                start_time=start,
                stop_time=stop,
                states=states_index_ranges.tolist(),
                events=events_index_ranges.tolist(),
                actions=actions_index_ranges.tolist(),
            )

        nwbfile.trials = trials

    def add_task_arguments_to_trials(
            self,
            nwbfile: NWBFile,
            metadata: dict,
            arguments_to_exclude: List[str] = None,
    ) -> None:
        if arguments_to_exclude is None:
            arguments_to_exclude = []
        trials = nwbfile.trials
        trials_settings = self._bpod_struct["TrialSettings"]

        task_arguments_metadata = metadata["Behavior"]["TaskArgumentsTable"]

        task_arguments_for_this_session = set()
        for trial_ind in range(len(trials)):
            task_arguments_for_this_session.update(trials_settings[trial_ind]["GUI"].keys())

        for task_argument_name in task_arguments_for_this_session:
            if task_argument_name in arguments_to_exclude:
                continue
            task_argument_values = np.array([trial_settings["GUI"][task_argument_name] for trial_settings in trials_settings])
            task_argument_type = task_arguments_metadata[task_argument_name]["expression_type"]
            if task_argument_type == "boolean":
                task_argument_values = task_argument_values.astype(bool)
            elif task_argument_name == "Block":
                block_name_mapping = {1: "Test", 2: "High", 3: "Low"}
                task_argument_values = np.array([block_name_mapping[block] for block in task_argument_values])

            trials.add_column(
                name=task_arguments_metadata[task_argument_name]["name"],
                description=task_arguments_metadata[task_argument_name]["description"],
                data=task_argument_values,
            )

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, task_arguments_to_exclude: list = None) -> None:
        if "Device" in metadata["Behavior"]:
            nwbfile.create_device(**metadata["Behavior"]["Device"])

        self.add_task(nwbfile=nwbfile, metadata=metadata)
        self.add_trials(nwbfile=nwbfile, metadata=metadata)
        self.add_task_arguments_to_trials(
            nwbfile=nwbfile,
            metadata=metadata,
            arguments_to_exclude=task_arguments_to_exclude,
        )
