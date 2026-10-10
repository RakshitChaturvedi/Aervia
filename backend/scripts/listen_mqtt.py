import os
import sys
import time
import json
from dotenv import load_dotenv
from awscrt import io, http, auth
from awsiot import mqtt_connection_builder

# Load .env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
load_dotenv(env_path)

access_key = os.getenv('AWS_ACCESS_KEY_ID')
secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
region = os.getenv('AWS_DEFAULT_REGION', 'ap-south-1')
endpoint = 'a2w7afielgnhaz-ats.iot.ap-south-1.amazonaws.com'
topic = 'aervia/Aervia_sensors/telemetry'

received_messages = []

def on_connection_interrupted(connection, error, **kwargs):
    print(f"Connection interrupted. error: {error}")

def on_connection_resumed(connection, return_code, session_present, **kwargs):
    print(f"Connection resumed. return_code: {return_code} session_present: {session_present}")

def on_message_received(topic, payload, dup, qos, retain, **kwargs):
    raw = payload.decode('utf-8')
    print(f"\n>>> [RECEIVED MQTT MESSAGE ON '{topic}']:\n{raw}\n")
    try:
        data = json.loads(raw)
        received_messages.append(data)
    except Exception:
        received_messages.append(raw)

print(f"Connecting to AWS IoT Core ({endpoint}) via WebSockets SigV4...")

credentials_provider = auth.AwsCredentialsProvider.new_static(
    access_key_id=access_key,
    secret_access_key=secret_key
)

mqtt_connection = mqtt_connection_builder.websockets_with_default_aws_signing(
    endpoint=endpoint,
    region=region,
    credentials_provider=credentials_provider,
    client_id="aervia_test_listener_" + str(int(time.time())),
    clean_session=True,
    keep_alive_secs=30,
    on_connection_interrupted=on_connection_interrupted,
    on_connection_resumed=on_connection_resumed
)

connect_future = mqtt_connection.connect()
connect_future.result(timeout=10)
print(f"Connected successfully! Subscribing to topic: {topic} and 'aervia/#'...")

from awscrt import io, http, auth, mqtt

# Subscribe to both exact topic and wildcard
sub_future1, packet_id1 = mqtt_connection.subscribe(
    topic=topic,
    qos=mqtt.QoS.AT_LEAST_ONCE,
    callback=on_message_received
)
sub_future1.result(timeout=10)

sub_future2, packet_id2 = mqtt_connection.subscribe(
    topic="aervia/#",
    qos=mqtt.QoS.AT_LEAST_ONCE,
    callback=on_message_received
)
sub_future2.result(timeout=10)

print(f"Listening for incoming sensor telemetry for 15 seconds...")
start = time.time()
while time.time() - start < 15:
    time.sleep(1)
    if len(received_messages) >= 2:
        break

print(f"Finished listening. Total messages captured: {len(received_messages)}")
if received_messages:
    print(f"Sample Payload Structure: {json.dumps(received_messages[0], indent=2)}")
else:
    print("No messages arrived within the 15-second window.")

disconnect_future = mqtt_connection.disconnect()
disconnect_future.result(timeout=5)
print("Disconnected cleanly.")
