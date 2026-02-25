import os
import subprocess
import sys

# 운영 서버 정보
SSH_CMD = r'C:\Windows\System32\OpenSSH\ssh.exe'
SCP_CMD = r'C:\Windows\System32\OpenSSH\scp.exe'
HOST = "admin@100.75.72.6"
REMOTE_PATH = "~/projects/biz-retriever/scripts/setup_security.sh"

def run_command(cmd):
    print(f"Executing: {' '.join(cmd)}")
    # Use shell=True for complex commands on Windows if needed, 
    # but direct list is safer for SSH
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        print(f"❌ Command failed with code {result.returncode}")
        return False
    return True

def main():
    print("🚀 Deploying Security Hardening Script...")
    
    # 1. Copy script to remote
    print("📦 Uploading setup_security.sh...")
    scp_cmd = [SCP_CMD, "scripts/setup_security.sh", f"{HOST}:{REMOTE_PATH}"]
    if not run_command(scp_cmd):
        return

    # 2. Make executable and run with sudo
    print("🛡️ Running security setup on remote (Password required for sudo)...")
    # We use -t to allow interactive sudo password entry if needed
    ssh_cmd = [SSH_CMD, "-t", HOST, f"chmod +x {REMOTE_PATH} && sudo {REMOTE_PATH}"]
    
    if run_command(ssh_cmd):
        print("\n✅ Security Hardening successfully applied to remote server!")
        print("Note: If you were disconnected, please reconnect. UFW is now active.")
    else:
        print("\n❌ Failed to apply security hardening.")

if __name__ == "__main__":
    main()
