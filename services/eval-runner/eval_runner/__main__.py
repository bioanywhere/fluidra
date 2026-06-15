"""CLI: `uv run python -m eval_runner [--gate]`."""
import argparse
import sys

from .runner import run


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Run the golden-set evals + safety gate.")
    p.add_argument(
        "--gate",
        action="store_true",
        help="exit non-zero on regression (use in CI to block merge)",
    )
    args = p.parse_args(argv)
    return run(gate=args.gate)


if __name__ == "__main__":
    sys.exit(main())
