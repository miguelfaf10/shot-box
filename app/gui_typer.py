import base64

import sys
import yaml

from pathlib import Path
from typing import List
import itertools
import logging

import typer
from rich.console import Console
from rich.segment import Segment
from rich.table import Column
from rich.progress import (
    BarColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
    SpinnerColumn,
    TimeElapsedColumn,
    TaskProgressColumn,
)

from pyfiglet import Figlet

from logic import ImageOrganizer
from utils import get_logger, scan_folder

# configuration parameters
with open("app/config.yaml") as file:
    config = yaml.safe_load(file)

DB_FILE = config["database"]["file"]
DB_FOLDER = config["database"]["folder"]
IMAGE_EXTS = list(
    itertools.chain.from_iterable(
        values for values in config["image"]["types"].values()
    )
)

# Create configure module   module_logger
logger = get_logger(__name__)

app = typer.Typer()
console = Console()
figlet = Figlet(font="slant")


def welcome():
    figlet.width = 100
    return f'{figlet.renderText("Shot Box")} {figlet.renderText("Photo - Organizer")}'


class Repository:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path.absolute()
        self.db_path = repo_path.joinpath(DB_FOLDER).joinpath(DB_FILE)
        if not self.check_repo():
            self.create_repo()
            console.print(f"Repo created at {str(self.repo_path)}")
        else:
            console.print(f"Repo folder at {str(self.repo_path)} exists")
        self.photo_org = ImageOrganizer(self.repo_path, self.db_path)

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
    Creates an image repository in provided folder if this doesn't exist already.

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
    """Diplay information about image repository if this exists in provided folder.

    Args:
        repo_str (str): filesystem path to repository folder

    Returns:
        Repository: repo object
    """
    repo = start_repo(Path(repo_str))

    info = repo.photo_org.get_info()
    console.print(f"Images in Database   : {info['total_photos']} entries")
    console.print(f"Images in Repository : {info['files_exist']} files")
    console.print(f"Diskspace occupied   : {int(info['total_size'])/(1024**2):.0f} MB")


@app.command()
def add(repo_str: str, folder_lst: List[str]):
    """Add new images from input list of folder to existing or new repository.

    Args:
        repo_str (str): filesystem path to repository folder

    Returns:
        Repository: repo object
    """
    console.print(welcome())

    repo = start_repo(Path(repo_str))

    ignored_folders = []
    ignored_images = []
    processed_images = []

    subfolder_lst = list(
        itertools.chain.from_iterable(
            Path(folder_str).glob("**/") for folder_str in folder_lst
        )
    )

    progress = Progress(
        # TextColumn("[bold blue]{task.fields[foldername]}", justify="right")
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        TimeElapsedColumn(),
        TextColumn("{task.fields[foldername]}", table_column=Column(width=25)),
        transient=True,
    )

    with progress:
        console.print(progress)

        add_folder_task = progress.add_task("[red]Adding folders: ", foldername="...")
        add_file_task = progress.add_task("[blue]Adding images:  ", foldername="...")

        progress.update(add_folder_task, total=len(subfolder_lst))
        for subfolder_path in subfolder_lst:
            progress.update(
                add_folder_task,
                foldername=f"./{str(subfolder_path)}/",
            )
            if not subfolder_path.exists():
                ignored_folders.append(subfolder_path.name)
                continue

            # find all image files in folder and sub-folders
            image_paths = scan_folder(subfolder_path, IMAGE_EXTS)

            progress.update(add_file_task, total=len(image_paths))
            for image_path in image_paths:
                progress.update(
                    add_file_task,
                    foldername=image_path.name,
                )

                if not repo.photo_org.process_file(image_path):
                    ignored_images.append(image_path.name)
                else:
                    processed_images.append(image_path.name)

                progress.update(add_file_task, advance=1)

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
    """Verify consistenty of existing image repository by database info with existing image files.

    Args:
        repo_str (str): filesystem path to repository folder

    Returns:
        None
    """
    repo = start_repo(Path(repo_str))

    out = repo.photo_org.check_consistency(IMAGE_EXTS)

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


@app.command()
def find(repo_str: str, tag: str, value: str):
    """Diplay information about image repository if this exists in provided folder.

    Args:
        repo_str (str): filesystem path to repository folder

    Returns:
        Repository: repo object
    """
    repo = start_repo(Path(repo_str))

    if tag == "country":
        out = repo.photo_org.filter_photos({"country": value})
        print(type(out[0].width))
    print(out)


if __name__ == "__main__":
    app()
