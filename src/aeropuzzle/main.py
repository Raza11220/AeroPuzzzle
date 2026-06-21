"""CLI entry point for AeroPuzzle."""

import argparse
from aeropuzzle import __version__


def main():
    parser = argparse.ArgumentParser(
        prog="aeropuzzle",
        description="AeroPuzzle — A gesture-controlled sliding puzzle game using hand tracking.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    # Parse known args so we can still pass through any future flags
    parser.parse_args()

    # Launch the game
    from aeropuzzle.app import main as run_game
    run_game()


if __name__ == "__main__":
    main()
