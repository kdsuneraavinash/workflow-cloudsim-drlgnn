from typing import SupportsFloat, Any

import numpy as np
import gymnasium as gym

from scheduler.config.settings import MAX_OBS_SIZE
from scheduler.rl_model.agents.gin_e_agent.mapper import GinEAgentMapper
from scheduler.rl_model.core.env.action import EnvAction
from scheduler.rl_model.core.env.observation import EnvObservation
from scheduler.rl_model.core.utils.helpers import energy_consumption_per_mi


class GinEAgentWrapper(gym.Wrapper):
    observation_space = gym.spaces.Box(low=0, high=np.inf, shape=(MAX_OBS_SIZE,), dtype=np.float32)
    action_space = gym.spaces.Discrete(MAX_OBS_SIZE)

    prev_obs: EnvObservation
    static_obs: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None

    def __init__(self, env: gym.Env[EnvObservation, EnvAction]):
        super().__init__(env)
        self.mapper = GinEAgentMapper(MAX_OBS_SIZE)

    # Reset
    # ------------------------------------------------------------------------------------------------------------------

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[np.ndarray, dict[str, Any]]:
        obs, info = super().reset(seed=seed, options=options)
        assert isinstance(obs, EnvObservation)
        self.static_obs = None  # Invalidate static obs cache
        mapped_obs = self.map_observation(obs)

        self.prev_obs = obs
        return mapped_obs, info

    # Step
    # ------------------------------------------------------------------------------------------------------------------

    def step(self, action: int) -> tuple[np.ndarray, SupportsFloat, bool, bool, dict[str, Any]]:
        mapped_action = self.map_action(action)
        obs, _, terminated, truncated, info = super().step(mapped_action)
        assert isinstance(obs, EnvObservation)
        mapped_obs = self.map_observation(obs)

        makespan_reward = -(obs.makespan() - self.prev_obs.makespan()) / obs.makespan()
        energy_reward = -(obs.energy_consumption() - self.prev_obs.energy_consumption()) / obs.energy_consumption()
        reward = makespan_reward + energy_reward

        self.prev_obs = obs
        return mapped_obs, reward, terminated, truncated, info

    # Mappings
    # ------------------------------------------------------------------------------------------------------------------

    def map_action(self, action: int) -> EnvAction:
        vm_count = len(self.prev_obs.vm_observations)
        return EnvAction(task_id=int(action // vm_count), vm_id=int(action % vm_count))

    def map_observation(self, observation: EnvObservation) -> np.ndarray:
        num_tasks = len(observation.task_observations)

        # Task/VM observations
        task_state_scheduled = [task.assigned_vm_id is not None for task in observation.task_observations]
        task_state_ready = [task.is_ready for task in observation.task_observations]
        vm_completion_time = [vm.completion_time for vm in observation.vm_observations]

        # Static observations (costs and compatibilities)
        (task_vm_compatibility_arr, task_vm_time_cost_arr, task_vm_energy_cost_arr) = self.get_static_obs(observation)

        # Task-Task observations
        adj_arr = np.zeros((num_tasks, num_tasks))
        for task_id, child_id in observation.task_dependencies:
            adj_arr[task_id, child_id] = 1

        # Calculate completion times iteratively (task dependencies)
        task_completion_time_arr = observation.task_completion_time()
        assert task_completion_time_arr is not None

        mapped_obs = self.mapper.map(
            task_state_scheduled=np.array(task_state_scheduled),
            task_state_ready=np.array(task_state_ready),
            task_completion_time=task_completion_time_arr,
            vm_completion_time=np.array(vm_completion_time),
            task_vm_compatibility=task_vm_compatibility_arr,
            task_vm_time_cost=task_vm_time_cost_arr,
            task_vm_energy_cost=task_vm_energy_cost_arr,
            adj=adj_arr,
        )

        return mapped_obs

    # Cached Static Obs
    # ------------------------------------------------------------------------------------------------------------------

    def get_static_obs(self, observation: EnvObservation):
        if self.static_obs is not None:
            return self.static_obs

        num_tasks = len(observation.task_observations)
        num_vms = len(observation.vm_observations)

        # Task-VM observations
        task_vm_compatibility = np.zeros((num_tasks, num_vms))
        task_vm_time_cost = [[1e8 for _ in range(num_vms)] for _ in range(num_tasks)]
        task_vm_energy_cost = [[1e8 for _ in range(num_vms)] for _ in range(num_tasks)]

        # Calculate costs (time and energy) (Cachable)
        for task_id in range(num_tasks):
            compatible_vm_ids = [vid for tid, vid in observation.compatibilities if tid == task_id]
            for vm_id in compatible_vm_ids:
                task_vm_compatibility[task_id, vm_id] = 1
                time_cost = (
                    observation.task_observations[task_id].length / observation.vm_observations[vm_id].cpu_speed_mips
                )
                energy_cost = (
                    energy_consumption_per_mi(observation.vm_observations[vm_id])
                    * observation.task_observations[task_id].length
                )
                task_vm_time_cost[task_id][vm_id] = min(task_vm_time_cost[task_id][vm_id], time_cost)
                task_vm_energy_cost[task_id][vm_id] = min(task_vm_energy_cost[task_id][vm_id], energy_cost)

        # Replace incompatible entries with the average over the VMs
        task_vm_compatibility_arr = np.array(task_vm_compatibility)
        task_vm_time_cost_arr = np.array(task_vm_time_cost)
        task_vm_energy_cost_arr = np.array(task_vm_energy_cost)
        for task_id in range(num_tasks):
            time_cost_sum = (task_vm_time_cost_arr[task_id] * task_vm_compatibility_arr[task_id]).sum()
            energy_cost_sum = (task_vm_energy_cost_arr[task_id] * task_vm_compatibility_arr[task_id]).sum()
            time_cost_avg = time_cost_sum / task_vm_compatibility_arr[task_id].sum()
            energy_cost_avg = energy_cost_sum / task_vm_compatibility_arr[task_id].sum()
            task_vm_time_cost_arr[task_id][task_vm_compatibility_arr[task_id] == 0] = time_cost_avg
            task_vm_energy_cost_arr[task_id][task_vm_compatibility_arr[task_id] == 0] = energy_cost_avg

        self.static_obs = (task_vm_compatibility_arr, task_vm_time_cost_arr, task_vm_energy_cost_arr)
        return self.static_obs
