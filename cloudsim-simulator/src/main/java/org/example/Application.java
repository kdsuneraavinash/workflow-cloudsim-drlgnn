package org.example;

import lombok.Setter;
import org.cloudbus.cloudsim.Log;
import org.example.api.scheduler.gym.GymSharedQueue;
import org.example.api.scheduler.gym.mappers.SimpleGymMapper;
import org.example.api.scheduler.gym.types.AgentResult;
import org.example.api.scheduler.gym.types.Action;
import org.example.api.scheduler.gym.types.JsonObservation;
import org.example.api.scheduler.gym.GymWorkflowScheduler;
import org.example.api.executor.LocalWorkflowExecutor;
import org.example.dataset.Dataset;
import org.example.simulation.SimulatedWorld;
import org.example.simulation.SimulatedWorldConfig;
import org.example.simulation.external.Py4JConnector;
import picocli.CommandLine;
import picocli.CommandLine.Command;
import picocli.CommandLine.Option;

import java.io.File;
import java.util.concurrent.Callable;

@Setter
@Command(name = "cloudsim-simulator", mixinStandardHelpOptions = true, version = "1.0",
        description = "Runs a simulation of a workflow scheduling algorithm.",
        usageHelpAutoWidth = true)
public class Application implements Callable<Integer> {
    @Option(names = {"-f", "--file"}, description = "Dataset file")
    private File datasetFile;

    @Option(names = {"-d", "--duration"}, description = "Duration of the simulation", defaultValue = "1000")
    private int duration;

    @Option(names = {"-p", "--port"}, description = "Py4J port", defaultValue = "25333")
    private int py4JPort;

    @Override
    public Integer call() throws Exception {
        System.err.println("Running simulation...");
        Log.disable();

        // Read input file or stdin
        var dataset = datasetFile != null
                ? Dataset.fromFile(datasetFile)
                : Dataset.fromStdin();

        // Configure simulation
        var config = SimulatedWorldConfig.builder()
                .simulationDuration(duration)
                .monitoringUpdateInterval(5)
                .build();

        // Create shared queue
        var gymSharedQueue = new GymSharedQueue<JsonObservation, Action>();

        // Create scheduler, and executor
        // var scheduler = new StaticWorkflowScheduler(new RoundRobinSchedulingAlgorithm());
        var schedulerAlgorithm = new SimpleGymMapper();
        var scheduler = new GymWorkflowScheduler<>(schedulerAlgorithm, gymSharedQueue);
        var executor = new LocalWorkflowExecutor();

        // Thread for Py4J connector
        var gymConnector = new Py4JConnector<>(py4JPort, gymSharedQueue);
        var gymThread = new Thread(gymConnector);
        gymThread.start();

        // Run simulation
        var world = SimulatedWorld.builder().dataset(dataset)
                .scheduler(scheduler).executor(executor)
                .config(config).build();
        var solution = world.runSimulation();
        System.out.println(solution.toJson());

        // Stop Py4J connector
        gymSharedQueue.setObservation(AgentResult.truncated());
        gymThread.join(5000);
        return 0;
    }

    public static void main(String[] args) {
        int exitCode = new CommandLine(new Application()).execute(args);
        System.exit(exitCode);
    }
}
