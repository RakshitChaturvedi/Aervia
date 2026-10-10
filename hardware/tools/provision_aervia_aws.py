"""Validate local AWS files and provision over USB without printing secrets."""
import argparse,json,re,time
from pathlib import Path
from datetime import datetime,timezone
import serial
from cryptography import x509
from cryptography.hazmat.primitives import serialization
p=argparse.ArgumentParser()
p.add_argument('--endpoint',help='Omit to stage credentials while awaiting the endpoint')
p.add_argument('--certificate',required=True)
p.add_argument('--private-key',required=True)
p.add_argument('--port',default='/dev/cu.usbmodem1101')
p.add_argument('--validate-only',action='store_true')
a=p.parse_args()
if a.endpoint and not re.fullmatch(r'[a-zA-Z0-9-]+-ats\.iot\.ap-south-1\.amazonaws\.com',a.endpoint):
 p.error('Expected an ATS data endpoint in ap-south-1, without https:// or a port')
cert_bytes=Path(a.certificate).read_bytes();key_bytes=Path(a.private_key).read_bytes()
cert=x509.load_pem_x509_certificate(cert_bytes)
key=serialization.load_pem_private_key(key_bytes,password=None)
def public_bytes(k):
 return k.public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
if public_bytes(cert.public_key())!=public_bytes(key.public_key()):
 p.error('Certificate and private key do not match')
now=datetime.now(timezone.utc)
if not cert.not_valid_before_utc<=now<cert.not_valid_after_utc:
 p.error('Certificate is outside its validity dates')
print('Certificate/key match and validity dates checked. AWS activation/policy still need remote verification.')
if a.validate_only:raise SystemExit(0)
config={'certificate':cert_bytes.decode('ascii'),'private_key':key_bytes.decode('ascii')}
if a.endpoint:config['endpoint']=a.endpoint
command=b'@AWS '+json.dumps(config,separators=(',',':')).encode()+b'\n'
if len(command)>8100:p.error('Credentials exceed USB provisioning command capacity')
with serial.Serial(a.port,115200,timeout=.1) as s:
 s.reset_input_buffer();buffer=bytearray();ack=False
 def consume():
  global ack
  buffer.extend(s.read(s.in_waiting or 1))
  while b'\n' in buffer:
   line,_,rest=buffer.partition(b'\n');buffer[:]=rest
   if line.startswith(b'AWS_CONFIG_'):
    status=line.decode(errors='replace').strip();print(status)
    if status.startswith('AWS_CONFIG_ERROR'):raise SystemExit('Provisioning failed')
    if status.startswith('AWS_CONFIG_SAVED'):ack=True
 for offset in range(0,len(command),48):
  s.write(command[offset:offset+48]);s.flush();time.sleep(.02);consume()
 deadline=time.monotonic()+15
 while not ack and time.monotonic()<deadline:consume()
 if not ack:raise SystemExit('No provisioning acknowledgment; do not assume configuration saved')
print('Configuration saved. '+('Device restarted.' if a.endpoint else 'Awaiting endpoint; device was not restarted.'))
