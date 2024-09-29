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
        "heft",
    ]

    stats: list[dict[str, float]] = []
    for algorithm in algorithms:
        random.seed(0)
        np.random.seed(0)

        env = StaticCloudSimEnvironment(env_config=copy.deepcopy(env_config))
        scheduler = algorithm_strategy.get_scheduler(algorithm)

        (tasks, vms), _ = env.reset()
        t1 = time.time()
        action = scheduler.schedule(tasks, vms)
        t2 = time.time()
        _, reward, terminated, truncated, info = env.step(action)
        assert terminated or truncated, "Static environment should terminate after one step"

        solution = info.get("solution")
        assert solution is not None and isinstance(solution, Solution), "Solution is not available"
        fig, ax = plt.subplots()
        plot_gantt_chart(ax, solution.dataset.workflows, solution.dataset.vms, solution.vm_assignments, label=True)
        fig.set_figwidth(12)
        fig.set_figheight(8)
        plt.savefig(f"{args.gantt_chart_prefix}_{algorithm}.png")
        plt.close(fig)

        makespan = max([assignment.end_time for assignment in solution.vm_assignments])
        print(f"Algorithm: {algorithm}, Reward: {reward}, Makespan: {makespan}, Time: {t2 - t1:.5f}s")
        stats.append(
            {
                "Algorithm": algorithm,
                "Reward": reward,
                "Makespan": makespan,
                "Time": t2 - t1,
                "IsOptimal": scheduler.is_optimal(),
            }
        )

    env.close()

    # Plotting the comparison
    df = DataFrame(stats).sort_values(by="Makespan", ascending=True).reset_index(drop=True)

    fig, ax1 = plt.subplots(figsize=(14, 7))
    bar_width = 0.35
    index = range(len(df["Algorithm"]))

    # Plotting Makespan
    ax1.bar(index, df["Makespan"], width=bar_width, label="Makespan", alpha=0.6, color="tab:blue")
    ax1.set_xlabel("Algorithm")
    ax1.set_ylabel("Makespan", color="tab:blue")
    ax1.tick_params(axis="y", labelcolor="tab:blue")
    ax1.set_xticks([i + bar_width / 2 for i in index])
    # Algorithm name should be df["Algorithm"] for non-optimal solutions, and df["Algorithm*"] for optimal solutions
    algorithm_names = [f"{df['Algorithm'][i]}*" if df["IsOptimal"][i] else df["Algorithm"][i] for i in index]
    ax1.set_xticklabels(algorithm_names, rotation=45, ha="right")

    # Creating a secondary y-axis for Time (log scale)
    ax2 = ax1.twinx()
    ax2.bar([i + bar_width for i in index], df["Time"], width=bar_width, label="Time (s)", alpha=0.6, color="tab:red")
    ax2.set_ylabel("Time (s)", color="tab:red")
    ax2.set_yscale("log")  # Set log scale for time
    ax2.tick_params(axis="y", labelcolor="tab:red")

    fig.legend(loc="upper right", bbox_to_anchor=(1, 1), bbox_transform=ax1.transAxes)
    plt.title("Comparison of Algorithms by Makespan and Time")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    args = tyro.cli(Args)
    main(args)
