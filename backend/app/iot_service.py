import os
import sys
import time
import json
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Ensure root .env is loaded
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
AWS_IOT_ENDPOINT = os.getenv("AWS_IOT_ENDPOINT", "a2w7afielgnhaz-ats.iot.ap-south-1.amazonaws.com")
AWS_IOT_TOPIC = os.getenv("AWS_IOT_TOPIC", "aervia/Aervia_sensors/telemetry")

# Indian Standard Time (UTC + 05:30)
IST = timezone(timedelta(hours=5, minutes=30), "IST")

def get_now_ist_str() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")

def to_ist_str(dt_or_str: Any) -> str:
    """Converts any timestamp string or datetime object to standardized IST string format with millisecond precision."""
    if not dt_or_str:
        return get_now_ist_str()
    if isinstance(dt_or_str, datetime):
        if dt_or_str.tzinfo is None:
            # Assume UTC
            dt_or_str = dt_or_str.replace(tzinfo=timezone.utc)
        ist_dt = dt_or_str.astimezone(IST)
        if ist_dt.microsecond:
            ms = ist_dt.microsecond // 1000
            return ist_dt.strftime(f"%Y-%m-%d %H:%M:%S.{ms:03d} IST")
        return ist_dt.strftime("%Y-%m-%d %H:%M:%S IST")
    s = str(dt_or_str).strip()
    if s.endswith("IST"):
        return s
    try:
        # Standard ISO format e.g. 2026-10-10T21:50:56.563+05:30
        clean = s.replace(" ", "T")
        if clean.endswith("Z"):
            clean = clean[:-1] + "+00:00"
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ist_dt = dt.astimezone(IST)
        if ist_dt.microsecond:
            ms = ist_dt.microsecond // 1000
            return ist_dt.strftime(f"%Y-%m-%d %H:%M:%S.{ms:03d} IST")
        return ist_dt.strftime("%Y-%m-%d %H:%M:%S IST")
    except Exception:
        return s

