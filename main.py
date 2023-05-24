import sys
from app.gui_typer import app as gui_typer_main


def main():
    # Pass command line arguments to gui_typer_main
    gui_typer_main(sys.argv[1:])


if __name__ == "__main__":
    main()
