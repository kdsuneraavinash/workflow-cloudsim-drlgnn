from gym_simulator.algorithms.base_ready_queue import BaseReadyQueueScheduler, TaskIdType
from gym_simulator.algorithms.types import TaskDto, VmDto


class BestFitScheduler(BaseReadyQueueScheduler):
    """
    Implementation of the Best Fit scheduling algorithm.

    Best Fit is a simple scheduling algorithm that schedules the tasks so that the VMs are used efficiently.
    The algorithm selects the VM that has the best fit for the task. (RAM)
    """

    def choose_next(self, ready_tasks: list[TaskIdType]) -> TaskIdType:
        """Choose the next task (with no preference)."""
        return ready_tasks[0]

    def schedule_next(self, task: TaskDto, vms: list[VmDto]) -> VmDto:
        """Schedule the task on the VM that has the best fit."""
        assert self.est_vm_completion_times is not None
        assert self.est_task_min_start_times is not None

        best_vm = None
        best_vm_allocation = -float("inf")
        for vm in vms:
            if not self.is_vm_suitable(vm, task):
                continue
            vm_allocation = task.req_memory_mb / vm.memory_mb
            assert 0 <= vm_allocation <= 1, f"Invalid VM allocation: {vm_allocation}"

            # If the current VM has a better fit, update the best VM
            if vm_allocation > best_vm_allocation:
                best_vm = vm
                best_vm_allocation = vm_allocation

            # If the current VM has the same memory, check the estimated completion time
            elif vm_allocation == best_vm_allocation:
                assert best_vm is not None
                if self.est_vm_completion_times[self.vid(vm)] < self.est_vm_completion_times[self.vid(best_vm)]:
                    best_vm = vm
                    best_vm_allocation = vm_allocation

        if best_vm is None:
            raise Exception("No VM found for task")

        return best_vm