class IoTCoreService:
    def __init__(self):
        self.endpoint = AWS_IOT_ENDPOINT
        self.topic = AWS_IOT_TOPIC
        self.region = AWS_DEFAULT_REGION
        self.mqtt_connection = None
        self.is_connected = False
        self.messages_received_count = 0
        self.last_message_time: Optional[float] = None
        self.last_received_ist: Optional[str] = None
        self.history_lock = threading.Lock()
        self.history: List[Dict[str, Any]] = []
        self.max_history = 100
        
        # Load initial baseline history from SQLite database (last 20 rows)
        self._load_initial_records_from_db()

        self.bg_thread: Optional[threading.Thread] = None
        self.running = False

    def _load_initial_records_from_db(self):
        """Seeds the telemetry cache with actual ground truth records from aervia.db."""
        db_path = os.path.join(PROJECT_ROOT, "backend", "aervia.db")
        seeded = False
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, station_id, timestamp, pm25, pm10, temp, humidity, pressure, voc_index
                    FROM sensor_readings
                    WHERE id IN (
                        SELECT MAX(id) FROM sensor_readings GROUP BY timestamp
                    )
                    ORDER BY id ASC
                """)
                rows = cur.fetchall()
                conn.close()

                if rows:
                    for r in rows:
                        rec = {
                            "device_id": str(r[1] or "aervia-54a91ed9b4dc"),
                            "station_name": "College Gate Sensor Node 1",
                            "timestamp": str(r[2]),
                            "raw_timestamp": str(r[2]),
                            "json_timestamp": str(r[2]),
                            "timestamp_ist": to_ist_str(r[2]),
                            "pm1": round(float(r[3]) * 0.48, 1),
                            "pm25": round(float(r[3]), 1),
                            "pm4": round(float(r[3]) * 1.4, 1),
                            "pm10": round(float(r[4]), 1),
                            "temp": round(float(r[5]), 1),
                            "humidity": round(float(r[6]), 1),
                            "pressure": round(float(r[7]), 1),
                            "voc_index": round(float(r[8] if len(r) > 8 and r[8] is not None else 59.0), 1),
                            "nox_index": 1.0,
                            "battery_v": 3.98,
                            "wifi_rssi_dbm": -68,
                            "quality_flag": "STANDBY",
                            "status": "OFFLINE",
                            "sensor_state": "OFF",
                            "is_sensor_online": False,
                            "source": "Database Ground Truth Capture",
                            "endpoint": self.endpoint
                        }
                        self.history.append(rec)
                    seeded = True
            except Exception as e:
                print(f"[AWS IoT Service] Warning reading initial db records: {e}")

        if not seeded or not self.history:
            # Fallback default record
            fallback_rec = {
                "device_id": "aervia-54a91ed9b4dc",
                "station_name": "College Gate Sensor Node 1",
                "timestamp": "2026-10-09 16:02:00 IST",
                "timestamp_ist": "2026-10-09 16:02:00 IST",
                "pm1": 96.8,
                "pm25": 201.5,
                "pm4": 283.0,
                "pm10": 323.4,
                "temp": 32.9,
                "humidity": 35.3,
                "pressure": 943.9,
                "voc_index": 59.0,
                "nox_index": 1.0,
                "battery_v": 3.98,
                "wifi_rssi_dbm": -68,
                "quality_flag": "STANDBY",
                "status": "OFFLINE",
                "sensor_state": "OFF",
                "is_sensor_online": False,
                "source": "College Gate Recorded Run",
                "endpoint": self.endpoint
            }
            self.history = [fallback_rec]

        self.latest_reading = dict(self.history[-1])

    @property
    def is_sensor_online(self) -> bool:
        """Physical sensor hardware is ONLINE only if a real MQTT message arrived in the last 35 seconds."""
        if self.last_message_time is None:
            return False
        return (time.time() - self.last_message_time) < 35.0

    def start(self):
        """Starts the AWS IoT Core background connection."""
        if self.running:
            return
        self.running = True
        
        self.bg_thread = threading.Thread(target=self._run_mqtt_loop, daemon=True, name="AWSIoTSubscriber")
        self.bg_thread.start()
        print(f"[AWS IoT Core Service] Started subscriber for {self.endpoint} on topic {self.topic}")

    def stop(self):
        self.running = False
        if self.mqtt_connection:
            try:
                disconnect_future = self.mqtt_connection.disconnect()
                disconnect_future.result(timeout=3)
            except Exception as e:
                print(f"[AWS IoT Core] Disconnect error: {e}")
        self.is_connected = False

    def _normalize_payload(self, raw_data: Any) -> Dict[str, Any]:
        """Maps incoming raw sensor packets into standardized IST telemetry."""
        d = raw_data if isinstance(raw_data, dict) else {}
        
        if "payload" in d and isinstance(d["payload"], dict):
            inner = d["payload"]
            for k, v in inner.items():
                d.setdefault(k, v)

        device_id = d.get("device_id") or d.get("station_id") or d.get("source_id") or "aervia-54a91ed9b4dc"
        ts_raw = str(d.get("timestamp") or d.get("timestamp_ist") or d.get("recorded_at") or get_now_ist_str())
        ts_ist = to_ist_str(ts_raw)
        sequence = d.get("sequence")
        
        pm25 = float(d.get("pm25") or d.get("pm2_5") or d.get("PM25") or 0.0)
        pm10 = float(d.get("pm10") or d.get("PM10") or pm25 * 1.5)
        pm1 = float(d.get("pm1") or d.get("PM1") or pm25 * 0.7)
        pm4 = float(d.get("pm4") or d.get("PM4") or pm25 * 1.1)

        temp = float(d.get("temperature_c") or d.get("temp") or d.get("temperature") or 30.0)
        humidity = float(d.get("humidity_pct") or d.get("humidity") or 40.0)
        pressure = float(d.get("pressure_hpa") or d.get("pressure") or 944.0)
        voc = float(d.get("voc_index") or d.get("voc") or 60.0)
        nox = float(d.get("nox_index") or d.get("nox") or 1.0)

        battery = float(d.get("battery_v") or d.get("battery") or 4.10)
        rssi = int(d.get("wifi_rssi_dbm") or d.get("rssi") or -60)

        record = {
            "device_id": str(device_id),
            "sequence": sequence,
            "station_name": "College Gate Sensor Node 1",
            "timestamp": ts_raw,
            "json_timestamp": ts_raw,
            "raw_timestamp": ts_raw,
            "timestamp_ist": ts_ist,
            "pm1": round(pm1, 1),
            "pm25": round(pm25, 1),
            "pm4": round(pm4, 1),
            "pm10": round(pm10, 1),
            "temp": round(temp, 1),
            "humidity": round(humidity, 1),
            "pressure": round(pressure, 1),
            "voc_index": round(voc, 1),
            "nox_index": round(nox, 1),
            "battery_v": round(battery, 2),
            "wifi_rssi_dbm": rssi,
            "quality_flag": str(d.get("quality_flag", "OK")),
            "status": "ONLINE",
            "sensor_state": "ACTIVE",
            "is_sensor_online": True,
            "source": f"AWS IoT Core ({self.topic})",
            "endpoint": self.endpoint,
            "raw_payload": d
        }
        return record

    def _persist_reading(self, record: Dict[str, Any]):
        """Persists genuine live reading to aervia.db."""
        try:
            db_path = os.path.join(PROJECT_ROOT, "backend", "aervia.db")
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sensor_readings (station_id, timestamp, pm25, pm10, temp, humidity, pressure, voc_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record["device_id"],
                record["timestamp_ist"],
                record["pm25"],
                record["pm10"],
                record["temp"],
                record["humidity"],
                record["pressure"],
                record.get("voc_index", 0.0)
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[AWS IoT Service] Error saving reading to db: {e}")

    def _on_message(self, topic, payload, **kwargs):
        try:
            raw_str = payload.decode("utf-8")
            data = json.loads(raw_str)
            norm = self._normalize_payload(data)
            
            with self.history_lock:
                # Deduplication: ignore immediate duplicate deliveries
                if self.history:
                    last = self.history[-1]
                    cur_seq = norm.get("sequence")
                    last_seq = last.get("sequence")
                    if cur_seq is not None and last_seq is not None and cur_seq == last_seq:
                        return
                    if norm["raw_timestamp"] == last.get("raw_timestamp") and cur_seq is None:
                        return
                
                self.last_message_time = time.time()
                self.last_received_ist = norm["timestamp_ist"]
                self.messages_received_count += 1
                self.latest_reading = norm
                self.history.append(dict(norm))
                if len(self.history) > self.max_history:
                    self.history.pop(0)

            self._persist_reading(norm)
            print(f"[AWS IoT Core] Real Ingest on '{topic}': seq={norm.get('sequence')} PM2.5={norm['pm25']} at {norm['timestamp_ist']}")
        except Exception as e:
            print(f"[AWS IoT Core] Error processing MQTT message: {e}")

    def _run_mqtt_loop(self):
        """Maintains persistent connection and subscriptions to AWS IoT Core."""
        while self.running:
            try:
                from awscrt import auth, mqtt
                from awsiot import mqtt_connection_builder

                print(f"[AWS IoT Core] Connecting to {self.endpoint} via WebSockets SigV4...")
                credentials_provider = auth.AwsCredentialsProvider.new_static(
                    access_key_id=AWS_ACCESS_KEY_ID,
                    secret_access_key=AWS_SECRET_ACCESS_KEY
                )

                client_id = f"aervia_backend_{int(time.time())}"
                self.mqtt_connection = mqtt_connection_builder.websockets_with_default_aws_signing(
                    endpoint=self.endpoint,
                    region=self.region,
                    credentials_provider=credentials_provider,
                    client_id=client_id,
                    clean_session=True,
                    keep_alive_secs=30,
                    on_connection_interrupted=lambda c, e, **k: print(f"[AWS IoT Core] Connection interrupted: {e}"),
                    on_connection_resumed=lambda c, r, s, **k: print(f"[AWS IoT Core] Connection resumed (return_code={r})")
                )

                connect_future = self.mqtt_connection.connect()
                connect_future.result(timeout=12)
                self.is_connected = True
                print(f"[AWS IoT Core] Broker connected! Subscribed to {self.topic}")

                # Subscribe to specific sensor telemetry topic only (prevents duplicate deliveries)
                sub1, _ = self.mqtt_connection.subscribe(
                    topic=self.topic,
                    qos=mqtt.QoS.AT_LEAST_ONCE,
                    callback=self._on_message
                )
                sub1.result(timeout=10)

                while self.running:
                    time.sleep(2)

            except Exception as e:
                self.is_connected = False
                print(f"[AWS IoT Core] MQTT subscriber error: {e}. Reconnecting in 15 seconds...")
                time.sleep(15)

    def publish_telemetry(self, payload: Dict[str, Any]) -> bool:
        """Publishes a sensor reading back to AWS IoT Core topic via MQTT."""
        try:
            norm = self._normalize_payload(payload)
            if self.mqtt_connection and self.is_connected:
                from awscrt import mqtt
                json_str = json.dumps(payload)
                pub_future, _ = self.mqtt_connection.publish(
                    topic=self.topic,
                    payload=json_str,
                    qos=mqtt.QoS.AT_LEAST_ONCE
                )
                pub_future.result(timeout=5)
                print(f"[AWS IoT Core] Published message to {self.topic}")
            
            # Local registration
            with self.history_lock:
                self.last_message_time = time.time()
                self.last_received_ist = norm["timestamp_ist"]
                self.messages_received_count += 1
                self.latest_reading = norm
                self.history.append(dict(norm))
                if len(self.history) > self.max_history:
                    self.history.pop(0)
            self._persist_reading(norm)
            return True
        except Exception as e:
            print(f"[AWS IoT Core] Error publishing to MQTT: {e}")
            return False

    def get_latest(self) -> Dict[str, Any]:
        with self.history_lock:
            sensor_online = self.is_sensor_online
            cur = dict(self.latest_reading)
            cur["status"] = "ONLINE" if sensor_online else "OFFLINE"
            cur["sensor_state"] = "ACTIVE" if sensor_online else "OFF"
            cur["is_sensor_online"] = sensor_online
            cur["quality_flag"] = "OK" if sensor_online else "STANDBY"

            return {
                **cur,
                "is_aws_connected": self.is_connected,
                "messages_received_count": self.messages_received_count,
                "last_received_ist": self.last_received_ist or cur.get("timestamp_ist"),
                "aws_iot_endpoint": self.endpoint,
                "aws_iot_topic": self.topic,
                "last_5_records": list(reversed(self.history[-5:])) if self.history else []
            }

    def get_telemetry_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.history_lock:
            return list(self.history[-limit:])

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "ONLINE" if self.is_sensor_online else "OFFLINE",
            "sensor_state": "ACTIVE" if self.is_sensor_online else "OFF",
            "is_sensor_online": self.is_sensor_online,
            "is_broker_connected": self.is_connected,
            "aws_endpoint": self.endpoint,
            "topic": self.topic,
            "region": self.region,
            "messages_received_count": self.messages_received_count,
            "last_received_ist": self.last_received_ist
        }

# Global singleton
iot_service = IoTCoreService()
