import paramiko
import os

HOST = "101.79.21.231"
USER = "root"
PASSWORD = "P4!dL4qEy?bd"
REMOTE_DIR = "/root/infinite_bot"
LOCAL_DIR = "/Users/choo/.gemini/antigravity/scratch/infinite_buying_v4"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD)
ftp = ssh.open_sftp()

files_to_upload = [
    "domain/models.py",
    "services/persistence.py",
    "services/scheduler.py",
    "services/notifier.py",
    "strategy/infinite_buying_v4.py",
    "strategy/state_machine.py",
    "app.py",
    "static/index.html",
    "static/app.js"
]

for file_path in files_to_upload:
    local_path = os.path.join(LOCAL_DIR, file_path)
    remote_path = f"{REMOTE_DIR}/{file_path}"
    print(f"Uploading {local_path} -> {remote_path}")
    ftp.put(local_path, remote_path)

ftp.close()

# Restart the server on remote
print("Restarting uvicorn on remote...")
_, out, _ = ssh.exec_command("tmux capture-pane -t infinite -p")
ssh.exec_command("tmux send-keys -t infinite C-c")
import time
time.sleep(2)
ssh.exec_command("tmux send-keys -t infinite 'pkill -f uvicorn' Enter")
time.sleep(2)
ssh.exec_command("tmux send-keys -t infinite 'nohup uvicorn app:app --host 0.0.0.0 --port 8081 > logs/app.log 2>&1 &' Enter")
time.sleep(2)

print("Deployment complete.")
ssh.close()
