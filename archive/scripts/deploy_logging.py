import subprocess
import os
import sys

# Windows SSH path
SSH_CMD = r'C:\Windows\System32\OpenSSH\ssh.exe'
HOST = "admin@100.75.72.6"
REMOTE_PROJECT_DIR = "~/projects/biz-retriever"

def run_ssh(cmd_str):
    full_cmd = [SSH_CMD, HOST, cmd_str]
    subprocess.run(full_cmd, check=True)

def deploy_file(local_path, remote_path):
    if not os.path.exists(local_path):
        print(f"❌ Error: {local_path} not found")
        sys.exit(1)

    with open(local_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"Deploying {local_path} -> {remote_path}...")
    # Use tee for safe overwrite
    cmd = [SSH_CMD, HOST, f'cat > {remote_path}']
    
    try:
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        stdout, stderr = process.communicate(input=content)
        
        if process.returncode != 0:
            print(f"❌ Deploy failed: {stderr}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def main():
    print("🚀 Deploying Logging Update...")
    
    # 1. Update logging.py on host
    deploy_file('app/core/logging.py', f'{REMOTE_PROJECT_DIR}/app/core/logging.py')

    # 2. Restart API and Worker to apply changes
    print("\n🔄 Restarting API and Worker...")
    run_ssh(f"cd {REMOTE_PROJECT_DIR} && docker compose restart api celery-worker")
        
    print("\n✅ Logging Update Deployed!")

if __name__ == "__main__":
    main()
