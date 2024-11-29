import random

import numpy as np

from scheduler.dataset_generator.core.gen_vm import generate_hosts, generate_vms, allocate_vms
from scheduler.dataset_generator.core.models import Dataset
from scheduler.dataset_generator.core.gen_workflow import generate_workflows


def generate_dataset(
    seed: int,
    host_count: int,
    vm_count: int,
    max_memory_gb: int,
    min_cpu_speed_mips: int,
    max_cpu_speed_mips: int,
    max_tasks_per_workflow: int,
    num_tasks: int,
    dag_method: str,
    task_length_dist: str,
    min_task_length: int,
    max_task_length: int,
    task_arrival: str,
    arrival_rate: float,
) -> Dataset:
    """
    Generate a dataset.
    """

    random.seed(seed)
    np.random.seed(seed)

    hosts = generate_hosts(host_count)
    vms = generate_vms(vm_count, max_memory_gb, min_cpu_speed_mips, max_cpu_speed_mips)
    allocate_vms(vms, hosts)

    workflows = generate_workflows(
        max_tasks_per_workflow=max_tasks_per_workflow,
        num_tasks=num_tasks,
        dag_method=dag_method,
        task_length_dist=task_length_dist,
        min_task_length=min_task_length,
        max_task_length=max_task_length,
        # Make sure that the problem is feasible
        max_req_memory_mb=max(vm.memory_mb for vm in vms),
        task_arrival=task_arrival,
        arrival_rate=arrival_rate,
    )

    return Dataset(workflows=workflows, vms=vms, hosts=hosts)
