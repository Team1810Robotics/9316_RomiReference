package frc.robot.commands;

import edu.wpi.first.wpilibj2.command.Command;
import edu.wpi.first.wpilibj2.command.Commands;
import frc.robot.subsystems.Drivetrain;

/** One timed movement block. The speed value is a normalized drive command, not measured velocity. */
public final class BlockMovement {
  private BlockMovement() {}

  /** Keep the original 3-argument API available to any existing code. */
  public static Command move(Drivetrain drive, String direction, double seconds) {
    double defaultSpeed =
        (direction.equalsIgnoreCase("left") || direction.equalsIgnoreCase("right")) ? 0.30 : 0.35;
    return move(drive, direction, seconds, defaultSpeed);
  }

  public static Command move(Drivetrain drive, String direction, double seconds, double speed) {
    if (!Double.isFinite(seconds) || seconds < 0.1 || seconds > 2.5) {
      throw new IllegalArgumentException("Duration must be 0.1-2.5 sec");
    }
    if (!Double.isFinite(speed) || speed < 0.30 || speed > 0.60) {
      throw new IllegalArgumentException("Speed must be 0.30-0.60");
    }

    final double forward;
    final double rotation;
    switch (direction.toLowerCase(java.util.Locale.ROOT)) {
      case "forward": forward = -speed; rotation = 0; break;
      case "backward": forward = speed; rotation = 0; break;
      case "left": forward = 0; rotation = -speed; break;
      case "right": forward = 0; rotation = speed; break;
      default: throw new IllegalArgumentException("Unknown direction: " + direction);
    }

    return Commands.runEnd(
        () -> drive.arcadeDrive(forward, rotation),
        drive::stop,
        drive)
        .withTimeout(seconds);
  }
}
