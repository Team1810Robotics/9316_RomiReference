
import time
import ntcore

inst = ntcore.NetworkTableInstance.getDefault()
inst.startClient4("GirlScoutTest")
inst.setServer("127.0.0.1")

print("Connecting to WPILib simulation...")

deadline = time.monotonic() + 5

while not inst.isConnected() and time.monotonic() < deadline:
    time.sleep(0.1)

if not inst.isConnected():
    raise RuntimeError("NetworkTables server not found")

table = inst.getTable("GirlScoutBlocks")

sequence = table.getEntry("sequence")
run_id = table.getEntry("runId")
status = table.getEntry("status")

# Test with a short, low-speed movement sequence.
sequence.setString("forward:0.5,right:0.5")

# Increment the ID to request a new execution.
run_id.setInteger(run_id.getInteger(0) + 1)

print("Program submitted")

for _ in range(40):
    print("Status:", status.getString("Unknown"))
    time.sleep(0.25)
