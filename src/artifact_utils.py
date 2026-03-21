import tempfile
from pathlib import Path

from logging_utils import get_logger


logger = get_logger(__name__)


def create_temp_png_path(prefix):
    with tempfile.NamedTemporaryFile(
        prefix=f"macro_pulse_{prefix}_", suffix=".png", delete=False
    ) as handle:
        return handle.name


def resolve_output_path(output_path, prefix):
    if output_path:
        return output_path
    return create_temp_png_path(prefix)


def cleanup_files(file_paths):
    for file_path in file_paths:
        if not file_path:
            continue

        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.info("Removed temporary file: %s", path)
