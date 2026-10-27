"""
File-backed store for regime generations.
Each generation lives in generations/<id>/ with report.md, plot.png and meta.json.
The id is derived from the request parameters, so identical requests are served
from disk instead of re-running the model.
"""

import json
import re
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.regime_hmm.pipeline import run_analysis, PLOT_FILENAME, REPORT_FILENAME
from src.regime_hmm.options import OPTIONS_PLOT_FILENAME

BACKEND_DIR = Path(__file__).resolve().parents[1]
GENERATIONS_DIR = BACKEND_DIR / "generations"
MODELS_DIR = BACKEND_DIR / "models"
META_FILENAME = "meta.json"
# Images a generation may serve to the frontend
IMAGE_FILENAMES = {PLOT_FILENAME, OPTIONS_PLOT_FILENAME}

TICKER_RE = re.compile(r"^[A-Z0-9.\-^=]{1,15}$")

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()

def make_id(ticker: str, start_date: str, end_date: str, fat_tail: bool, max_regimes: int, switch_cost: float = 0.0) -> str:
    model = "fat" if fat_tail else "gaussian"
    # Suffix only when set, so ids of existing zero-cost generations stay valid
    suffix = f"_s{switch_cost:g}" if switch_cost else ""
    return f"{ticker}_{start_date}_{end_date}_{model}_m{max_regimes}{suffix}"

def _gen_dir(gen_id: str) -> Optional[Path]:
    """Resolves a generation directory, rejecting ids that escape the store."""
    if not gen_id or gen_id.startswith(".") or "/" in gen_id or "\\" in gen_id:
        return None
    path = GENERATIONS_DIR / gen_id
    return path if path.parent == GENERATIONS_DIR else None

