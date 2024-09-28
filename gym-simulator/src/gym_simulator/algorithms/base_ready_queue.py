from abc import ABC, abstractmethod

from gym_simulator.algorithms.base import BaseScheduler
from gym_simulator.algorithms.types import TaskDto, VmAssignmentDto, VmDto, TaskIdType, VmIdType


class BaseReadyQueueScheduler(BaseScheduler, ABC):
    """
    Base class for scheduling algorithms that use a ready queue.

    Following is the pseudo code for the algorithm:
    1. Initialize the ready queue with start tasks in each workflow.
    2. While the ready queue is not empty:
        - Choose the next task to schedule. (Implement this in the subclass)
        - Schedule the task on a VM. (Implement this in the subclass)
        - Update the ready tasks based on the dependencies.
    """

    task_map: dict[TaskIdType, TaskDto] | None = None
    vm_map: dict[VmIdType, VmDto] | None = None
    est_vm_completion_times: dict[VmIdType, float] | None = None
    est_task_min_start_times: dict[TaskIdType, float] | None = None

    def schedule(self, tasks: list[TaskDto], vms: list[VmDto]) -> list[VmAssignmentDto]:
        assignments: list[VmAssignmentDto] = []

        self.task_map = {self.tid(_task): _task for _task in tasks}
        self.vm_map = {self.vid(_vm): _vm for _vm in vms}

        self.est_vm_completion_times = {self.vid(_vm): 0.0 for _vm in vms}  # Time when the VM will be free
        self.est_task_min_start_times = {self.tid(_task): 0.0 for _task in tasks}  # Min time when the task can start

        ready_tasks = [self.tid(_task) for _task in tasks if _task.id == 0]
        processed_tasks: set[TaskIdType] = set()
        while ready_tasks:
            next_task_id = self.choose_next(ready_tasks)
            ready_tasks.remove(next_task_id)
            processed_tasks.add(next_task_id)

            task = self.get_task(next_task_id)
            selected_vm = self.schedule_next(task, vms)
            assignments.append(VmAssignmentDto(selected_vm.id, task.workflow_id, task.id))

            # Update the completion time of the VM and the min start time of the child tasks
            computation_time = task.length / selected_vm.cpu_speed_mips
            completion_time = (
                max(self.est_vm_completion_times[self.vid(selected_vm)], self.est_task_min_start_times[self.tid(task)])
                + computation_time
            )
            self.est_vm_completion_times[self.vid(selected_vm)] = completion_time
            for child_id in task.child_ids:
                child_task_id_1: TaskIdType = (task.workflow_id, child_id)
                self.est_task_min_start_times[child_task_id_1] = max(
                    completion_time, self.est_task_min_start_times[child_task_id_1]
                )

            # Update the ready tasks
            for child_id in task.child_ids:
                child_task_id_2: TaskIdType = (task.workflow_id, child_id)
                all_parents_processed = all(
                    self.tid(parent) in processed_tasks
                    for parent in tasks
                    if parent.workflow_id == task.workflow_id and child_id in parent.child_ids
                )
                if all_parents_processed and child_task_id_2 not in ready_tasks:
                    ready_tasks.append(child_task_id_2)

        assert len(assignments) == len(tasks), f"Expected {len(tasks)} assignments, got {len(assignments)}"
        self.est_vm_completion_times = None
        self.est_task_min_start_times = None
        return assignments

    @abstractmethod
    def choose_next(self, ready_tasks: list[TaskIdType]) -> TaskIdType:
        """Out of the ready tasks, choose the next task to schedule."""
        raise NotImplementedError

    @abstractmethod
    def schedule_next(self, task: TaskDto, vms: list[VmDto]) -> VmDto:
        """Assign the task to a VM."""
        raise NotImplementedError

    # Helper functions

    def tid(self, task: TaskDto) -> TaskIdType:
        """Return the task ID."""
        return (task.workflow_id, task.id)

    def vid(self, vm: VmDto) -> VmIdType:
        """Return the VM ID."""
        return vm.id

    def get_task(self, task_id: TaskIdType) -> TaskDto:
        """Return the task with the given ID."""
        assert self.task_map is not None, "Task map not initialized yet"
        assert task_id in self.task_map, f"Unknown task id: {task_id}"
        return self.task_map[task_id]

    def get_vm(self, vm_id: VmIdType) -> VmDto:
        """Return the VM with the given ID."""
        assert self.vm_map is not None, "VM map not initialized yet"
        assert vm_id in self.vm_map, f"Unknown VM id: {vm_id}"
        return self.vm_map[vm_id]
