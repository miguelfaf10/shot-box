from pathlib import Path
from typing import List
import logging


def scan_folder(folder_path: Path, file_extensions, recursive=False) -> List[Path]:
    # Add new photo folders to the database

    file_list = folder_path.glob("**/*") if recursive else folder_path.glob("*")

    return [
        file_path
        for file_path in file_list
        if file_path.is_file() and file_path.suffix.lower() in file_extensions
    ]


def get_logger(name):
    logger = logging.getLogger("rich")
    logger.setLevel(logging.DEBUG)

    #        formatter = logging.Formatter("%(levelname)s - %(message)s")
    formatter = logging.Formatter(
        "%(asctime)s -  [%(filename)s:%(lineno)d] - %(levelname)s - %(message)s"
    )
    handler = logging.FileHandler("/home/miguel/sw/shot-box/logs/log.log", mode="a")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
