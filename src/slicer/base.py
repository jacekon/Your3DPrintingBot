"""
Base abstract class for slicer implementations.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List


class BaseSlicer(ABC):
    """Abstract base class for 3D printer slicers."""

    @abstractmethod
    async def slice_file(self, stl_path: Path, output_dir: Path) -> Path:
        """
        Slice a single STL file to G-code.

        Args:
            stl_path: Path to the input STL file
            output_dir: Directory where G-code should be saved

        Returns:
            Path to the generated G-code file

        Raises:
            FileNotFoundError: If STL file or preset doesn't exist
            RuntimeError: If slicing fails
        """
        pass

    @abstractmethod
    async def slice_files(self, stl_paths: List[Path], output_dir: Path) -> List[Path]:
        """
        Slice multiple STL files to G-code.

        Args:
            stl_paths: List of paths to STL files
            output_dir: Directory where G-code files should be saved

        Returns:
            List of paths to generated G-code files

        Raises:
            FileNotFoundError: If any STL file or preset doesn't exist
            RuntimeError: If slicing fails
        """
        pass
