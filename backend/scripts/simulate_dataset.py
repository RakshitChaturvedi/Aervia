"""Generate a deterministic, physically plausible Aervia development dataset.

The simulator is NOT a scientific sensor model. It creates controlled test
conditions so downstream preprocessing and analytics can be tested before the
real ESP32/SPS30/BME280 data is available.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def gaussian(t: float, center: float, width: float, amplitude: float) -> float:
    return amplitude * math.exp(-0.5 * ((t - center) / width) ** 2)


def build_dataset(start: datetime, seconds: int, seed: int = 42) -> dict[str, list[dict]]:
    # A tiny deterministic PRNG avoids requiring numpy for the simulator.
    state = seed

    def noise(scale: float) -> float:
        nonlocal state
        state = (1664525 * state + 1013904223) % (2**32)
        unit = state / (2**32 - 1)
        return (unit * 2.0 - 1.0) * scale

    sensor: list[dict] = []
    activity: list[dict] = []
    weather: list[dict] = []
    reference: list[dict] = []

    # Event centers in seconds from start. These are deliberately obvious so
    # event detection can later be validated against known ground truth.
    events = [
        (35 * 60, 18.0, 6 * 60),
        (85 * 60, 30.0, 8 * 60),
    ]

    for i in range(seconds):
        ts = start + timedelta(seconds=i)
        minute = i / 60.0

        # Smooth outdoor background plus measurement noise.
        daily = 3.0 * math.sin(2 * math.pi * minute / 180.0)
        background = 24.0 + daily
        event_excess = sum(
            gaussian(i, center, width, amplitude) for center, amplitude, width in events
        )
        pm25 = max(1.0, background + event_excess + noise(0.7))
        pm10 = max(pm25 + 5.0 + noise(1.0), pm25)
        pm1 = max(0.5, pm25 * 0.55 + noise(0.4))
        pm4 = max(pm25 * 0.82 + noise(0.6), pm25)

        temperature = 27.0 + 2.5 * math.sin(2 * math.pi * minute / 180.0) + noise(0.08)
        humidity = 68.0 - 9.0 * math.sin(2 * math.pi * minute / 180.0) + noise(0.3)
        pressure = 1008.0 + noise(0.15)

        sensor.append(
            {
                "timestamp": ts.isoformat(),
                "source_id": "gate-node-01",
                "stream": "sensor",
                "pm1": round(pm1, 3),
                "pm25": round(pm25, 3),
                "pm4": round(pm4, 3),
                "pm10": round(pm10, 3),
                "particle_count": round(900 + pm25 * 25 + noise(15), 2),
                "typical_particle_size": round(1.2 + pm25 / 120 + noise(0.02), 3),
                "temperature_c": round(temperature, 3),
                "humidity_pct": round(humidity, 3),
                "pressure_hpa": round(pressure, 3),
                "voc_index": round(100 + event_excess * 0.8 + noise(2), 2),
                "nox_index": round(40 + event_excess * 0.5 + noise(1.5), 2),
                "battery_pct": round(99.0 - i / max(seconds, 1) * 2.0, 3),
                "signal_dbm": round(-58 + noise(3), 2),
                "restart_count": 0,
                "packet_seq": i + 1,
                "health": "ok",
            }
        )

        # Weather is sampled once per minute, not once per second.
        if i % 60 == 0:
            wind = 1.2 + 0.7 * math.sin(2 * math.pi * minute / 120.0) + noise(0.05)
            direction = (135.0 + 35.0 * math.sin(2 * math.pi * minute / 240.0)) % 360
            weather.append(
                {
                    "timestamp": ts.isoformat(),
                    "source_id": "sim-weather",
                    "stream": "weather",
                    "temperature_c": round(temperature, 3),
                    "humidity_pct": round(humidity, 3),
                    "pressure_hpa": round(pressure, 3),
                    "wind_speed_ms": round(max(0.0, wind), 3),
                    "wind_direction_deg": round(direction, 2),
                }
            )

            regional_pm = 20.0 + 2.0 * math.sin(2 * math.pi * minute / 240.0) + noise(0.2)
            reference.append(
                {
                    "timestamp": ts.isoformat(),
                    "source_id": "sim-reference-station",
                    "stream": "reference",
                    "station_id": "reference-01",
                    "pm25": round(max(0.0, regional_pm), 3),
                    "pm10": round(max(0.0, regional_pm + 7 + noise(0.3)), 3),
                    "no2": round(18.0 + noise(0.5), 3),
                    "source_timestamp": ts.isoformat(),
                }
            )

    # Activity is sparse and event-driven, matching a human observation log.
    activity_events = [
        (30 * 60, "bus", 2, "arrival", "bus-07", "high", 90, False, False, False, "two buses entering"),
        (33 * 60, "bus", 2, "idling", "bus-07", "high", 105, False, False, False, "one bus idling at queue"),
        (40 * 60, "bus", 1, "departure", "bus-07", "medium", 55, False, False, False, "bus queue clearing"),
        (80 * 60, "bus", 3, "arrival", "bus-11", "high", 130, False, False, False, "heavy arrival period"),
        (84 * 60, "bus", 3, "idling", "bus-11", "high", 140, True, False, False, "dust observed near queue"),
        (96 * 60, "bus", 1, "departure", "bus-11", "medium", 60, False, False, False, "queue clearing"),
    ]
    for offset, vehicle_class, count, bus_event, bus_id, crowd, pedestrians, dust, sweeping, construction, notes in activity_events:
        if offset < seconds:
            activity.append(
                {
                    "timestamp": (start + timedelta(seconds=offset)).isoformat(),
                    "source_id": "observer-gate-01",
                    "stream": "activity",
                    "vehicle_class": vehicle_class,
                    "vehicle_count": count,
                    "bus_event": bus_event,
                    "bus_id": bus_id,
                    "crowd_level": crowd,
                    "pedestrian_count": pedestrians,
                    "dust": dust,
                    "sweeping": sweeping,
                    "construction": construction,
                    "notes": notes,
                }
            )

    return {
        "sensor": sensor,
        "activity": activity,
        "weather": weather,
        "reference": reference,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a deterministic Aervia test dataset")
    parser.add_argument("--output", default="data/simulated/input", help="Output directory")
    parser.add_argument("--minutes", type=int, default=120, help="Duration of sensor simulation")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    start = datetime(2026, 10, 8, 8, 0, 0, tzinfo=UTC)
    dataset = build_dataset(start, args.minutes * 60, args.seed)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    for stream, rows in dataset.items():
        write_jsonl(output / f"{stream}.jsonl", rows)

    metadata = {
        "dataset_id": "aervia-simulated-gate-v1",
        "start": start.isoformat(),
        "duration_minutes": args.minutes,
        "seed": args.seed,
        "ground_truth_event_centers_seconds": [2100, 5100],
        "note": "Synthetic development data only; not a real sensor measurement.",
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Generated {args.minutes} minutes of synthetic sensor data in {output}")
    for stream, rows in dataset.items():
        print(f"  {stream:10s}: {len(rows):6d} records")


if __name__ == "__main__":
    main()