import paramiko

HOST = "101.79.21.231"
USER = "root"
PASSWORD = "P4!dL4qEy?bd"

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)
    
    stdin, stdout, stderr = ssh.exec_command("tail -n 200 /root/infinite_bot/app.log")
    print(stdout.read().decode())
    
    ssh.close()
except Exception as e:
    print(f"SSH Error: {e}")
