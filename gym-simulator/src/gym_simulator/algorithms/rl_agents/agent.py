from typing import Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions.categorical import Categorical

from icecream import ic

from gym_simulator.algorithms.rl_agents.gin_network import GinActorNetwork, GinCriticNetwork


class Agent(nn.Module):
    def __init__(self, max_jobs: int, max_machines: int):
        super().__init__()

        self.max_jobs = max_jobs
        self.max_machines = max_machines

        self.actor = GinActorNetwork(max_jobs, max_machines)
        self.critic = GinCriticNetwork(max_jobs, max_machines)

    def get_value(self, x: torch.Tensor) -> torch.Tensor:
        """
        :param x: (batch_size, N)
        :return values: (batch_size,)
        """
        batch_size = x.shape[0]
        values = []

        for batch_index in range(batch_size):
            features = self.decode_observation(x[batch_index])
            values.append(self.critic(*features))

        return torch.stack(values)

    def get_action_and_value(
        self, x: torch.Tensor, action: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        :param x: (batch_size, N)
        :param action: (batch_size,)
        :return chosen_actions: (batch_size,)
        :return log_probs: (batch_size,)
        :return entropies: (batch_size,)
        :return values: (batch_size,)
        """
        batch_size = x.shape[0]
        all_chosen_actions, all_log_probs, all_entropies, all_values = [], [], [], []

        for batch_index in range(batch_size):
            features = self.decode_observation(x[batch_index])

            action_scores: torch.Tensor = self.actor(*features)
            action_scores = action_scores.squeeze(-1)
            action_scores = action_scores.reshape(self.max_jobs, self.max_machines)

            mask = torch.zeros((self.max_jobs, self.max_machines))
            task_state_ready = features[1]
            task_vm_compatibility = features[4]
            mask[task_state_ready == 0, :] = 1
            mask = mask.masked_fill(~task_vm_compatibility.bool(), 1)
            action_scores = action_scores.masked_fill(mask.bool(), -1e8)

            action_scores = action_scores.flatten()
            action_probabilities = F.softmax(action_scores, dim=0)

            probs = Categorical(action_probabilities)
            chosen_action = action[batch_index] if action is not None else probs.sample()
            value = self.critic(*features)

            all_chosen_actions.append(chosen_action)
            all_log_probs.append(probs.log_prob(chosen_action))
            all_entropies.append(probs.entropy())
            all_values.append(value)

        chosen_actions = torch.stack(all_chosen_actions)
        log_probs = torch.stack(all_log_probs)
        entropies = torch.stack(all_entropies)
        values = torch.stack(all_values)

        return chosen_actions, log_probs, entropies, values

    def decode_observation(self, x: torch.Tensor):
        n_jobs = int(x[0].long().item())
        n_machines = int(x[1].long().item())
        x = x[2:]

        task_state_scheduled = x[:n_jobs].long()
        x = x[n_jobs:]

        task_state_ready = x[:n_jobs].long()
        x = x[n_jobs:]

        task_completion_time = x[:n_jobs]
        x = x[n_jobs:]

        vm_completion_time = x[:n_machines]
        x = x[n_machines:]

        task_vm_compatibility = x[: n_jobs * n_machines].reshape(n_jobs, n_machines).long()
        x = x[n_jobs * n_machines :]

        task_vm_time_cost = x[: n_jobs * n_machines].reshape(n_jobs, n_machines)
        x = x[n_jobs * n_machines :]

        task_vm_power_cost = x[: n_jobs * n_machines].reshape(n_jobs, n_machines)
        x = x[n_jobs * n_machines :]

        task_graph_edges = x[: n_jobs * n_jobs].reshape(n_jobs, n_jobs).long()
        x = x[n_jobs * n_jobs :]

        return (
            task_state_scheduled,
            task_state_ready,
            task_completion_time,
            vm_completion_time,
            task_vm_compatibility,
            task_vm_time_cost,
            task_vm_power_cost,
            task_graph_edges,
        )