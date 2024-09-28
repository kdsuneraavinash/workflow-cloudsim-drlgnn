import tyro
import copy
import dataclasses
import random

import matplotlib.pyplot as plt
import numpy as np

from dataset_generator.core.models import Solution
from dataset_generator.visualizers.plotters import plot_gantt_chart
from gym_simulator.algorithms import algorithm_strategy
from gym_simulator.environments.static import StaticCloudSimEnvironment


@dataclasses.dataclass
class Args:
    simulator: str
    """path to the simulator JAR file"""
    host_count: int = 10
    """number of hosts"""
    vm_count: int = 10
    """number of VMs"""
    workflow_count: int = 5
    """number of workflows"""
    task_limit: int = 5
    """maximum number of tasks"""
    gantt_chart_prefix: str = "tmp/gantt_chart"
    """prefix for the Gantt chart files"""


def main(args: Args):
    env_config = {
        "host_count": args.host_count,
        "vm_count": args.vm_count,
        "workflow_count": args.workflow_count,
        "task_limit": args.task_limit,
        "simulator_mode": "embedded",
        "simulator_kwargs": {
            "simulator_jar_path": args.simulator,
            "verbose": False,
            "remote_debug": False,
        },
    }
    algorithms = [
        "round_robin",
        "max_min",
        "min_min",
        "best_fit",
        "fjssp_fifo_spt",
        "fjssp_fifo_eet",
        "fjssp_mopnr_spt",
        "fjssp_mopnr_eet",
        "fjssp_lwkr_spt",
        "fjssp_lwkr_eet",
        "fjssp_mwkr_spt",
        "fjssp_mwkr_eet",
        "cp_sat",
    ]

    for algorithm in algorithms:
        random.seed(0)
        np.random.seed(0)

        env = StaticCloudSimEnvironment(env_config=copy.deepcopy(env_config))
        scheduler = algorithm_strategy.get_scheduler(algorithm)

        (tasks, vms), _ = env.reset()
        action = scheduler.schedule(tasks, vms)
        _, reward, terminated, truncated, info = env.step(action)
        assert terminated or truncated, "Static environment should terminate after one step"

        solution = info.get("solution")
        assert solution is not None and isinstance(solution, Solution), "Solution is not available"
        fig, ax = plt.subplots()
        plot_gantt_chart(ax, solution.dataset.workflows, solution.dataset.vms, solution.vm_assignments, label=True)
        fig.set_figwidth(12)
        fig.set_figheight(8)
        plt.savefig(f"{args.gantt_chart_prefix}_{algorithm}.png")

        makespan = max([assignment.end_time for assignment in solution.vm_assignments])
        print(f"Algorithm: {algorithm}, Reward: {reward}, Makespan: {makespan}")

    env.close()


if __name__ == "__main__":
    args = tyro.cli(Args)
    main(args)
