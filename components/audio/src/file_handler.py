import hashlib
from pathlib import Path

class FileHandler:

    def __init__(self, resource_path: Path):
        self._resource_path = resource_path

    def write_file(self, path: Path, data: bytes):
        full_path = self._resource_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(data)
        print("Wrote file " + str(path))
    
    def get_hashes(self, path=None):
        if path is None:
            path = self._resource_path
        if path.is_dir():
            hashes = {}
            for sub_path in path.iterdir():
                hashes.update(self.get_hashes(sub_path))
        else:
            if path.name == ".gitignore":
                return {}
            with open(path, "rb") as f:
                data = f.read()
            checksum = hashlib.md5(data).hexdigest()
            # Represent as a POSIX path (forward slashes) on Windows too, since
            # Core and the component need to agree
            relative_path = path.relative_to(self._resource_path).as_posix()
            hashes = { relative_path: checksum }
        return hashes