"""One-time download of a pinned Blockly bundle for offline Romi Wi-Fi use."""
from pathlib import Path
from urllib.request import Request, urlopen

DEST = Path(__file__).resolve().parent / "vendor" / "blockly.min.js"
URLS = [
    "https://cdn.jsdelivr.net/npm/blockly@13.4.0/blockly.min.js",
    "https://unpkg.com/blockly@13.4.0/blockly.min.js",
]
DEST.parent.mkdir(parents=True, exist_ok=True)
for url in URLS:
    try:
        print("Downloading:", url)
        with urlopen(Request(url, headers={"User-Agent": "RomiBlocklySetup/1.0"}), timeout=30) as response:
            data = response.read(3_000_000)
        if len(data) < 100_000 or b"Blockly" not in data[:100_000]:
            # Bundles may not have a human-readable prefix; size is the useful check.
            if len(data) < 100_000 or data.lstrip().startswith(b"<"):
                raise ValueError("Download did not look like JavaScript")
        DEST.write_bytes(data)
        print(f"Saved {len(data):,} bytes to {DEST}")
        print("You can now switch to the Romi Wi-Fi; the editor works offline.")
        break
    except Exception as exc:
        print("Download failed:", exc)
else:
    raise SystemExit("Unable to fetch Blockly. Connect to regular internet Wi-Fi and try again.")
