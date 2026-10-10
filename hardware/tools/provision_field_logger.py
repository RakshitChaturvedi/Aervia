"""Provision credentials over local USB; no key contents are logged or committed."""
import argparse,json,time
from pathlib import Path
import serial
p=argparse.ArgumentParser()
p.add_argument('--port',default='/dev/cu.usbmodem1101')
p.add_argument('--key-file')
p.add_argument('--wifi-file',required=True)
p.add_argument('--initialize-storage',action='store_true',help='Initialize unmounted internal logging partition; never format a mounted partition')
a=p.parse_args();cfg=json.loads(Path(a.wifi_file).read_text())
if a.key_file:
 key=json.loads(Path(a.key_file).read_text())
 if key.get('type')!='service_account':raise SystemExit('Expected service-account JSON')
 cfg.update({k:key[k] for k in ('client_email','private_key')})
 print('Provisioning account:',key['client_email'])
packet=('@CONFIG '+json.dumps(cfg,separators=(',',':'))+'\n').encode()
if len(packet)>8000:raise SystemExit('Configuration too large')
with serial.Serial(a.port,115200,timeout=.2,write_timeout=5) as ser:
 time.sleep(1);ser.reset_input_buffer()
 replies=[]
 def drain():
  while ser.in_waiting:
   line=ser.readline().decode(errors='replace').strip()
   if line.startswith(('CONFIG_','STORAGE_')):replies.append(line)
 def send(packet):
  for i in range(0,len(packet),48):ser.write(packet[i:i+48]);time.sleep(.20);drain()
 if a.initialize_storage:
  send(b'@FORMAT\n');deadline=time.monotonic()+35;ready=False
  while time.monotonic()<deadline:
   line=replies.pop(0) if replies else ser.readline().decode(errors='replace').strip()
   if line.startswith(('STORAGE_READY','STORAGE_ALREADY_READY')):ready=True;print(line);break
   if line.startswith('STORAGE_INIT_FAILED'):raise SystemExit(line)
  if not ready:raise SystemExit('No storage confirmation; configuration not sent')
 send(packet);deadline=time.monotonic()+15
 while time.monotonic()<deadline:
  line=replies.pop(0) if replies else ser.readline().decode(errors='replace').strip()
  if line.startswith('CONFIG_SAVED'):print(line);break
  if line.startswith('CONFIG_ERROR'):raise SystemExit(line)
 else:raise SystemExit('No configuration acknowledgement')
