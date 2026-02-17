"""
ElegooSlicer implementation for slicing STL files to G-code.

⚠️ CRITICAL ISSUE: ElegooSlicer's CLI crashes with segmentation fault when slicing.
While it shows CLI options with --help, it segfaults when actually executing:
    ElegooSlicer --slice 0 --outputdir ./output model.stl
    [1] segmentation fault

RECOMMENDATION: Use OrcaSlicer instead, which has stable CLI support
and can import .elegoo_printer config files without issues.

This class is kept for reference but should NOT be used in production.
"""
import asyncio
import logging
import shutil
from pathlib import Path
from typing import List, Optional

from src.slicer.base import BaseSlicer

logger = logging.getLogger(__name__)


class ElegooSlicer(BaseSlicer):
    """
    ElegooSlicer wrapper for converting STL files to G-code using subprocess.
    
    ⚠️ WARNING: ElegooSlicer CLI is BROKEN - crashes with segmentation fault.
    DO NOT USE THIS CLASS. Use OrcaSlicer instead.
    
    This implementation is kept for reference only.
    """

    def __init__(
        self,
        preset_path: Optional[Path] = None,
        elegoo_bin_path: Optional[str] = None,
    ):
        """
        Initialize ElegooSlicer wrapper.

        Args:
            preset_path: Path to .elegoo_printer preset file. If None, uses default from config/printers/
            elegoo_bin_path: Path to ElegooSlicer binary. If None, searches common locations
        """
        self.preset_path = preset_path or self._get_default_preset()
        self.elegoo_bin = elegoo_bin_path or self._find_elegoo_binary()
        
        if not self.elegoo_bin:
            raise FileNotFoundError(
                "ElegooSlicer binary not found. Please install ElegooSlicer:\n"
                "  Download from: https://www.elegoo.com/pages/3d-printing-user-support"
            )
        
        if self.preset_path and self.preset_path.exists():
            logger.info(f"ElegooSlicer initialized: binary={self.elegoo_bin}, preset={self.preset_path.name}")
        else:
            logger.warning(
                f"ElegooSlicer initialized without custom preset (will use ElegooSlicer defaults). "
                f"To use custom settings, place .elegoo_printer file in config/printers/"
            )
            logger.info(f"ElegooSlicer initialized: binary={self.elegoo_bin}, preset=None (using defaults)")

    def _get_default_preset(self) -> Optional[Path]:
        """Get the default preset path from config/printers/."""
        config_dir = Path(__file__).resolve().parent.parent.parent / "config" / "printers"
        
        # Look for .elegoo_printer files (native ElegooSlicer config bundles)
        elegoo_configs = list(config_dir.glob("*.elegoo_printer"))
        if elegoo_configs:
            logger.info(f"Found Elegoo config: {elegoo_configs[0].name}")
            return elegoo_configs[0]
        
        # Fallback to JSON files
        json_configs = list(config_dir.glob("*Elegoo*.json"))
        if json_configs:
            logger.info(f"Found JSON config: {json_configs[0].name}")
            return json_configs[0]
        
        return None

    def _find_elegoo_binary(self) -> Optional[str]:
        """
        Find ElegooSlicer binary in common installation locations.
        
        Returns:
            Path to elegoo-slicer or ElegooSlicer binary, or None if not found
        """
        # Common locations for ElegooSlicer
        possible_paths = [
            "/Applications/ElegooSlicer.app/Contents/MacOS/ElegooSlicer",  # macOS app bundle
            shutil.which("elegoo-slicer"),  # in PATH
            shutil.which("ElegooSlicer"),  # alternative name in PATH
        ]
        
        for path in possible_paths:
            if path and Path(path).exists():
                logger.info(f"Found ElegooSlicer binary at: {path}")
                return path
        
        logger.warning("ElegooSlicer binary not found in common locations")
        return None

    async def slice_file(self, stl_path: Path, output_dir: Path) -> Path:
        """
        Slice a single STL file to G-code using ElegooSlicer.

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
        
        # Build command
        cmd = [
            str(self.elegoo_bin),
            "--slice", "0",  # 0 = slice all plates  
            "--outputdir", str(output_dir),
        ]
        
        # Add preset if available
        # For .elegoo_printer files, we need to extract and use the printer JSON
        # For now, rely on ElegooSlicer's configured defaults
        # User should import the .elegoo_printer file in ElegooSlicer GUI first
        if self.preset_path and self.preset_path.exists():
            if self.preset_path.suffix == ".elegoo_printer":
                logger.info(f"Using Elegoo printer bundle: {self.preset_path.name}")
                logger.info("Note: Import this file in ElegooSlicer GUI first for best results")
            elif self.preset_path.suffix == ".json":
                # Try loading JSON config (may or may not work depending on completeness)
                logger.debug(f"Attempting to use JSON config: {self.preset_path.name}")
        else:
            logger.debug("Using ElegooSlicer's configured default settings")
        
        cmd.append(str(stl_path))
        
        logger.info(f"Slicing {stl_path.name} with ElegooSlicer...")
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
                logger.debug(f"ElegooSlicer stdout: {stdout.decode()}")
            if stderr:
                logger.debug(f"ElegooSlicer stderr: {stderr.decode()}")
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else stdout.decode() if stdout else "Unknown error"
                logger.error(f"ElegooSlicer failed with code {process.returncode}: {error_msg}")
                raise RuntimeError(f"Slicing failed: {error_msg}")
            
            if not gcode_path.exists():
                raise RuntimeError(f"G-code file not created: {gcode_path}")
            
            file_size = gcode_path.stat().st_size
            logger.info(f"✅ Sliced {stl_path.name} -> {gcode_path.name} ({file_size / 1024:.1f} KB)")
            
            return gcode_path
            
        except FileNotFoundError:
            raise RuntimeError(f"Failed to execute ElegooSlicer binary: {self.elegoo_bin}")
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
