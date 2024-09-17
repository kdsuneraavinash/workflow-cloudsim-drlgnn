import dataclasses
import json
import tyro

import networkx as nx
import matplotlib.pyplot as plt

from dataset_generator.core.models import Solution
from dataset_generator.visualizers.utils import save_agraph
from dataset_generator.visualizers.plotters import plot_gantt_chart, plot_workflow_graphs, plot_execution_graph
from dataset_generator.visualizers.printers import print_solution


@dataclasses.dataclass
class Args:
    prefix: str = "tmp/viz_solution"
    """file prefix to use (with directory)"""


def main(args: Args):
    dataset_str = input()
    dataset_dict = json.loads(dataset_str)
    solution = Solution.from_json(dataset_dict)

    # Workflow graph
    _, ax = plt.subplots()
    G_w: nx.DiGraph = nx.DiGraph()
    A_w = plot_workflow_graphs(G_w, solution.dataset.workflows)
    save_agraph(A_w, f"{args.prefix}_workflows.png")

    # Solution
    print_solution(solution.dataset.workflows, solution.vm_assignments)

    # Execution graph
    _, ax = plt.subplots()
    G_e: nx.DiGraph = nx.DiGraph()
    A_e = plot_execution_graph(G_e, solution.dataset.workflows, solution.dataset.vms, solution.vm_assignments)
    save_agraph(A_e, f"{args.prefix}_execution.png", dir_lr=True)

    # Gantt chart
    _, ax = plt.subplots()
    plot_gantt_chart(ax, solution.dataset.workflows, solution.dataset.vms, solution.vm_assignments, label=False)
    plt.savefig(f"{args.prefix}_gantt.png")


if __name__ == "__main__":
    args = tyro.cli(Args)
    main(args)
