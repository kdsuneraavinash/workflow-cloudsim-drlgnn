package org.example.core.factories;

import lombok.Builder;
import lombok.NonNull;
import org.cloudbus.cloudsim.Vm;
import org.example.core.entities.CloudletSchedulerTimeSharedFixed;
import org.example.core.registries.VmRegistry;
import org.example.dataset.DatasetVm;

import java.util.ArrayList;
import java.util.List;

/// Factory for creating VMs.
@Builder
public class VmFactory {
    private Vm createVm(int brokerId, @NonNull DatasetVm datasetVm) {
        var id = datasetVm.getId();
        var vmSpeed = datasetVm.getCpuSpeedMips(); // MIPS
        var vmCores = 1; // We assume all VMs have 1 core
        var vmRamMb = datasetVm.getMemoryMb(); // MB
        var vmBwMbps = datasetVm.getBandwidthMbps(); // Mbit/s
        var vmSizeMb = datasetVm.getDiskMb(); // MB
        var vmVmm = datasetVm.getVmm();

        var cloudletScheduler = new CloudletSchedulerTimeSharedFixed();
        return new Vm(id, brokerId, vmSpeed, vmCores,
                vmRamMb, vmBwMbps, vmSizeMb, vmVmm, cloudletScheduler);
    }

    /// Create a list of VMs based on the dataset using registered hosts.
    public List<Vm> createVms(int brokerId, @NonNull List<DatasetVm> datasetVms) {
        var vmList = new ArrayList<Vm>();
        for (var datasetVm : datasetVms) {
            var vm = createVm(brokerId, datasetVm);
            vmList.add(vm);
        }

        var vmRegistry = VmRegistry.getInstance();
        vmRegistry.registerNewVms(vmList);
        return vmList;
    }
}
