"""
Fetch STL files from a model URL (Printables, Thingiverse), optionally from zip.
Saves files under a unique job_id directory for downstream processing (e.g. slicer).
"""
import json
import logging
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import uuid

import httpx

logger = logging.getLogger(__name__)

# Constants
FILES_PRINTABLES_BASE = "https://files.printables.com"
PRINTABLES_FILES_PAGE = "https://www.printables.com/model/{model_id}/files"
DEFAULT_JOBS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "jobs"
DEFAULT_STL_FILENAME = "file.stl"
HTTP_TIMEOUT_SHORT = 30.0
HTTP_TIMEOUT_LONG = 60.0
USER_AGENT = "Your3DPrintingBot/1.0 (3D print job fetcher)"


def _model_id_from_printables_url(url: str) -> str | None:
    """Extract Printables model id from URL like .../model/285921-... or .../model/285921/files."""
    m = re.search(r"printables\.com/model/(\d+)", url, re.IGNORECASE)
    return m.group(1) if m else None


def _parse_printables_stls_from_html(html: str) -> list[dict[str, Any]]:
    """Extract stls array from Printables /files page embedded JSON."""
    # Page embeds escaped JSON (backslash-quote); avoid matching "stls" in URL paths
    json_key = '\\"stls\\":'
    idx = html.find(json_key)
    if idx == -1:
        return []
    start = html.find("[", idx)
    if start == -1:
        return []
    depth = 0
    for i in range(start, min(start + 20000, len(html))):
        c = html[i]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                raw = html[start : i + 1]
                raw = raw.replace('\\"', '"').replace('\\/', "/")
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return []
                break
    return []


def _printables_stl_download_url(file_preview_path: str, file_name: str) -> str:
    """Build direct STL download URL from filePreviewPath and file name.
    Server expects filename derived from preview basename (e.g. dhtcasetoppins_preview.png -> dhtcasetoppins.stl).
    """
    if not file_preview_path:
        return ""
    dir_part = str(Path(file_preview_path).parent).replace("\\", "/")
    # Derive server filename: preview is .../something_preview.png -> STL is .../something.stl
    base = Path(file_preview_path).stem
    if base.endswith("_preview"):
        server_name = base[:-8] + ".stl"
    else:
        server_name = file_name if file_name else DEFAULT_STL_FILENAME
    return f"{FILES_PRINTABLES_BASE}/{dir_part}/{server_name}"


