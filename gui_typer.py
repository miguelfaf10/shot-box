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
    else:
        path.joinpath(".photo-organizer").mkdir(parents=True)
        logger.info(f"Created photo repository in: {str(path)}")
    photo_org = PhotoOrganizer(path)


@app.command()
def info(path_str: str):
    path = Path(path_str).absolute()
    if not path.joinpath(".photo-organizer/"):
        console.print(f"Path {str(path)} is not a valid repository")
    else:
        photo_org = PhotoOrganizer(path)
        info = photo_org.get_summary()
        console.print(info)


@app.command()
def add(repo_str: str, path_lst: List[str]):
    repo_path = Path(repo_str)
    photo_org = PhotoOrganizer(repo_path)

    path_ignored = []
    for path_str in path_lst:
        path = Path(path_str)
        if not path.exists():
            path_ignored.append(path_str)
        else:
            list_image_paths = photo_org.scan_folder(path)
            list_photos = photo_org.analyse_images(list_image_paths)
            photo_org.add_images(list_photos)
            photo_org.copy_images(list_photos)

    if path_ignored:
        console.print(f"Paths {path_ignored} doesn't exist and will be ignored")


@app.command()
def delete():
    print("Deleting user: Hiro Hamada")


if __name__ == "__main__":
    app()
