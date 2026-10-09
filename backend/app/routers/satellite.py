"""
Satellite NO₂ Overlay Router
Fetches live NO₂ concentration data from Open-Meteo CAMS Air Quality API,
generates a color-mapped RGBA heatmap PNG, and serves it to the frontend
for deck.gl BitmapLayer overlay on the live map.

Supports: Delhi, Hyderabad, Bengaluru (extensible via CITY_BOUNDS).
Caching: 1-hour disk cache per city to avoid hammering the external API.
"""

import io
import os
import time
import json
import hashlib
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import requests
from PIL import Image, ImageFilter, ImageChops
from fastapi import APIRouter, Query, Response
from fastapi.responses import Response as FastAPIResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["satellite"])

# ── City Bounding Boxes: [west_lon, south_lat, east_lon, north_lat] ──
CITY_BOUNDS: dict[str, list[float]] = {
    "Delhi":     [76.84, 28.40, 77.35, 28.88],
    "Hyderabad": [78.20, 17.20, 78.65, 17.60],
    "Bengaluru": [77.40, 12.80, 77.80, 13.15],
}

# Grid resolution: number of sample points along each axis
GRID_SIZE = 12

# Output image resolution (upscaled from GRID_SIZE × GRID_SIZE)
IMG_SIZE = 512

# Cache duration in seconds (1 hour)
CACHE_TTL = 3600

# Cache directory
CACHE_DIR = Path(__file__).resolve().parent.parent / "satellite_cache"
CACHE_DIR.mkdir(exist_ok=True)

# Open-Meteo CAMS Air Quality API endpoint
OPEN_METEO_AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


_edge_mask = None

def get_edge_mask(size: int) -> Image.Image:
    """Generate a smooth elliptical falloff mask that guarantees zero opacity at the edges."""
    global _edge_mask
    if _edge_mask is None or _edge_mask.size != (size, size):
        y, x = np.ogrid[:size, :size]
        center = (size - 1) / 2.0
        
        # Normalized distance from center (0.0 at center, 1.0 at outer edge)
        nx = (x - center) / center
        ny = (y - center) / center
        dist = np.sqrt(nx**2 + ny**2)
        
        # Smooth cosine falloff starting from 30% radius out to 88% radius
        fade_start = 0.30
        fade_end = 0.88
        
        t = np.clip((dist - fade_start) / (fade_end - fade_start), 0.0, 1.0)
        # Cosine smooth curve (1.0 at center -> 0.0 at edge)
        alpha = 0.5 * (1.0 + np.cos(np.pi * t))
        alpha[dist >= fade_end] = 0.0
        
        _edge_mask = Image.fromarray((alpha * 255).astype(np.uint8), "L")
    return _edge_mask


