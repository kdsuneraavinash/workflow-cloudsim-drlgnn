package org.example.models;

import lombok.Data;

@Data
public class DatasetVm {
    private final int id;
    private final int hostId;
    private final int cores;
    private final int cpuSpeedMips;
    private final int memoryMb;
    private final int diskMb;
    private final int bandwidthMbps;
    private final String vmm;
}
