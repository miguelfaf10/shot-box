import base64
import sys

from pathlib import Path
from typing import List
import logging

import typer
from rich.console import Console
from rich.segment import Segment
from rich.progress import Progress

from PIL import Image

from logic import PhotoOrganizer
from utils import get_logger, scan_folder


DB_FILE_NAME = "photo.db"
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".bmp"]


# Create configure module   module_logger
logger = get_logger(__name__)

app = typer.Typer()
console = Console()


@app.command()
def create(path_str: str):
    """
    Creates a photo repository with the given path. If the path already exists, it logs the message and prints a message to the console
    If it doesn't exist, it creates a new photo repository at the path and logs a message and prints a message to the console.

    Args:
    path_str: A string representing the path where to create the photo repository.

    Returns:
    None.
    """
    path = Path(path_str).absolute()
    if path.exists():
        logger.info(f"Path {str(path)} already exists")
        console.print(f"Path {str(path)} already exists")
    else:
        path.joinpath(".photo-organizer").mkdir(parents=True)
        logger.info(f"Created photo repository in: {str(path)}")
        console.print(f"Created photo repository in: {str(path)}")

    photo_org = PhotoOrganizer(path, DB_FILE_NAME)


@app.command()
def info(path_str: str):
    path = Path(path_str).absolute()
    if not path.joinpath(".photo-organizer/"):
        console.print(f"Path {str(path)} is not a valid repository")
    else:
        photo_org = PhotoOrganizer(path, DB_FILE_NAME)
        info = photo_org.get_summary()
        console.print(f"Images in Database   : {info['total_photos']} entries")
        console.print(f"Images in Repository : {info['files_exist']} files")
        console.print(
            f"Diskspace occupied   : {int(info['total_size'])/1024/1024:.0f} MB"
        )


@app.command()
def add(repo_str: str, folder_lst: List[str]):
    repo_path = Path(repo_str)
    photo_org = PhotoOrganizer(repo_path, db_filename=DB_FILE_NAME)

    ignored_folders = []
    ignored_images = []
    processed_images = []

    progress = Progress()
    with progress:
        console.print(progress)
        add_folder_task = progress.add_task(
            "[red]Adding folders: ", total=len(folder_lst)
        )

        for folder_str in folder_lst:
            folder_path = Path(folder_str)

            if not folder_path.exists():
                ignored_folders.append(folder_path.name)
                continue

            # find all image files in folder and sub-folders
            image_paths = scan_folder(folder_path, IMAGE_EXTENSIONS)
            add_file_task = progress.add_task(
                "[blue]Adding files:   ", total=len(image_paths)
            )

            for image_path in image_paths:
                progress.update(add_file_task, advance=1)

                if not photo_org.process_file(image_path):
                    ignored_images.append(image_path.name)
                else:
                    processed_images.append(image_path.name)

            progress.reset(add_file_task)
            progress.update(add_folder_task, advance=1)

    if ignored_folders:
        console.print(f"Ignored {len(ignored_folders)} folders")

    if ignored_images:
        console.print(
            f"Added {len(processed_images)}/{len(processed_images)+len(ignored_images)} images"
        )


@app.command()
def delete():
    print("Deleting user: Hiro Hamada")


if __name__ == "__main__":
    app()
