package org.example.ticks;

import lombok.Builder;
import org.example.registries.HostRegistry;

/// Tick listener that updates the utilization of monitored hosts.
public class MonitoredHostsUpdater extends SimulationTickListener {
    private static final String NAME = "MONITORED_HOSTS_UPDATER";

    private final long monitoringUpdateInterval;

    private double nextScheduleAtMs = 0;

    @Builder
    protected MonitoredHostsUpdater(long monitoringUpdateInterval) {
        super(NAME);
        this.monitoringUpdateInterval = monitoringUpdateInterval;
    }

    @Override
    protected void onTick(double time) {
        if (nextScheduleAtMs <= time) {
            nextScheduleAtMs += monitoringUpdateInterval;
            var hostRegistry = HostRegistry.getInstance();
            hostRegistry.updateUtilizationOfHosts(time);
        }
    }
}
