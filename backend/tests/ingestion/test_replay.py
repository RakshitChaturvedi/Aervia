import json

import pytest

from src.ingestion import JsonlRawStore
from src.ingestion.mqtt_consumer import MQTTIngestionConsumer
from src.ingestion.replay import iter_messages, replay_directory


def test_replay_routes_all_jsonl_streams(tmp_path):
    inp = tmp_path / "input"
    inp.mkdir()
    ts = "2026-10-08T08:00:00+00:00"
    rows = {
        "sensor": {"timestamp": ts, "source_id": "gate-01", "pm25": 30, "sequence": 1, "boot_id": "b"},
        "activity": {"timestamp": ts, "source_id": "observer-01", "bus_event": "idling"},
        "weather": {"timestamp": ts, "source_id": "weather-01", "wind_speed_ms": 2},
        "reference": {"timestamp": ts, "source_id": "feed", "station_id": "station-01", "pm25": 22},
    }
    for stream, row in rows.items():
        (inp / f"{stream}.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

    store = JsonlRawStore(tmp_path / "raw")
    summary = replay_directory(inp, MQTTIngestionConsumer(store))
    assert (summary.attempted, summary.accepted, summary.duplicates, summary.rejected) == (4, 4, 0, 0)
    for stream in rows:
        assert len((tmp_path / f"raw/{stream}/{stream}.jsonl").read_text().splitlines()) == 1


def test_replay_tsv_live_export_keeps_missing_timestamp(tmp_path):
    path = tmp_path / "live.txt"
    path.write_text(
        "sequence\ttimestamp_ist\tdevice_id\tboot_id\tpm2_5_ug_m3\tquality_flag\n"
        "1\t2026-10-09T14:24:46+05:30\tdev\tb1\t22.4\tok\n"
        "2\t\tdev\tb1\t23.1\treview\n",
        encoding="utf-8",
    )
    assert len(list(iter_messages(path))) == 2
    store = JsonlRawStore(tmp_path / "raw")
    summary = replay_directory(path, MQTTIngestionConsumer(store))
    assert summary.accepted == 2 and summary.rejected == 0
    rows = [json.loads(line) for line in (tmp_path / "raw/sensor/sensor.jsonl").read_text().splitlines()]
    assert sorted(row["pm25"] for row in rows) == [22.4, 23.1]
    assert next(row for row in rows if row["pm25"] == 23.1)["timestamp"] is None


def test_timestamp_in_pressure_is_quarantined_not_reassigned(tmp_path):
    path = tmp_path / "bad_pressure.csv"
    path.write_text(
        "sequence,timestamp_ist,device_id,boot_id,pm2_5_ug_m3,pressure_hpa,quality_flag,quality_flags\n"
        '1,,dev,b1,18.58,2026-10-09T14:33:18.878+05:30,review,"[\"clock_unsynced\"]"\n',
        encoding="utf-8",
    )
    messages = list(iter_messages(path))
    payload = messages[0][1]["payload"]
    assert payload["timestamp_ist"] is None
    assert payload["pressure_hpa"] is None
    assert payload["quality_flag"] == "review"
    assert "invalid_pressure_field" in payload["quality_flags"]
    assert payload["_raw_csv_row"]["pressure_hpa"] == "2026-10-09T14:33:18.878+05:30"

    store = JsonlRawStore(tmp_path / "raw")
    summary = replay_directory(path, MQTTIngestionConsumer(store))
    assert summary.accepted == 1 and summary.rejected == 0
    stored = json.loads((tmp_path / "raw/sensor/sensor.jsonl").read_text().splitlines()[0])
    assert stored["timestamp"] is None and stored["pressure_hpa"] is None
    assert stored["raw_payload"]["_raw_csv_row"]["pressure_hpa"].startswith("2026-")


def test_replay_continues_after_invalid_record_and_counts_reject(tmp_path):
    path = tmp_path / "rows.csv"
    path.write_text(
        "sequence,timestamp_ist,device_id,boot_id,pm2_5_ug_m3,pressure_hpa\n"
        "1,2026-10-09T14:24:46+05:30,dev,b1,22.4,944.7\n"
        "2,2026-10-09T14:24:47+05:30,dev,b1,23.1,not-a-number\n"
        "3,2026-10-09T14:24:48+05:30,dev,b1,24.1,944.8\n",
        encoding="utf-8",
    )
    store = JsonlRawStore(tmp_path / "raw")
    summary = replay_directory(path, MQTTIngestionConsumer(store))
    assert summary.attempted == 3
    assert summary.accepted == 2
    assert summary.rejected == 1
    assert summary.duplicates == 0
    assert len((tmp_path / "raw/sensor/sensor.jsonl").read_text().splitlines()) == 2
    assert "ValidationError" in summary.errors[0]


def test_duplicate_packet_counted_separately(tmp_path):
    path = tmp_path / "duplicates.csv"
    path.write_text(
        "sequence,timestamp_ist,device_id,boot_id,pm2_5_ug_m3\n"
        "1,2026-10-09T14:24:46+05:30,dev,b1,22.4\n"
        "1,2026-10-09T14:24:46+05:30,dev,b1,22.4\n",
        encoding="utf-8",
    )
    summary = replay_directory(path, MQTTIngestionConsumer(JsonlRawStore(tmp_path / "raw")))
    assert summary.attempted == 2
    assert summary.accepted == 1
    assert summary.duplicates == 1
    assert summary.rejected == 0


def test_replay_orders_timed_rows_but_keeps_untimed_first(tmp_path):
    path = tmp_path / "ordered.csv"
    path.write_text(
        "sequence,timestamp_ist,device_id,boot_id,pm2_5_ug_m3\n"
        "1,,dev,b1,30\n"
        "3,2026-10-08T08:00:02+00:00,dev,b1,20\n"
        "2,2026-10-08T08:00:01+00:00,dev,b1,10\n",
        encoding="utf-8",
    )
    messages = list(iter_messages(path))
    assert [message[1]["payload"]["sequence"] for message in messages] == ["1", "2", "3"]


def test_malformed_jsonl_line_is_counted_and_does_not_stop_replay(tmp_path):
    inp = tmp_path / "input"
    inp.mkdir()
    (inp / "sensor.jsonl").write_text(
        '{"timestamp":"2026-10-08T08:00:00+00:00","source_id":"g","pm25":20,"sequence":1,"boot_id":"b"}\n'
        '{not-json}\n'
        '{"timestamp":"2026-10-08T08:00:02+00:00","source_id":"g","pm25":22,"sequence":2,"boot_id":"b"}\n',
        encoding="utf-8",
    )
    summary = replay_directory(inp, MQTTIngestionConsumer(JsonlRawStore(tmp_path / "raw")))
    assert summary.attempted == 3
    assert summary.accepted == 2
    assert summary.rejected == 1


def test_missing_stream_directory_fails_clearly(tmp_path):
    with pytest.raises(FileNotFoundError):
        list(iter_messages(tmp_path / "empty"))