def _grid_to_png(grid: np.ndarray) -> bytes:
    """Convert a GRID_SIZE × GRID_SIZE NO₂ grid into a realistic, organic satellite heatmap PNG."""

    # CAMS cells are ~10–40 km, so Hyderabad/Bengaluru often have a tiny range
    # (a few µg/m³). Stretch that local contrast so the cloud is visible, while
    # still using absolute concentration for overall opacity (Delhi stays denser).
    valid_vals = grid[np.isfinite(grid) & (grid > 0)]
    if len(valid_vals) == 0:
        min_val, max_val, mean_val = 5.0, 50.0, 5.0
    else:
        min_val = float(np.min(valid_vals))
        max_val = float(np.max(valid_vals))
        mean_val = float(np.mean(valid_vals))
        if max_val - min_val < 2.0:
            max_val = min_val + 2.0

    span = max_val - min_val + 1e-5
    abs_scale = float(np.clip(mean_val / 20.0, 0.85, 1.0))

    # 2. Build RGBA array from grid
    grid_h, grid_w = grid.shape
    rgba_grid = np.zeros((grid_h, grid_w, 4), dtype=np.uint8)

    for y in range(grid_h):
        for x in range(grid_w):
            val = float(grid[y, x])
            if val <= 0:
                continue

            rel = min(max((val - min_val) / span, 0.0), 1.0)
            # Faint city-wide haze + brighter local maxima (no fully-clear core)
            lifted = 0.28 + 0.72 * rel
            alpha = int((lifted ** 1.2) * 230 * abs_scale)
            alpha = max(alpha, 40)

            # Atmospheric Colormap: Deep Indigo -> Electric Violet -> Hot Magenta -> Bright Sun/White
            if rel < 0.35:
                s = rel / 0.35
                r = int(55 + s * 125)
                g = int(12 + s * 25)
                b = int(130 + s * 65)
            elif rel < 0.75:
                s = (rel - 0.35) / 0.40
                r = int(180 + s * 75)
                g = int(37 + s * 55)
                b = int(195 - s * 65)
            else:
                s = (rel - 0.75) / 0.25
                r = 255
                g = int(92 + s * 155)
                b = int(130 + s * 110)

            rgba_grid[y, x] = (min(r, 255), min(g, 255), min(b, 255), min(alpha, 255))

    small_img = Image.fromarray(rgba_grid, "RGBA")

    # 3. High-resolution bicubic upscaling (512x512)
    large_img = small_img.resize((IMG_SIZE, IMG_SIZE), Image.BICUBIC)

    # 4. Multi-stage Gaussian plume diffusion for realistic gas dispersion
    diffuse = large_img.filter(ImageFilter.GaussianBlur(radius=20))
    core = large_img.filter(ImageFilter.GaussianBlur(radius=7))
    blended = Image.blend(diffuse, core, alpha=0.5)

    # 5. Elliptical feathering mask to remove all rectangular borders
    mask = get_edge_mask(IMG_SIZE)
    r, g, b, a = blended.split()
    feathered_a = ImageChops.multiply(a, mask)
    final_img = Image.merge("RGBA", (r, g, b, feathered_a))

    # Save optimized PNG to bytes
    buf = io.BytesIO()
    final_img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _fetch_no2_grid(city: str) -> Optional[np.ndarray]:
    """Fetch a GRID_SIZE × GRID_SIZE array of current NO₂ values (µg/m³)
    from the Open-Meteo CAMS Air Quality API for the given city."""

    bounds = CITY_BOUNDS.get(city)
    if not bounds:
        return None

    west, south, east, north = bounds

    # Create evenly spaced grid points
    lats = np.linspace(south, north, GRID_SIZE)
    lons = np.linspace(west, east, GRID_SIZE)

    # Build comma-separated coordinate lists for multi-point query
    lat_list = []
    lon_list = []
    for lat in lats:
        for lon in lons:
            lat_list.append(f"{lat:.4f}")
            lon_list.append(f"{lon:.4f}")

    try:
        resp = requests.get(
            OPEN_METEO_AQ_URL,
            params={
                "latitude": ",".join(lat_list),
                "longitude": ",".join(lon_list),
                "current": "nitrogen_dioxide",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Open-Meteo API error for {city}: {e}")
        return None

    # Parse response: list of dicts, each with .current.nitrogen_dioxide
    if not isinstance(data, list):
        data = [data]

    grid = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.float32)
    for idx, point in enumerate(data):
        row = idx // GRID_SIZE
        col = idx % GRID_SIZE
        try:
            val = point.get("current", {}).get("nitrogen_dioxide")
            grid[row, col] = val if val is not None else 0.0
        except (KeyError, TypeError):
            grid[row, col] = 0.0

    # Flip vertically: row 0 should be south (bottom of image)
    # but BitmapLayer expects image top = north
    grid = np.flipud(grid)

    return grid


CACHE_VERSION = "v2"


def _get_cache_path(city: str) -> Path:
    """Return the filesystem path for a cached satellite image."""
    return CACHE_DIR / f"no2_{city.lower()}_{CACHE_VERSION}.png"


def _get_cache_meta_path(city: str) -> Path:
    """Return the filesystem path for cache metadata."""
    return CACHE_DIR / f"no2_{city.lower()}_{CACHE_VERSION}.json"


def _is_cache_valid(city: str) -> bool:
    """Check if the cached image exists and is less than CACHE_TTL old."""
    meta_path = _get_cache_meta_path(city)
    if not meta_path.exists():
        return False
    try:
        with open(meta_path, "r") as f:
            meta = json.load(f)
        return (time.time() - meta.get("timestamp", 0)) < CACHE_TTL
    except Exception:
        return False


def _write_cache(city: str, png_bytes: bytes, bounds: list[float]):
    """Write the generated PNG and metadata to disk cache."""
    cache_path = _get_cache_path(city)
    meta_path = _get_cache_meta_path(city)
    with open(cache_path, "wb") as f:
        f.write(png_bytes)
    with open(meta_path, "w") as f:
        json.dump({"timestamp": time.time(), "bounds": bounds}, f)


def _read_cache(city: str) -> Optional[bytes]:
    """Read cached PNG bytes from disk."""
    cache_path = _get_cache_path(city)
    if cache_path.exists():
        with open(cache_path, "rb") as f:
            return f.read()
    return None


@router.get("/satellite/no2")
async def get_no2_overlay(city: str = Query("Delhi", description="City name: Delhi, Hyderabad, or Bengaluru")):
    """Return a live NO₂ heatmap PNG overlay for the specified city.

    The image is a 256×256 RGBA PNG generated from the Open-Meteo CAMS
    Air Quality API. It is cached for 1 hour on disk.

    Response headers include:
    - X-Bounds: JSON array [west, south, east, north] for deck.gl BitmapLayer
    - X-Cache: HIT or MISS
    """
    bounds = CITY_BOUNDS.get(city)
    if not bounds:
        return Response(
            content=json.dumps({"error": f"Unknown city: {city}. Supported: {list(CITY_BOUNDS.keys())}"}),
            status_code=400,
            media_type="application/json",
        )

    # Check cache first
    if _is_cache_valid(city):
        png_bytes = _read_cache(city)
        if png_bytes:
            return Response(
                content=png_bytes,
                media_type="image/png",
                headers={
                    "X-Bounds": json.dumps(bounds),
                    "X-Cache": "HIT",
                    "Cache-Control": f"public, max-age={CACHE_TTL}",
                },
            )

    # Fetch fresh data from Open-Meteo
    grid = _fetch_no2_grid(city)
    if grid is None:
        # If API fails, try serving stale cache
        png_bytes = _read_cache(city)
        if png_bytes:
            return Response(
                content=png_bytes,
                media_type="image/png",
                headers={
                    "X-Bounds": json.dumps(bounds),
                    "X-Cache": "STALE",
                    "Cache-Control": "public, max-age=300",
                },
            )
        return Response(
            content=json.dumps({"error": "Failed to fetch NO₂ data and no cache available."}),
            status_code=502,
            media_type="application/json",
        )

    # Generate PNG
    png_bytes = _grid_to_png(grid)

    # Write to cache
    _write_cache(city, png_bytes, bounds)

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "X-Bounds": json.dumps(bounds),
            "X-Cache": "MISS",
            "Cache-Control": f"public, max-age={CACHE_TTL}",
        },
    )
