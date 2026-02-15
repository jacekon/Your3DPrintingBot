# Downloads component

Fetches STL files from supported model URLs (Printables; Thingiverse planned) and saves them under a unique **job ID** for downstream processing (e.g. slicer).

## Behaviour

- **Input:** Model page URL (e.g. `https://www.printables.com/model/285921-...`).
- **Output:** `(job_id, list[Path])` — a UUID job id and paths to saved `.stl` files.
- **Storage:** Files are written under `data/jobs/<job_id>/`. Each STL keeps a safe filename derived from the model.

## Supported sites

### Printables

- Parses the `/files` page HTML and extracts the embedded JSON `stls` array.
- Builds direct download URLs to `files.printables.com` (filename derived from preview path).
- Downloads each STL and saves it in the job directory.
- Some entries may have no `filePreviewPath` in the page; those are skipped.

### Thingiverse

- Not implemented yet (`fetch_model_files` raises `NotImplementedError` for thingiverse.com).

## Zip support

- If a source provides a single zip of all files, the component can download it and call `unzip_stls_from_path(zip_path, out_dir)` to extract only `.stl` files.
- Currently only direct STL URLs are used for Printables.

## Usage

```python
from src.downloads.fetcher import fetch_model_files

job_id, stl_paths = await fetch_model_files(
    "https://www.printables.com/model/285921-wifi-climate-sensor-enclosure-for-esp32-or-esp8266"
)
# job_id is a UUID string; stl_paths are Path objects under data/jobs/<job_id>/
```

## Test

```bash
python scripts/test_fetch_stl.py
```

Uses the WiFi climate sensor enclosure model and prints the job id and saved STL paths.