def _lock_for(gen_id: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(gen_id, threading.Lock())

def get_generation(gen_id: str) -> Optional[dict]:
    path = _gen_dir(gen_id)
    if path is None or not (path / META_FILENAME).exists():
        return None
    meta = json.loads((path / META_FILENAME).read_text(encoding="utf-8"))
    markdown = (path / REPORT_FILENAME).read_text(encoding="utf-8")
    return {"meta": meta, "markdown": markdown}

def image_path(gen_id: str, filename: str) -> Optional[Path]:
    path = _gen_dir(gen_id)
    if path is None or filename not in IMAGE_FILENAMES or not (path / filename).exists():
        return None
    return path / filename

def delete_generation(gen_id: str) -> bool:
    """Removes a generation folder. Returns False if it doesn't exist."""
    path = _gen_dir(gen_id)
    if path is None:
        return False
    # Take the generation lock so a delete can't interleave with a run for the same id
    with _lock_for(gen_id):
        if not (path / META_FILENAME).exists():
            return False
        shutil.rmtree(path)
    return True

def list_generations() -> list[dict]:
    if not GENERATIONS_DIR.exists():
        return []
    metas = []
    for meta_file in GENERATIONS_DIR.glob(f"*/{META_FILENAME}"):
        if meta_file.parent.name.startswith("."):
            continue
        metas.append(json.loads(meta_file.read_text(encoding="utf-8")))
    return sorted(metas, key=lambda m: m["created_at"], reverse=True)

def generate(ticker: str, start_date: str, end_date: str, max_regimes: int = 3, fat_tail: bool = False, switch_cost: float = 0.0) -> tuple[dict, bool]:
    """Returns (generation, cached). Runs the pipeline only if no matching generation exists."""
    gen_id = make_id(ticker, start_date, end_date, fat_tail, max_regimes, switch_cost)

    # Serialize identical requests so a double-click can't run the model twice
    with _lock_for(gen_id):
        existing = get_generation(gen_id)
        if existing is not None:
            return existing, True

        final_dir = GENERATIONS_DIR / gen_id
        tmp_dir = GENERATIONS_DIR / f".tmp-{gen_id}"
        shutil.rmtree(tmp_dir, ignore_errors=True)

        try:
            summary = run_analysis(
                ticker=ticker, start_date=start_date, end_date=end_date,
                max_regimes=max_regimes, fat_tail=fat_tail, switch_cost=switch_cost,
                out_dir=str(tmp_dir), base_dir=str(BACKEND_DIR),
            )
            meta = {
                "id": gen_id,
                "ticker": ticker,
                "start_date": start_date,
                "end_date": end_date,
                "max_regimes": max_regimes,
                "fat_tail": fat_tail,
                "switch_cost": switch_cost,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "regimes": summary["regimes"],
                "current_regime": summary["current_regime"],
                "observations": summary["observations"],
                "legacy": False,
            }
            (tmp_dir / META_FILENAME).write_text(json.dumps(meta, indent=2), encoding="utf-8")
            # Report paths were written relative to the tmp dir; point them at the final location
            report = tmp_dir / REPORT_FILENAME
            report.write_text(report.read_text(encoding="utf-8").replace(tmp_dir.name, gen_id), encoding="utf-8")
            tmp_dir.rename(final_dir)
        except Exception:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise

    return get_generation(gen_id), False

# --- Legacy import -----------------------------------------------------------

def _md_field(pattern: str, text: str) -> Optional[str]:
    match = re.search(pattern, text)
    return match.group(1) if match else None

def import_legacy_reports() -> list[str]:
    """Moves pre-API reports from models/*.md (and their plots) into the generation store."""
    imported = []
    for md_file in sorted(MODELS_DIR.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        ticker = _md_field(r"\*\*Ticker Symbol\*\* \| `([^`]+)`", text)
        dates = re.search(r"\*\*Analysis Range\*\* \| `([^`]+)` to `([^`]+)`", text)
        max_regimes = _md_field(r"\*\*Prior Upper Bound Regimes\*\* \| `(\d+)`", text)
        image = re.search(r"!\[([^\]]*)\]\(([^)]+\.png)\)", text)
        if not (ticker and dates and max_regimes and image):
            print(f"Skipping legacy report {md_file.name}: could not parse header")
            continue

        fat_tail = "Student's t" in text
        start_date, end_date = dates.group(1), dates.group(2)
        gen_id = make_id(ticker, start_date, end_date, fat_tail, int(max_regimes))
        target = GENERATIONS_DIR / gen_id
        if target.exists():
            continue

        src_plot = MODELS_DIR / image.group(2)
        if not src_plot.exists():
            print(f"Skipping legacy report {md_file.name}: plot {src_plot.name} not found")
            continue

        generated = _md_field(r"\*\*Generated:\*\* (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", text)
        current = _md_field(r"\*\*Current Identified Regime\*\* \| \*\*Regime (\d+)\*\*", text)
        observations = _md_field(r"\*\*Total Trading Observations\*\* \| `([\d,]+)`", text)
        regimes = sorted({int(r) for r in re.findall(r"\| \*\*Regime (\d+)\*\* \|", text)})

        target.mkdir(parents=True)
        shutil.move(str(src_plot), target / PLOT_FILENAME)
        text = text.replace(image.group(0), f"![{image.group(1)}]({PLOT_FILENAME})")
        (target / REPORT_FILENAME).write_text(text, encoding="utf-8")
        meta = {
            "id": gen_id,
            "ticker": ticker,
            "start_date": start_date,
            "end_date": end_date,
            "max_regimes": int(max_regimes),
            "fat_tail": fat_tail,
            "created_at": datetime.strptime(generated, "%Y-%m-%d %H:%M:%S").isoformat() if generated else datetime.fromtimestamp(md_file.stat().st_mtime).isoformat(timespec="seconds"),
            "regimes": regimes,
            "current_regime": int(current) if current is not None else None,
            "observations": int(observations.replace(",", "")) if observations else None,
            "legacy": True,
        }
        (target / META_FILENAME).write_text(json.dumps(meta, indent=2), encoding="utf-8")
        md_file.unlink()
        imported.append(gen_id)
    return imported
