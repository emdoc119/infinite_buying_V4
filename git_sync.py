import os
import subprocess
import paramiko
import time

HOST = "101.79.21.231"
USER = "root"
PASSWORD = "P4!dL4qEy?bd"

def run_local(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if result.stdout: print(result.stdout.strip())
    if result.stderr: print(result.stderr.strip())
    return result.returncode == 0

def main():
    print("===========================================")
    print(" 🚀 V4 시스템 원클릭 동기화 및 자동 배포 시작")
    print("===========================================")

    print("\n1. 로컬 코드 변경사항 확인 및 GitHub 푸시 중...")
    run_local("git add .")
    
    # Check if there's anything to commit
    res = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if res.stdout.strip():
        run_local("git commit -m 'Auto-update'")
        
    print("\nPushing to origin...")
    if not run_local("git push origin main"):
        print("❌ GitHub 푸시 실패. 로컬 인증을 확인해주세요.")
        return
    print("✅ GitHub 푸시 성공!")

    print("\n2. 원격 서버 접속 및 deploy.sh 실행 중...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)
        
        stdin, stdout, stderr = ssh.exec_command("cd /root/infinite_bot && chmod +x deploy.sh && ./deploy.sh")
        # Wait for the command to finish and print output line by line
        exit_status = stdout.channel.recv_exit_status()
        
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if out: print(out)
        if err: print(f"Error: {err}")
            
        if exit_status == 0:
            print("\n===========================================")
            print(" 🎉 원격 배포 및 봇 재구동이 정상적으로 완료되었습니다!")
            print("===========================================")
        else:
            print(f"\n❌ 원격 배포 스크립트 실행 중 에러가 발생했습니다. (Exit code: {exit_status})")
            
        ssh.close()
    except Exception as e:
        print(f"\n❌ 원격 서버 접속 실패: {e}")

if __name__ == '__main__':
    main()
