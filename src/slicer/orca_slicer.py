"""
OrcaSlicer implementation for slicing STL files to G-code.
"""
import asyncio
import json
import logging
import shutil
import tempfile
import zipfile
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
        self._cli_cache_dir = Path(__file__).resolve().parent.parent.parent / "config" / "printers" / ".orca_cli_cache"
        self._cli_cache_dir.mkdir(exist_ok=True)
        
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
        
        # Priority order for config files:
        # 1. Extracted bundle directory (printer/filament/process)
        # 2. .orca_printer (OrcaSlicer native config bundle)
        # 3. .elegoo_printer (ElegooSlicer config, compatible with OrcaSlicer)
        # 4. .json (exported settings)
        # 5. .3mf (project file, not ideal for CLI)

        bundle_dirs = [
            path for path in config_dir.iterdir()
            if path.is_dir() and (path / "bundle_structure.json").exists()
        ]
        if bundle_dirs:
            preferred = next((path for path in bundle_dirs if path.name.lower().startswith("elegoocc")), bundle_dirs[0])
            logger.info(f"Found bundle directory preset: {preferred.name}")
            return preferred
        
        orca_configs = list(config_dir.glob("*.orca_printer"))
        if orca_configs:
            logger.info(f"Found OrcaSlicer config: {orca_configs[0].name}")
            return orca_configs[0]
        
        elegoo_configs = list(config_dir.glob("*.elegoo_printer"))
        if elegoo_configs:
            logger.info(f"Found Elegoo config: {elegoo_configs[0].name}")
            return elegoo_configs[0]
        
        json_configs = list(config_dir.glob("*.json"))
        if json_configs:
            logger.info(f"Found JSON config: {json_configs[0].name}")
            return json_configs[0]
        
        # Fallback to 3MF (won't work with --load-settings but kept for reference)
        mf_configs = list(config_dir.glob("*.3mf"))
        if mf_configs:
            logger.warning(
                f"Found 3MF file ({mf_configs[0].name}) but it cannot be used with CLI. "
                "Export settings to JSON from OrcaSlicer GUI or use .orca_printer/.elegoo_printer."
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

    def _find_orca_datadir(self) -> Optional[Path]:
        candidates = [
            Path.home() / "Library" / "Application Support" / "OrcaSlicer",
            Path.home() / ".config" / "OrcaSlicer",
        ]

        for path in candidates:
            if path.exists():
                return path

        return None

    def _find_machine_preset(self, name: str) -> Optional[Path]:
        if not name:
            return None

        datadir = self._find_orca_datadir()
        if not datadir:
            return None

        user_match = list((datadir / "user" / "default").rglob(f"machine/**/{name}.json"))
        if user_match:
            return user_match[0]

        system_match = list((datadir / "system").rglob(f"machine/**/{name}.json"))
        if system_match:
            return system_match[0]

        return None

    def _get_datadir_presets(self) -> Optional[tuple[Path, Path, Path]]:
        datadir = self._find_orca_datadir()
        if not datadir:
            return None

        machine = datadir / "user" / "default" / "machine" / "Elegoo Centauri Carbon 0.4 nozzle - JK.json"
        filament = datadir / "user" / "default" / "filament" / "Elegoo PLA-CF @ECC - JK.json"

        process_candidates = [
            datadir / "user" / "default" / "process" / "0.12mm Fine @Elegoo CC 0.4 nozzle - JK.json",
            datadir / "system" / "Elegoo" / "process" / "ECC" / "0.12mm Fine @Elegoo CC 0.4 nozzle.json",
            datadir / "system" / "Elegoo" / "process" / "ECC" / "0.20mm Standard @Elegoo CC 0.4 nozzle.json",
        ]
        process = next((path for path in process_candidates if path.exists()), None)

        if machine.exists() and filament.exists() and process:
            return machine, filament, process

        return None

    def _extract_config_bundle(self, bundle_path: Path) -> Optional[List[Path]]:
        """
        Extract .orca_printer or .elegoo_printer bundle and return paths to JSON configs.
        
        These bundle files are ZIP archives containing:
        - printer/[name].json
        - filament/[name].json
        - process/[name].json
        - bundle_structure.json
        
        Args:
            bundle_path: Path to .orca_printer or .elegoo_printer file
            
        Returns:
            List of paths to extracted JSON config files in order [printer, filament, process],
            or None if extraction fails
        """
        if not bundle_path.exists():
            logger.error(f"Bundle file not found: {bundle_path}")
            return None

        try:
            extract_dir = bundle_path.parent / f".{bundle_path.stem}_extracted"
            extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(bundle_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            logger.debug(f"Extracted bundle to: {extract_dir}")

            return self._extract_config_dir(extract_dir)

        except zipfile.BadZipFile:
            logger.error(f"Invalid bundle file (not a ZIP archive): {bundle_path}")
            return None
        except Exception as exc:
            logger.exception(f"Failed to extract bundle: {exc}")
            return None

    def _extract_config_dir(self, config_dir: Path) -> Optional[List[Path]]:
        printer_jsons = list((config_dir / "printer").glob("*.json")) if (config_dir / "printer").exists() else []
        filament_jsons = list((config_dir / "filament").glob("*.json")) if (config_dir / "filament").exists() else []
        process_jsons = list((config_dir / "process").glob("*.json")) if (config_dir / "process").exists() else []

        if not (printer_jsons and filament_jsons and process_jsons):
            logger.error(
                f"Bundle missing required configs: printer={len(printer_jsons)}, "
                f"filament={len(filament_jsons)}, process={len(process_jsons)}"
            )
            return None

        config_files = [
            printer_jsons[0],
            filament_jsons[0],
            process_jsons[0],
        ]

        logger.info(f"Extracted {len(config_files)} config files from bundle")
        logger.debug(f"  Printer: {config_files[0].name}")
        logger.debug(f"  Filament: {config_files[1].name}")
        logger.debug(f"  Process: {config_files[2].name}")

        return config_files

    def _load_json(self, path: Path) -> Optional[dict]:
        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception as exc:
            logger.warning(f"Failed to read JSON config {path}: {exc}")
            return None

    def _ensure_type(self, config_path: Path, expected_type: str) -> Path:
        data = self._load_json(config_path)
        if not data:
            return config_path

        existing_type = str(data.get("type", "")).lower()
        if existing_type:
            return config_path

        data["type"] = expected_type
        cache_path = self._cli_cache_dir / f"{config_path.stem}.cli.json"
        try:
            with cache_path.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
            return cache_path
        except Exception as exc:
            logger.warning(f"Failed to write CLI config cache {cache_path}: {exc}")
            return config_path

    def _ensure_layer_gcode(self, process_config: Path) -> Path:
        data = self._load_json(process_config)
        if not data:
            return process_config

        layer_gcode = str(data.get("layer_gcode", ""))
        if self._gcode_has_g92(layer_gcode):
            return process_config

        data["layer_gcode"] = (layer_gcode + "\nG92 E0\n").lstrip()
        cache_path = self._cli_cache_dir / f"{process_config.stem}.g92.cli.json"
        try:
            with cache_path.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
            return cache_path
        except Exception as exc:
            logger.warning(f"Failed to write CLI process cache {cache_path}: {exc}")
            return process_config

    def _ensure_machine_layer_gcode(self, machine_config: Path) -> Path:
        data = self._load_json(machine_config)
        if not data:
            return machine_config

        layer_gcode = str(data.get("layer_gcode", ""))
        if self._gcode_has_g92(layer_gcode):
            return machine_config

        data["layer_gcode"] = (layer_gcode + "\nG92 E0\n").lstrip()
        cache_path = self._cli_cache_dir / f"{machine_config.stem}.g92.cli.json"
        try:
            with cache_path.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
            return cache_path
        except Exception as exc:
            logger.warning(f"Failed to write CLI machine cache {cache_path}: {exc}")
            return machine_config

    def _ensure_process_compatibility(
        self,
        process_config: Path,
        printer_name: str,
        printer_settings_id: str,
        printer_inherits: str,
    ) -> Path:
        data = self._load_json(process_config)
        if not data:
            return process_config

        desired = [value for value in [printer_name, printer_settings_id, printer_inherits] if value]
        compatible = data.get("compatible_printers")
        if isinstance(compatible, list) and all(value in compatible for value in desired):
            return process_config

        data["compatible_printers"] = desired
        data["compatible_printers_condition"] = ""

        cache_path = self._cli_cache_dir / f"{process_config.stem}.compat.cli.json"
        try:
            with cache_path.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
            return cache_path
        except Exception as exc:
            logger.warning(f"Failed to write CLI compatibility cache {cache_path}: {exc}")
            return process_config

    def _gcode_has_g92(self, gcode: str) -> bool:
        return "G92 E0" in gcode.upper()

    def _needs_g92_fix(self, printer_config: Path, process_config: Optional[Path] = None) -> bool:
        printer_data = self._load_json(printer_config)
        if not printer_data:
            return False

        use_relative = str(printer_data.get("use_relative_e_distances", "0")).lower() in {"1", "true", "yes"}
        if not use_relative:
            gcode_flavor = str(printer_data.get("gcode_flavor", "")).lower()
            if not gcode_flavor:
                inherited_name = str(printer_data.get("inherits", "")).strip()
                inherited_path = self._find_machine_preset(inherited_name)
                inherited_data = self._load_json(inherited_path) if inherited_path else None
                gcode_flavor = str((inherited_data or {}).get("gcode_flavor", "")).lower()

            if gcode_flavor != "klipper":
                return False

        process_data = self._load_json(process_config) if process_config else None
        layer_gcode = (process_data or {}).get("layer_gcode", "")
        return not self._gcode_has_g92(layer_gcode or "")

    def _get_fix_layer_gcode_path(self) -> Optional[Path]:
        fix_path = Path(__file__).resolve().parent.parent.parent / "config" / "printers" / "fix_layer_gcode.json"
        return fix_path if fix_path.exists() else None

    def _build_preset_args(self) -> List[str]:
        preset_args: List[str] = []

        if not self.preset_path or not self.preset_path.exists():
            datadir_presets = self._get_datadir_presets()
            if not datadir_presets:
                return []

            machine_config, filament_config, process_config = datadir_presets
            logger.info("Using OrcaSlicer datadir presets for CLI slicing.")

            printer_config = self._ensure_type(machine_config, "machine")
            process_config = self._ensure_type(process_config, "process")
            filament_config = self._ensure_type(filament_config, "filament")

            printer_data = self._load_json(printer_config) or {}
            printer_name = str(printer_data.get("name", "")).strip()
            printer_settings_id = str(printer_data.get("printer_settings_id", "")).strip()
            printer_inherits = str(printer_data.get("inherits", "")).strip()
            if printer_name or printer_settings_id or printer_inherits:
                process_config = self._ensure_process_compatibility(
                    process_config,
                    printer_name,
                    printer_settings_id,
                    printer_inherits,
                )

            if self._needs_g92_fix(printer_config, process_config):
                printer_config = self._ensure_machine_layer_gcode(printer_config)
                process_config = self._ensure_layer_gcode(process_config)

            preset_args.extend(["--load-settings", ";".join(str(p) for p in [printer_config, process_config])])
            preset_args.extend(["--load-filaments", str(filament_config)])
            return preset_args

        if self.preset_path.is_dir():
            config_files = self._extract_config_dir(self.preset_path)
            if not config_files:
                return []

            printer_config, filament_config, process_config = config_files
            printer_config = self._ensure_type(printer_config, "machine")
            process_config = self._ensure_type(process_config, "process")
            filament_config = self._ensure_type(filament_config, "filament")

            printer_data = self._load_json(printer_config) or {}
            printer_name = str(printer_data.get("name", "")).strip()
            printer_settings_id = str(printer_data.get("printer_settings_id", "")).strip()
            printer_inherits = str(printer_data.get("inherits", "")).strip()
            if printer_name or printer_settings_id or printer_inherits:
                process_config = self._ensure_process_compatibility(
                    process_config,
                    printer_name,
                    printer_settings_id,
                    printer_inherits,
                )

            if self._needs_g92_fix(printer_config, process_config):
                printer_config = self._ensure_machine_layer_gcode(printer_config)
                process_config = self._ensure_layer_gcode(process_config)

            settings_files = [printer_config, process_config]

            preset_args.extend(["--load-settings", ";".join(str(p) for p in settings_files)])
            preset_args.extend(["--load-filaments", str(filament_config)])
            return preset_args

        if self.preset_path.suffix in [".orca_printer", ".elegoo_printer"]:
            config_files = self._extract_config_bundle(self.preset_path)
            if not config_files:
                return []

            printer_config, filament_config, process_config = config_files
            printer_config = self._ensure_type(printer_config, "machine")
            process_config = self._ensure_type(process_config, "process")
            filament_config = self._ensure_type(filament_config, "filament")

            if self._needs_g92_fix(printer_config, process_config):
                process_config = self._ensure_layer_gcode(process_config)

            settings_files = [printer_config, process_config]

            preset_args.extend(["--load-settings", ";".join(str(p) for p in settings_files)])
            preset_args.extend(["--load-filaments", str(filament_config)])
            return preset_args

        if self.preset_path.suffix == ".json":
            data = self._load_json(self.preset_path) or {}
            config_type = str(data.get("type", "")).lower()

            if config_type in {"filament", "filaments"}:
                return ["--load-filaments", str(self._ensure_type(self.preset_path, "filament"))]

            if config_type in {"machine", "printer", "process", "print"}:
                expected_type = "machine" if config_type in {"machine", "printer"} else "process"
                settings_files = [self._ensure_type(self.preset_path, expected_type)]
                if config_type in {"machine", "printer"} and self._needs_g92_fix(self.preset_path):
                    fix_path = self._get_fix_layer_gcode_path()
                    if fix_path and fix_path != self.preset_path:
                        settings_files.append(fix_path)
                return ["--load-settings", ";".join(str(p) for p in settings_files)]

        return []

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
        
        # Build command
        cmd = [
            str(self.orca_bin),
            "--slice", "0",  # 0 = slice all plates
            "--outputdir", str(output_dir),
        ]
        
        preset_args = self._build_preset_args()
        if preset_args:
            cmd.extend(preset_args)
        elif self.preset_path and self.preset_path.exists():
            logger.info(
                f"Preset '{self.preset_path.name}' could not be applied via CLI; using OrcaSlicer defaults."
            )
        
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
                gcode_files = sorted(output_dir.glob("*.gcode"), key=lambda p: p.stat().st_mtime, reverse=True)
                if gcode_files:
                    gcode_path = gcode_files[0]
                else:
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
        
        
            datadir = self._find_orca_datadir()
            if datadir:
                cmd.extend(["--datadir", str(datadir)])
        
            cmd.extend([
                "--slice", "0",  # 0 = slice all plates
                "--outputdir", str(output_dir),
            ])
        if errors:
            error_summary = "\n".join([f"  • {name}: {err}" for name, err in errors])
            raise RuntimeError(
                f"Failed to slice {len(errors)}/{len(stl_paths)} file(s):\n{error_summary}"
            )
        
        logger.info(f"✅ Successfully sliced {len(gcode_paths)} file(s)")
        return gcode_paths
