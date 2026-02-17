"""
OrcaSlicer implementation for slicing STL files to G-code.
"""
import asyncio
import logging
import shutil
from pathlib import Path
from typing import List, Optional

from src.slicer.base import BaseSlicer

logger = logging.getLogger(__name__)


class OrcaSlicer(BaseSlicer):
    """
    OrcaSlicer wrapper for converting STL files to G-code using subprocess.
    
    Requires OrcaSlicer to be installed and accessible via CLI.
    On macOS: brew install --cask orcaslicer
    """

    def __init__(
        self,
        preset_path: Optional[Path] = None,
        orca_bin_path: Optional[str] = None,
    ):
        """
        Initialize OrcaSlicer wrapper.

        Args:
            preset_path: Path to .3mf preset file. If None, uses default from config/printers/
            orca_bin_path: Path to OrcaSlicer binary. If None, searches common locations
        """
        self.preset_path = preset_path or self._get_default_preset()
        self.orca_bin = orca_bin_path or self._find_orca_binary()
        
        if not self.orca_bin:
            raise FileNotFoundError(
                "OrcaSlicer binary not found. Please install OrcaSlicer:\n"
                "  macOS: brew install --cask orcaslicer\n"
                "  Linux: Download from https://github.com/SoftFever/OrcaSlicer"
            )
        
        if self.preset_path and self.preset_path.exists():
            logger.info(f"OrcaSlicer initialized: binary={self.orca_bin}, preset={self.preset_path.name}")
        else:
            logger.warning(
                f"OrcaSlicer initialized without custom preset (will use OrcaSlicer defaults). "
                f"To use custom settings, export them to JSON from OrcaSlicer GUI."
            )
            logger.info(f"OrcaSlicer initialized: binary={self.orca_bin}, preset=None (using defaults)")

    def _get_default_preset(self) -> Optional[Path]:
        """Get the default preset path from config/printers/."""
        config_dir = Path(__file__).resolve().parent.parent.parent / "config" / "printers"
        
        # Look for JSON config files first (exported from OrcaSlicer)
        json_configs = list(config_dir.glob("*.json"))
        if json_configs:
            logger.info(f"Found JSON config: {json_configs[0].name}")
            return json_configs[0]
        
        # Fallback to 3MF (won't work with --load-settings but kept for reference)
        mf_configs = list(config_dir.glob("*.3mf"))
        if mf_configs:
            logger.warning(
                f"Found 3MF file ({mf_configs[0].name}) but it cannot be used with CLI. "
                "Export settings to JSON from OrcaSlicer GUI."
            )
        
        return None

    def _find_orca_binary(self) -> Optional[str]:
        """
        Find OrcaSlicer binary in common installation locations.
        
        Returns:
            Path to orca-slicer or orcaslicer-console binary, or None if not found
        """
        # Common locations for OrcaSlicer
        possible_paths = [
            "/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer",  # macOS app bundle
            "/Applications/OrcaSlicer.app/Contents/MacOS/orcaslicer",  # alternative name
            shutil.which("orcaslicer"),  # in PATH
            shutil.which("orca-slicer"),  # alternative name in PATH
            shutil.which("OrcaSlicer"),  # capitalized version
        ]
        
        for path in possible_paths:
            if path and Path(path).exists():
                logger.info(f"Found OrcaSlicer binary at: {path}")
                return path
        
        logger.warning("OrcaSlicer binary not found in common locations")
        return None

    async def slice_file(self, stl_path: Path, output_dir: Path) -> Path:
        """
        Slice a single STL file to G-code using OrcaSlicer.

        Args:
            stl_path: Path to the input STL file
            output_dir: Directory where G-code should be saved

        Returns:
            Path to the generated G-code file

        Raises:
            FileNotFoundError: If STL file doesn't exist
            RuntimeError: If slicing fails
        """
        if not stl_path.exists():
            raise FileNotFoundError(f"STL file not found: {stl_path}")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Output G-code file will have same name as STL but with .gcode extension  
        gcode_path = output_dir / f"{stl_path.stem}.gcode"
        
        # Build command - OrcaSlicer will use its configured defaults
        # The JSON files we have are printer-only configs, not complete bundles
        # Best approach: Configure the printer in OrcaSlicer GUI once, then CLI inherits settings
        cmd = [
            str(self.orca_bin),
            "--slice", "0",  # 0 = slice all plates  
            "--no-check",    # Skip validation checks (G-code validation can be overly strict)
            "--outputdir", str(output_dir),
        ]
        
        # Note: --load-settings requires a complete config bundle (printer+filament+process)
        # Since we only have printer config, we'll rely on OrcaSlicer's saved defaults
        # User should configure their printer in OrcaSlicer GUI first
        logger.debug("Using OrcaSlicer's configured default settings with --no-check flag")
        
        cmd.append(str(stl_path))
        
        logger.info(f"Slicing {stl_path.name} with OrcaSlicer...")
        logger.debug(f"Command: {' '.join(cmd)}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            # Log output for debugging
            if stdout:
                logger.debug(f"OrcaSlicer stdout: {stdout.decode()}")
            if stderr:
                logger.debug(f"OrcaSlicer stderr: {stderr.decode()}")
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else stdout.decode() if stdout else "Unknown error"
                logger.error(f"OrcaSlicer failed with code {process.returncode}: {error_msg}")
                raise RuntimeError(f"Slicing failed: {error_msg}")
            
            if not gcode_path.exists():
                raise RuntimeError(f"G-code file not created: {gcode_path}")
            
            file_size = gcode_path.stat().st_size
            logger.info(f"✅ Sliced {stl_path.name} -> {gcode_path.name} ({file_size / 1024:.1f} KB)")
            
            return gcode_path
            
        except FileNotFoundError:
            raise RuntimeError(f"Failed to execute OrcaSlicer binary: {self.orca_bin}")
        except Exception as e:
            logger.exception(f"Unexpected error during slicing: {e}")
            raise RuntimeError(f"Slicing failed: {e}")

    async def slice_files(self, stl_paths: List[Path], output_dir: Path) -> List[Path]:
        """
        Slice multiple STL files to G-code.

        Args:
            stl_paths: List of paths to STL files
            output_dir: Directory where G-code files should be saved

        Returns:
            List of paths to generated G-code files

        Raises:
            RuntimeError: If any slicing operation fails
        """
        logger.info(f"Starting batch slicing of {len(stl_paths)} file(s)...")
        
        gcode_paths = []
        errors = []
        
        for stl_path in stl_paths:
            try:
                gcode_path = await self.slice_file(stl_path, output_dir)
                gcode_paths.append(gcode_path)
            except Exception as e:
                logger.error(f"Failed to slice {stl_path.name}: {e}")
                errors.append((stl_path.name, str(e)))
        
        if errors:
            error_summary = "\n".join([f"  • {name}: {err}" for name, err in errors])
            raise RuntimeError(
                f"Failed to slice {len(errors)}/{len(stl_paths)} file(s):\n{error_summary}"
            )
        
        logger.info(f"✅ Successfully sliced {len(gcode_paths)} file(s)")
        return gcode_paths
