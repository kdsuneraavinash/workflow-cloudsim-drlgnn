import random

import numpy as np
from dataset_generator.core.models import Dataset
from dataset_generator.core.gen_workflow import generate_workflows
from dataset_generator.core.gen_vm import generate_hosts, generate_vms, allocate_vms


def generate_dataset(
    host_count: int,
    vm_count: int,
    max_memory_gb: int,
    min_cpu_speed_mips: int,
    max_cpu_speed_mips: int,
    workflow_count: int,
    dag_method: str,
    gnp_min_n: int,
    gnp_max_n: int,
    task_length_dist: str,
    min_task_length: int,
    max_task_length: int,
    task_arrival: str,
    arrival_rate: float,
) -> Dataset:
    """
    Generate a dataset.
    """

    hosts = generate_hosts(host_count)
    vms = generate_vms(vm_count, max_memory_gb, min_cpu_speed_mips, max_cpu_speed_mips)
    allocate_vms(vms, hosts)

    workflows = generate_workflows(
        workflow_count=workflow_count,
        dag_method=dag_method,
        gnp_min_n=gnp_min_n,
        gnp_max_n=gnp_max_n,
        task_length_dist=task_length_dist,
        min_task_length=min_task_length,
        max_task_length=max_task_length,
        # Make sure that the problem is feasible
        max_req_memory_mb=max(vm.memory_mb for vm in vms),
        task_arrival=task_arrival,
        arrival_rate=arrival_rate,
    )

    return Dataset(workflows=workflows, vms=vms, hosts=hosts)
