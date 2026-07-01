#!/bin/bash
# deploy.sh
# 원격 서버(네이버 클라우드)에서 Git을 통해 최신 코드를 가져오고 봇을 재시작합니다.

echo "Pulling latest code from GitHub..."
git pull origin main

echo "Installing requirements..."
./venv/bin/pip install -r requirements.txt

echo "Killing existing uvicorn processes..."
pkill -f uvicorn

echo "Starting uvicorn in background..."
nohup ./venv/bin/uvicorn app:app --host 0.0.0.0 --port 8081 > app.log 2>&1 &

echo "Deployment complete."
