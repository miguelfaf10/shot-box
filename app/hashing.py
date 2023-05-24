import hashlib
from click import Path

import imagehash

from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()


def perceptual_hash(image_path: Path, method: str = "phash") -> str:
    """
    Generates a perceptual hash identifier for an image using the specified method.

    Args:
        image_path (str): The file path of the image.
        method (str, optional): The hashing method to use. Defaults to 'phash'.
            Options: 'average', 'phash', 'dhash', 'whash'.

    Returns:
        str: The perceptual hash identifier for the image content.
    """
    if method not in ["average", "phash", "dhash", "whash"]:
        raise ValueError(f"Unsupported hashing method: {method}")

    with Image.open(image_path) as img:
        if method == "average":
            hash_value = imagehash.average_hash(img)
        elif method == "phash":
            hash_value = imagehash.phash(img)
        elif method == "dhash":
            hash_value = imagehash.dhash(img)
        elif method == "whash":
            hash_value = imagehash.whash(img)

    return str(hash_value)


def crypto_hash(image_path: str, algorithm: str = "sha256") -> str:
    """
    Generates a unique hash identifier for an image using the specified hashing algorithm.

    Args:
        image_path (str): The file path of the image.
        algorithm (str, optional): The hashing algorithm to use. Defaults to 'sha256'.

    Returns:
        str: The unique hash identifier for the image content.
    """
    if algorithm not in hashlib.algorithms_guaranteed:
        raise ValueError(f"Unsupported hashing algorithm: {algorithm}")

    hasher = hashlib.new(algorithm)

    with open(image_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)

    return hasher.hexdigest()
