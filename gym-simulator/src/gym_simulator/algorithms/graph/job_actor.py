from dataclasses import dataclass
from typing import Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions.categorical import Categorical

from icecream import ic

from torch_geometric.nn import GCNConv, global_mean_pool
from torch_geometric.utils import dense_to_sparse


class GnnJobActor(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 128, critic_hidden_dim: int = 32):
        super().__init__()
        self.input_dim = input_dim
        self.machine_state = nn.Parameter(torch.Tensor(hidden_dim).uniform_(-1, 1))

        # Define Encoder, Actor, and Critic
        self.encoder = nn.ModuleList(
            [
                GCNConv(input_dim, hidden_dim),
                GCNConv(hidden_dim, hidden_dim),
                GCNConv(hidden_dim, hidden_dim),
            ]
        )
        self.actor = nn.Sequential(
            nn.Linear(hidden_dim * 3, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )
        self.critic = nn.Sequential(
            nn.Linear(hidden_dim, critic_hidden_dim),
            nn.ReLU(),
            nn.Linear(critic_hidden_dim, 1),
        )

    # Encode Graph ------------------------------------------------------------

    def encode_features_to_graph(self, features: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        """
        :param features: (n_jobs, input_dim)
        :param adj: (n_jobs, n_jobs)

        :return mean_pool: (hidden_dim,)
        :return node_embedding: (n_jobs, hidden_dim)
        """
        edge_index, _ = dense_to_sparse(adj)

        h = features.clone()
        for layer in self.encoder:
            h = F.relu(layer(h, edge_index))

        batch = torch.zeros(adj.shape[0], dtype=torch.long)
        mean_pool_batched = global_mean_pool(h, batch)
        mean_pool = mean_pool_batched.squeeze(0)

        node_embedding = h.clone()

        return mean_pool, node_embedding

    # Extract Features --------------------------------------------------------

    def extract_features(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        :param x: (N,)

        :return features: (n_jobs, 2)
        :return adj: (n_jobs, n_jobs)
        :return candidates: (n_jobs,)
        """
        n_jobs = x[0].long().item()
        x = x[2:]

        features_size = n_jobs * self.input_dim
        adj_size = n_jobs * n_jobs
        candidates_size = n_jobs

        return (
            x[:features_size].reshape(n_jobs, self.input_dim),
            x[features_size : features_size + adj_size].reshape(n_jobs, n_jobs),
            x[features_size + adj_size : features_size + adj_size + candidates_size].long(),
        )

    # Get Value ---------------------------------------------------------------

    def get_value(self, x: torch.Tensor) -> torch.Tensor:
        """
        :param x: (batch_size, N)
        :return values: (batch_size,)
        """
        batch_size = x.shape[0]
        values = []

        for batch_index in range(batch_size):
            features, adj, _ = self.extract_features(x[batch_index])
            global_graph_embedding, _ = self.encode_features_to_graph(features, adj)
            values.append(self.critic(global_graph_embedding))

        return torch.stack(values)

    # Get Action and Value ----------------------------------------------------

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
            features, adj, candidates = self.extract_features(x[batch_index])

            # h^t_G: global_graph_embedding (hidden_dim,)
            # h^L_v,t: job_node_embeddings (n_jobs, hidden_dim)
            global_graph_embedding, job_node_embeddings = self.encode_features_to_graph(features, adj)

            # Repeat pooled features and concatenate for actor (n_jobs, hidden_dim * 3)
            global_graph_embedding_rep = global_graph_embedding.unsqueeze(0).expand_as(job_node_embeddings)
            machine_state_rep = self.machine_state[None, :].expand_as(job_node_embeddings)
            concat_feats = torch.cat(
                #    h^L_v,t        || h^t_G                  || u_t
                (job_node_embeddings, global_graph_embedding_rep, machine_state_rep),
                dim=-1,
            )

            # c^o_t,k: Calculate scores and apply mask
            job_action_scores: torch.Tensor = self.actor(concat_feats) * 10  # (n_jobs, 1)
            job_action_scores = job_action_scores.squeeze(-1)  # (n_jobs,)

            # p_j(a^m_t): Softmax for probability distribution
            job_action_probabilities = F.softmax(job_action_scores, dim=0)
            logits = job_action_probabilities.masked_fill(~candidates.bool(), float("-inf"))
            probs = Categorical(logits=logits)
            chosen_action = action[batch_index] if action is not None else probs.sample()
            value = self.critic(global_graph_embedding)

            all_chosen_actions.append(chosen_action)
            all_log_probs.append(probs.log_prob(chosen_action))
            all_entropies.append(probs.entropy())
            all_values.append(value)

        return (
            torch.stack(all_chosen_actions),
            torch.stack(all_log_probs),
            torch.stack(all_entropies),
            torch.stack(all_values),
        )
