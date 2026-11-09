package frc.robot.subsystems;

import java.util.ArrayList;
import java.util.List;
import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.networktables.NetworkTableEntry;
import edu.wpi.first.networktables.NetworkTableInstance;
import edu.wpi.first.wpilibj.DriverStation;
import edu.wpi.first.wpilibj.romi.OnBoardIO;
import edu.wpi.first.wpilibj2.command.Command;
import edu.wpi.first.wpilibj2.command.SequentialCommandGroup;
import edu.wpi.first.wpilibj2.command.SubsystemBase;
import frc.robot.commands.BlockMovement;

/** Receives short, bounded Blockly sequences and publishes read-only Romi sensors. */
public class BlockProgramReceiver extends SubsystemBase {
  private final Drivetrain drivetrain;
  private final OnBoardIO onboardIO;
  private final NetworkTable table = NetworkTableInstance.getDefault().getTable("GirlScoutBlocks");
  private final NetworkTable sensors = table.getSubTable("sensors");
  private final NetworkTableEntry sequence = table.getEntry("sequence");
  private final NetworkTableEntry runId = table.getEntry("runId");
  private final NetworkTableEntry stopId = table.getEntry("stopId");
  private final NetworkTableEntry status = table.getEntry("status");
  private long lastRunId;
  private long lastStopId;
  private Command running;
  private long nextSensorPublishMs;

  public BlockProgramReceiver(Drivetrain drivetrain, OnBoardIO onboardIO) {
    this.drivetrain = drivetrain;
    this.onboardIO = onboardIO;
    lastRunId = runId.getInteger(0);
    lastStopId = stopId.getInteger(0);
    status.setString("Ready");
  }

  private void publishSensors() {
    long now = System.currentTimeMillis();
    if (now < nextSensorPublishMs) return;
    nextSensorPublishMs = now + 100; // Throttle NetworkTables writes to ~10 Hz.
    sensors.getEntry("gyroZDeg").setDouble(drivetrain.getGyroAngleZ());
    sensors.getEntry("leftIn").setDouble(drivetrain.getLeftDistanceInch());
    sensors.getEntry("rightIn").setDouble(drivetrain.getRightDistanceInch());
    sensors.getEntry("buttonA").setBoolean(onboardIO.getButtonAPressed());
    sensors.getEntry("buttonB").setBoolean(onboardIO.getButtonBPressed());
    sensors.getEntry("buttonC").setBoolean(onboardIO.getButtonCPressed());
    sensors.getEntry("stampMs").setDouble(now);
    sensors.getEntry("ready").setBoolean(true);
  }

  @Override
  public void periodic() {
    publishSensors(); // Readings remain visible even when disabled.

    long stop = stopId.getInteger(0);
    if (stop != lastStopId) {
      lastStopId = stop;
      if (running != null) running.cancel();
      drivetrain.stop();
      status.setString("Stopped");
      return;
    }

    long id = runId.getInteger(0);
    if (id == lastRunId) return;
    lastRunId = id;
    if (running != null) running.cancel();

    if (!DriverStation.isTeleopEnabled()) {
      status.setString("Enable Teleoperated mode first");
      return;
    }

    try {
      String[] blocks = sequence.getString("").split(",");
      if (blocks.length < 1 || blocks.length > 8) {
        throw new IllegalArgumentException("Use 1-8 blocks");
      }
      List<Command> commands = new ArrayList<>();
      double total = 0.0;
      for (String block : blocks) {
        String[] fields = block.trim().split(":");
        if (fields.length != 2 && fields.length != 3) {
          throw new IllegalArgumentException("Invalid block: " + block);
        }
        String direction = fields[0].trim().toLowerCase(java.util.Locale.ROOT);
        double seconds = Double.parseDouble(fields[1].trim());
        double speed = fields.length == 3
            ? Double.parseDouble(fields[2].trim())
            : (direction.equals("left") || direction.equals("right") ? 0.30 : 0.35);
        if (!Double.isFinite(seconds) || seconds < 0.1 || seconds > 2.5) {
          throw new IllegalArgumentException("Each block must last 0.1-2.5 sec");
        }
        total += seconds;
        if (total > 8.00001) {
          throw new IllegalArgumentException("8-second limit exceeded");
        }
        commands.add(BlockMovement.move(drivetrain, direction, seconds, speed));
      }

      running = new SequentialCommandGroup(commands.toArray(new Command[0]))
          .finallyDo(interrupted -> {
            if (lastRunId == id) {
              status.setString(interrupted ? "Stopped" : "Complete");
            }
          });
      running.schedule();
      status.setString("Running");
    } catch (IllegalArgumentException e) {
      status.setString("Error: " + e.getMessage());
    }
  }
}
