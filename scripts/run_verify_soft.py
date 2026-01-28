import subprocess
import os
import sys

# Windows SSH path (adjusted based on previous findings)
SSH_CMD = r'C:\Windows\System32\OpenSSH\ssh.exe'
HOST = "admin@100.75.72.6"

def run_ssh(cmd_str):
    full_cmd = [SSH_CMD, HOST, cmd_str]
    subprocess.run(full_cmd, check=True)

def deploy_script():
    local_path = 'scripts/verify_soft_match.py'
    remote_path = '/tmp/verify_soft_match.py'
    
    with open(local_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"Deploying {local_path}...")
    cmd = [SSH_CMD, HOST, f'cat > {remote_path}']
    
    try:
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(input=content.encode('utf-8'))
        
        if process.returncode != 0:
            print(f"Deploy failed: {stderr.decode('utf-8')}")
            sys.exit(1)
        print("Deploy success.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def execute_remote():
    print("Executing verification script inside container...")
    # 1. Copy to container
    run_ssh("docker cp /tmp/verify_soft_match.py biz-retriever-api:/app/scripts/verify_soft_match.py")
    
    # 2. Execute
    run_ssh("docker exec biz-retriever-api python scripts/verify_soft_match.py")

if __name__ == "__main__":
    deploy_script()
    execute_remote()
