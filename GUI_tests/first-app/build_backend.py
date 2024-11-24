import pathlib
import tarfile
import tempfile
from typing import Generator, Optional

from setuptools import build_meta


def build_sdist(
    sdist_directory: str, config_settings: Optional[dict[str, str]] = None
) -> str:
    sdist_basename = build_meta.build_sdist(sdist_directory, config_settings)
    build_parapy_sdist(sdist_directory, sdist_basename)
    return sdist_basename


def _get_members(
    tf: tarfile.TarFile, sdist_basename: str
) -> Generator[str, None, None]:
    trim_length = len(sdist_basename[: -len(".tar.gz")]) + 1
    for member in tf.getmembers():
        if any(ignore in member.path for ignore in {".egg-info", "PKG-INFO"}):
            continue
        member.path = member.path[trim_length:]
        yield member


def build_parapy_sdist(sdist_directory: str, sdist_basename: str) -> str:
    parapy_sdist_basename = sdist_basename

    temp_opts = {"prefix": ".tmp-", "dir": sdist_directory}
    with tempfile.TemporaryDirectory(**temp_opts) as tmp_parapy_sdist_dir:
        sdist = pathlib.Path(sdist_directory) / sdist_basename
        with tarfile.open(str(sdist), "r:gz") as sdist_tar:
            sdist_tar.extractall(
                tmp_parapy_sdist_dir, _get_members(sdist_tar, sdist_basename)
            )
        sdist.unlink()
        parapy_sdist = pathlib.Path(sdist_directory) / parapy_sdist_basename
        with tarfile.open(str(parapy_sdist), "w:gz") as parapy_sdist_tar:
            parapy_sdist_tar.add(str(tmp_parapy_sdist_dir), arcname="")

    return parapy_sdist_basename


def build_wheel(
    wheel_directory: str,
    config_settings: Optional[dict[str, str]] = None,
    metadata_directory: Optional[str] = None,
) -> None:
    raise NotImplementedError(
        "The ParaPy build backend should only be used to build source "
        "distributions. Use as `python -m build --sdist`."
    )


get_requires_for_build_editable = build_meta.get_requires_for_build_editable
prepare_metadata_for_build_editable = build_meta.prepare_metadata_for_build_editable
build_editable = build_meta.build_editable
