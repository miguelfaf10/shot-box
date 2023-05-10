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


class Repository:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path.absolute()
        self.db_path = repo_path.joinpath(f".photo-organizer/{DB_FILE_NAME}")
        if not self.check_repo():
            self.create_repo()
            console.print(f"Repo created at {str(self.repo_path)}")
        else:
            console.print(f"Repo folder at {str(self.repo_path)} already exists")
        self.photo_organizer = PhotoOrganizer(self.repo_path, self.db_path)

    def check_repo(self):
        if not self.repo_path.exists():
            logger.debug(f"Folder {str(self.repo_path)} does not exist")
            return False

        if not self.db_path.parent.exists():
            logger.debug(f"Database folder {str(self.db_path)} not present")
            return False

        return True

    def create_repo(self):
        self.db_path.parent.mkdir(parents=True)
        return True


@app.command()
def create(repo_str: str):
    """
    Creates a photo repository with the given path. If the path already exists, it logs the message and prints a message to the console
    If it doesn't exist, it creates a new photo repository at the path and logs a message and prints a message to the console.

    Args:
    path_str: A string representing the path where to create the photo repository.

    Returns:
    None
    """
    repo = Repository(Path(repo_str))
    photo_org = PhotoOrganizer(repo.repo_path, repo.db_path)


@app.command()
def info(repo_str: str):
    repo = Repository(Path(repo_str))

    if not repo.check_repo():
        console.print(f"Path {str(repo.repo_pathpath)} is not a valid repository")
        exit(-1)

    photo_org = PhotoOrganizer(repo.repo_path, repo.db_path)
    info = photo_org.get_summary()
    console.print(f"Images in Database   : {info['total_photos']} entries")
    console.print(f"Images in Repository : {info['files_exist']} files")
    console.print(f"Diskspace occupied   : {int(info['total_size'])/(2*1024):.0f} MB")


@app.command()
def add(repo_str: str, folder_lst: List[str]):
    repo = Repository(Path(repo_str))
    if not repo.check_repo():
        console.print(f"Path {str(repo.repo_pathpath)} is not a valid repository")
        exit(-1)

    photo_org = PhotoOrganizer(repo.repo_path, repo.db_path)
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
def verify(repo_str: str):
    repo = Repository(Path(repo_str))
    if not repo.check_repo():
        console.print(f"Path {str(repo.repo_pathpath)} is not a valid repository")
        exit(-1)

    photo_org = PhotoOrganizer(repo.repo_path, db_filename=DB_FILE_NAME)


if __name__ == "__main__":
    app()
