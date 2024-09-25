from dataset_generator.core.models import Dataset, VmAssignment
from dataset_generator.solvers.cp_sat_solver import solve_cp_sat
from dataset_generator.solvers.round_robin_solver import solve_round_robin


def solve(method: str, dataset: Dataset) -> list[VmAssignment]:
    if method == "sat":
        return solve_cp_sat(workflows=dataset.workflows, vms=dataset.vms)
    elif method == "round_robin":
        return solve_round_robin(workflows=dataset.workflows, vms=dataset.vms)

    raise ValueError(f"Unknown method: {method}")