async def fetch_printables_stl_list(model_id: str) -> list[dict[str, Any]]:
    """Fetch Printables /files page and return list of STL file info (name, filePreviewPath, etc.)."""
    url = PRINTABLES_FILES_PAGE.format(model_id=model_id)
    async with httpx.AsyncClient(follow_redirects=True, timeout=HTTP_TIMEOUT_SHORT) as client:
        response = await client.get(
            url,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
    stls = _parse_printables_stls_from_html(response.text)
    return [s for s in stls if (s.get("name") or "").lower().endswith(".stl")]


async def download_file(client: httpx.AsyncClient, url: str, dest: Path) -> None:
    """Download a single file to dest."""
    response = await client.get(url)
    response.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(response.content)


def _safe_filename(name: str) -> str:
    """Sanitize filename for local storage."""
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip() or DEFAULT_STL_FILENAME


def _generate_job_id(user_id: int, jobs_dir: Path | None = None) -> str:
    """
    Generate structured job ID: yyyy.mm.dd-userid-increment.
    
    Args:
        user_id: Telegram user ID
        jobs_dir: Directory where jobs are stored
    
    Returns:
        Job ID string in format: 2026.02.16-123456-001
    """
    jobs_dir = jobs_dir or DEFAULT_JOBS_DIR
    today = datetime.now().strftime("%Y.%m.%d")
    prefix = f"{today}-{user_id}-"
    
    # Find existing jobs for this user today
    if jobs_dir.exists():
        existing = list(jobs_dir.glob(f"{prefix}*"))
        if existing:
            # Extract increment numbers and find max
            increments = []
            for job_dir in existing:
                try:
                    # Extract the increment part (last component after last dash)
                    parts = job_dir.name.split("-")
                    if len(parts) >= 3:
                        increments.append(int(parts[-1]))
                except (ValueError, IndexError):
                    continue
            next_increment = max(increments) + 1 if increments else 1
        else:
            next_increment = 1
    else:
        next_increment = 1
    
    return f"{prefix}{next_increment:03d}"


async def fetch_and_save_printables(
    model_url: str,
    user_id: int | None = None,
    job_id: str | None = None,
    jobs_dir: Path | None = None,
) -> tuple[str, list[Path]]:
    """
    Fetch all STL files for a Printables model URL and save under a job directory.

    Args:
        model_url: Printables model URL
        user_id: Telegram user ID (required for structured job IDs)
        job_id: Optional explicit job ID (if not provided, generates structured ID)
        jobs_dir: Optional jobs directory path

    Returns:
        (job_id, list of paths to saved .stl files)
    """
    jobs_dir = jobs_dir or DEFAULT_JOBS_DIR
    
    if job_id is None:
        if user_id is None:
            # Fallback to UUID if no user_id provided
            job_id = str(uuid.uuid4())
        else:
            job_id = _generate_job_id(user_id, jobs_dir)
    
    job_dir = jobs_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    model_id = _model_id_from_printables_url(model_url)
    if not model_id:
        raise ValueError(f"Could not extract Printables model id from URL: {model_url}")

    stl_list = await fetch_printables_stl_list(model_id)
    if not stl_list:
        raise ValueError(f"No STL files found for Printables model {model_id}")

    saved_stls: list[Path] = []
    async with httpx.AsyncClient(follow_redirects=True, timeout=HTTP_TIMEOUT_LONG) as client:
        for info in stl_list:
            name = info.get("name") or DEFAULT_STL_FILENAME
            preview_path = info.get("filePreviewPath") or ""
            url = _printables_stl_download_url(preview_path, name)
            if not url:
                logger.warning("Skipping STL with no URL: %s", name)
                continue
            safe_name = _safe_filename(name)
            dest = job_dir / safe_name
            try:
                await download_file(client, url, dest)
                saved_stls.append(dest)
                logger.info("Downloaded %s -> %s", name, dest)
            except httpx.HTTPError as e:
                logger.warning("Failed to download %s: %s", url, e)

    return job_id, saved_stls


def unzip_stls_from_path(zip_path: Path, out_dir: Path) -> list[Path]:
    """Extract all .stl files from a zip into out_dir. Returns list of extracted .stl paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if name.lower().endswith(".stl"):
                safe = _safe_filename(Path(name).name)
                target = out_dir / safe
                target.write_bytes(zf.read(name))
                extracted.append(target)
    return extracted


async def fetch_model_files(
    model_url: str,
    user_id: int | None = None,
    job_id: str | None = None,
    jobs_dir: Path | None = None,
) -> tuple[str, list[Path]]:
    """
    Fetch STL files from a supported model URL (Printables; Thingiverse TBD).
    If the source provides a zip, it is downloaded, unzipped, and STLs are saved.
    Otherwise STL files are downloaded individually.

    Args:
        model_url: URL to the model
        user_id: Telegram user ID (for structured job IDs)
        job_id: Optional explicit job ID
        jobs_dir: Optional jobs directory path

    Returns:
        (job_id, list of paths to .stl files in the job directory)
    """
    parsed = urlparse(model_url)
    netloc = (parsed.netloc or "").lower()
    if "printables.com" in netloc:
        return await fetch_and_save_printables(model_url, user_id=user_id, job_id=job_id, jobs_dir=jobs_dir)
    if "thingiverse.com" in netloc:
        raise NotImplementedError("Thingiverse fetcher not implemented yet")
    raise ValueError(f"Unsupported model URL: {model_url}")
