import socket
import json
import sys

HOST = '0.0.0.0'
PORT = 5000

try:
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except (socket.error):
  sys.stderr.write("[ERROR] %s\n" )
  sys.exit(1)

try:
  sock.connect((HOST, PORT))
except (socket.error):
  sys.stderr.write("[ERROR] %s\n" )
  sys.exit(2)

msg = {'@message': 'python test message', '@tags': ['python', 'test']}

sock.send(json.dumps(msg))

sock.close()
sys.exit(0)