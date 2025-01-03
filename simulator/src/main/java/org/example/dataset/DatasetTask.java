package org.example.dataset;

import lombok.Data;

import java.util.List;

@Data
public class DatasetTask {
    private final int id;
    private final int workflowId;
    private final int length;
    private final int reqMemoryMb;
    private final List<Integer> childIds;
}
