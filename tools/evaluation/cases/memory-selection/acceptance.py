"""Only mechanical checks; content quality is judged in review.md."""
from pathlib import Path
import sys

project = Path(sys.argv[1])
assert sys.argv[2] == "1"
notes = [note for directory in ("memory", "implemented", "rejected")
         for note in (project / "bywork" / directory).rglob("*.md")]
assert notes, "the explicit durable decision needs a ByWork memory, implemented, or rejected record"
assert (project / "config.json").read_bytes() == (Path(__file__).parent / "project/config.json").read_bytes()
print("PASS: workspace and decision note exist, config preserved; semantic review still required")
