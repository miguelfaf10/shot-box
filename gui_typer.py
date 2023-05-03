from pathlib import Path
from typing import List
import logging

import typer
from rich.console import Console

from logic import PhotoOrganizer
from utils import get_logger

# Create configure module   module_logger
logger = get_logger(main=True)

app = typer.Typer()
console = Console()


@app.command()
def create(path_str: str):
    path = Path(path_str).absolute()
    if path.exists():
        logger.info(f"Path {str(path)} already exists")
        console.print(f"Path {str(path)} already exists")
    else:
        path.joinpath(".photo-organizer").mkdir(parents=True)
        logger.info(f"Created photo repository in: {str(path)}")
        console.print(f"Created photo repository in: {str(path)}")

    photo_org = PhotoOrganizer(path)


@app.command()
def info(path_str: str):
    path = Path(path_str).absolute()
    if not path.joinpath(".photo-organizer/"):
        console.print(f"Path {str(path)} is not a valid repository")
    else:
        photo_org = PhotoOrganizer(path)
        info = photo_org.get_summary()
        console.print(f"Image entries in Database   : {info['total_photos']}")
        console.print(f"Image files in Repository   : {info['files_exist']}")
        console.print(f"Diskspace occupied by files : {info['total_size']}")


@app.command()
def add(repo_str: str, path_lst: List[str]):
    repo_path = Path(repo_str)
    photo_org = PhotoOrganizer(repo_path)

    path_ignored = []
    images_not_added = []
    for path_str in path_lst:
        path = Path(path_str)
        if not path.exists():
            path_ignored.append(path_str)
        else:
            image_not_added = photo_org.process_folder(path)

    if path_ignored:
        console.print("Paths below don't exist and will be ignored")
        console.print(path_ignored)

    if images_not_added:
        for image_str in images_not_added:
            console.print(
                f"Entry with perceptual-hash of {image_str} already exists in repository. File not added and not copied."
            )
            console.print(path_ignored)


@app.command()
def delete():
    print("Deleting user: Hiro Hamada")


if __name__ == "__main__":
    app()
