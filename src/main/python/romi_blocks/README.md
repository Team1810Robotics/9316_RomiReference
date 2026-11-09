# Romi Blocks — local visual programming prototype

This is a **real Blockly editor**, coupled to your existing WPILib RomiReference project. It **does not** replace `RobotContainer.java`, `BlockMovement.java`, `BlockProgramReceiver.java`, or Elastic. The editor runs only on the same Windows laptop as WPILib simulation.

## One-time setup (while connected to internet Wi-Fi)

1. Copy the entire `romi_blocks` folder to your project's `src\main\python` directory.
2. From `src\main\python`, run:

   ```cmd
   py -3.14 romi_blocks\download_blockly.py
   ```

   This downloads the Blockly 13.4.0 JavaScript bundle into `romi_blocks\vendor\blockly.min.js`. The file is not included in the ZIP because it was not accessible from the build environment. Blockly is open source, Apache-2.0 licensed.

3. Ensure `pyntcore` remains installed for Python 3.14 (you already verified that in the successful `test_romi_blocks.py` test).

## Each session (Romi Wi-Fi; internet not required)

1. Power Romi and connect the laptop to the Romi Wi-Fi.
2. Launch WPILib **Simulate Robot Code**. Verify the websocket connection to Romi.
3. In Simulation GUI, select **Teleoperated** and **enable** the robot.
4. From `src\main\python`, start the bridge:

   ```cmd
   py -3.14 romi_blocks\bridge.py
   ```

5. Open **http://127.0.0.1:8765** in Chrome or Edge.
6. Drag blocks from the flyout into one connected vertical stack (or press Load example). Choose durations and click **Run blocks**.
7. Use **STOP robot** if you want to cancel a running sequence (it sends an incremented `stopId` to Java). **The Simulation GUI's Disable remains the primary safety stop.**

Keep the bridge terminal open. `Ctrl+C` shuts down the local web server.

## How it works

`Blockly` in browser → local HTTP server on `127.0.0.1:8765` → Python `ntcore` → `GirlScoutBlocks/sequence` and `GirlScoutBlocks/runId` on the simulation's localhost NetworkTables → your Java receiver → drive commands → Romi over Wi-Fi.

Status is read back from `GirlScoutBlocks/status`. Server also sends `GirlScoutBlocks/stopId` on Stop.

No Java changes are required if your working test script already uses those exact keys. The bridge enforces the same constraints as the receiver: 1–8 blocks, 0.1–2.5 seconds each, 8 seconds maximum. Only four actions are supported (forward, backward, left, right). To add loops, sensors, conditionals, or wait commands, extend the Java receiver first.

## Troubleshooting

- **Blockly missing**: Run `download_blockly.py` while on normal Internet Wi-Fi; after it downloads, Romi Wi-Fi is fine.
- **Waiting for WPILib simulation**: The bridge connects to `127.0.0.1` over NetworkTables; restart WPILib simulation and verify network access to Romi separately.
- **Enable Teleoperated mode first**: The Java `BlockProgramReceiver` intentionally refuses runs outside enabled Teleop.
- **Status Complete but no movement**: Test joystick movement and the Romi websocket; `Complete` only confirms the command finished, not that wheels turned.
- **Port 8765 already in use**: Close the previous `bridge.py` process, or adjust the `PORT` constant in bridge.py and the local URL.
- **Browser shows an old page**: Force reload with `Ctrl+Shift+R`.
- **Stop appears delayed**: Use Simulation GUI Disable immediately; network-command cancellation depends on the connection and Java receiver loop.

## For instructors

Suggested 5-minute challenge: Start with Forward 0.6 → Right 0.4 → Forward 0.6, then have students predict how doubling the turn duration changes the route. Test at reduced motor output in a clear space.
