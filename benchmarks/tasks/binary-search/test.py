"""Hidden test. Not shown to the agent. Run after the arm finishes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from broken import search  # the file the agent edits


def main():
    xs = [1, 3, 5, 7, 9, 11]
    for i, v in enumerate(xs):
        assert search(xs, v) == i, f"search({v}) returned {search(xs, v)}, want {i}"
    for v in (0, 2, 4, 12):
        assert search(xs, v) == -1, f"search({v}) should be -1"
    assert search([], 1) == -1
    assert search([4], 4) == 0
    print("PASS")


if __name__ == "__main__":
    main()
