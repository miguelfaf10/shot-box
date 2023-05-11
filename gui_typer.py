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
            console.print(f"Repo folder at {str(self.repo_path)} exists")
        self.photo_org = PhotoOrganizer(self.repo_path, self.db_path)

    def check_repo(self):
        if not (self.repo_path.exists() and self.db_path.parent.exists()):
            return False
        else:
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
    # photo_org = PhotoOrganizer(repo.repo_path, repo.db_path)


def start_repo(repo_path: Path):
    """Create Repository object based on input repository folder and checks if this
    is folder contains a valir repository.

    Args:
        repo_path (Path): filesystem path to repository folder

    Returns:
        Repository: repo object
    """
    repo = Repository(repo_path)
    if not repo.check_repo():
        console.print(f"Path {str(repo.repo_pathpath)} is not a valid repository")
        exit(-1)
    # photo_org = PhotoOrganizer(repo.repo_path, repo.db_path)

    return repo


@app.command()
def info(repo_str: str):
    repo = start_repo(Path(repo_str))

    info = repo.photo_org.get_info()
    console.print(f"Images in Database   : {info['total_photos']} entries")
    console.print(f"Images in Repository : {info['files_exist']} files")
    console.print(f"Diskspace occupied   : {int(info['total_size'])/(1024**2):.0f} MB")


@app.command()
def add(repo_str: str, folder_lst: List[str]):
    repo = start_repo(Path(repo_str))

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
                "[blue]Adding images:  ", total=len(image_paths)
            )

            for image_path in image_paths:
                if "3904" in image_path.name:
                    pass
                progress.update(add_file_task, advance=1)

                if not repo.photo_org.process_file(image_path):
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
    repo = start_repo(Path(repo_str))

    out = repo.photo_org.check_consistency(IMAGE_EXTENSIONS)

    if sum((len(num) for num in out.values())) == 0:
        console.print("Repository is in perfect shape!")
    else:
        if (n := len(out["exist_db_not_copied"])) > 0:
            console.print(f"WARNING: Files in Database but not copied to Repo: {n}")
        if (n := len(out["exist_repo_not_db"])) > 0:
            console.print(f"ERROR:   Files in Repo but missing in Database: {n}")
        if (n := len(out["exist_db_not_repo"])) > 0:
            console.print(f"ERROR:   Files in Database but missing in Repo: {n}")
        if (n := len(out["exist_repo_incorrect_name"])) > 0:
            console.print(f"ERROR:   Files in Repo with incorrect name:     {n}")
    print(out)


if __name__ == "__main__":
    app()
