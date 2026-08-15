import socket
import paramiko

hosts = ['185.199.52.85', 'skinsurance.tech', '2a02:4780:12:aa78::1']
ports = [22, 2222, 80, 443]

for h in hosts:
    for p in ports:
        try:
            s = socket.create_connection((h, p), timeout=3)
            print(f"Connection to {h}:{p} SUCCESSFUL")
            s.close()
        except Exception as e:
            print(f"Connection to {h}:{p} FAILED: {e}")
