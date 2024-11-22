from typing import Any
import torch
import tyro
import copy
import dataclasses
import random
import time

from pandas import DataFrame
import matplotlib.pyplot as plt
import numpy as np

from dataset_generator.core.models import Solution
from dataset_generator.visualizers.plotters import plot_gantt_chart
from gym_simulator.algorithms import algorithm_strategy
from gym_simulator.core.simulators.proxy import InternalProxySimulatorObs
from gym_simulator.environments.static import StaticCloudSimEnvironment


@dataclasses.dataclass
class Args:
    simulator: str
    """path to the simulator JAR file"""
    seed: int = 0
    """random seed"""
    host_count: int = 10
    """number of hosts"""
    vm_count: int = 4
    """number of VMs"""
    workflow_count: int = 10
    """number of workflows"""
    task_limit: int = 20
    """maximum number of tasks"""
    buffer_size: int = 1000
    """size of the workflow scheduler buffer"""
    buffer_timeout: int = 100
    """Timeout of the workflow scheduler buffer"""
    gantt_chart_prefix: str = "tmp/gantt_chart"
    """prefix for the Gantt chart files"""


def main(args: Args):
    random.seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.backends.cudnn.deterministic = True

    env_config = {
        "host_count": args.host_count,
        "vm_count": args.vm_count,
        "workflow_count": args.workflow_count,
        "task_limit": args.task_limit,
        "simulator_mode": "embedded",
        "seed": args.seed,
        "simulator_kwargs": {
            "dataset_args": {
                "task_arrival": "dynamic",
            },
            "simulator_jar_path": args.simulator,
            "scheduler_preset": f"buffer:gym:{args.buffer_size}:{args.buffer_timeout}",
            "verbose": False,
            "remote_debug": False,
        },
    }
    agent_env_config = {
        "host_count": args.host_count,
        "vm_count": args.vm_count,
        "workflow_count": args.workflow_count,
        "task_limit": args.task_limit,
        "simulator_mode": "proxy",
        "seed": args.seed,
        "simulator_kwargs": {"proxy_obs": InternalProxySimulatorObs()},
    }

    algorithms = [
        ("Proposed Model", "rl:gin:1732021759_ppo_gin_makespan_power_est_10_20:model_1064960.pt"),
        ("Round Robin", "round_robin"),
        ("Max-Min", "max_min"),
        ("Min-Min", "min_min"),
        ("Best Fit", "best_fit"),
        ("HEFT", "heft"),
        ("Power Heuristic", "power_saving"),
        ("CP-SAT", "cp_sat"),
    ]

    stats: list[dict[str, Any]] = []
    for name, algorithm in algorithms:
        env = StaticCloudSimEnvironment(env_config=copy.deepcopy(env_config))
        scheduler = algorithm_strategy.get_scheduler(algorithm, env_config=copy.deepcopy(agent_env_config))

        total_time = 0
        (tasks, vms), _ = env.reset(seed=args.seed)
        while True:
            start_time = time.time()
            action = scheduler.schedule(tasks, vms)
            end_time = time.time()
            total_time += end_time - start_time
            (tasks, vms), _, terminated, truncated, info = env.step(action)
            if terminated or truncated:
                break

        solution = info.get("solution")
        power_watt = info.get("total_power_consumption_watt")
        assert solution is not None and isinstance(solution, Solution), "Solution is not available"
        fig, ax = plt.subplots()
        plot_gantt_chart(ax, solution.dataset.workflows, solution.dataset.vms, solution.vm_assignments, label=True)
        fig.set_figwidth(12)
        fig.set_figheight(7)
        fig.tight_layout()
        plt.savefig(f"{args.gantt_chart_prefix}_{algorithm}.png")
        plt.close(fig)

        makespan = max([assignment.end_time for assignment in solution.vm_assignments])
        entry = {
            "Algorithm": name,
            "Makespan": makespan,
            "Time": total_time,
            "IsOptimal": scheduler.is_optimal(),
            "PowerW": power_watt,
            "EnergyJ": power_watt * makespan,
        }
        print(entry)
        stats.append(entry)

    env.close()

    for stat in stats:
        print(f"& {stat["Algorithm"]}& {stat["Makespan"]:.1f} & {stat["EnergyJ"]:.1f} & {stat["Time"]:.1f} \\\\ %")

    # Plotting the comparison
    df = DataFrame(stats).sort_values(by="Makespan", ascending=True).reset_index(drop=True)

    fig, ax1 = plt.subplots(figsize=(14, 7))
    bar_width = 0.25
    index = range(len(df["Algorithm"]))

    # Plotting Makespan
    ax1.bar(index, df["Makespan"], width=bar_width, label="Makespan", color="tab:blue")
    ax1.set_xlabel("Algorithm")
    ax1.set_ylabel("Makespan", color="tab:blue")
    ax1.tick_params(axis="y", labelcolor="tab:blue")
    ax1.set_xticks([i + bar_width / 2 for i in index])
    # Algorithm name should be df["Algorithm"] for non-optimal solutions, and df["Algorithm*"] for optimal solutions
    algorithm_names = [f"{df['Algorithm'][i]}*" if df["IsOptimal"][i] else df["Algorithm"][i] for i in index]
    ax1.set_xticklabels(algorithm_names, rotation=45, ha="right")

    # Adding Energy consumption to the plot
    ax2 = ax1.twinx()
    ax2.bar([i + bar_width for i in index], df["EnergyJ"], width=bar_width, label="Energy (J)", color="tab:green")
    ax2.set_ylabel("Energy (J)", color="tab:green")
    ax2.tick_params(axis="y", labelcolor="tab:green")

    # Creating a secondary y-axis for Time
    ax3 = ax1.twinx()
    ax3.spines["right"].set_position(("axes", 1.2))
    ax3.bar([i + 2 * bar_width for i in index], df["Time"], width=bar_width, label="Time (s)", color="tab:red")
    ax3.set_ylabel("Time (s)", color="tab:red")
    ax3.tick_params(axis="y", labelcolor="tab:red")

    fig.legend(loc="upper right", bbox_to_anchor=(1, 1), bbox_transform=ax1.transAxes)
    plt.title("Comparison of Algorithms by Makespan, Power and Time")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    args = tyro.cli(Args)
    main(args)
