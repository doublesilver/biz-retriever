import subprocess
import os

HOST = "admin@100.75.72.6"

def deploy_file(local_path, remote_path):
    if not os.path.exists(local_path):
        print(f"Error: {local_path} not found")
        return

    with open(local_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Use full path to ssh to avoid 'Open with' dialog issues
    ssh_cmd = r'C:\Windows\System32\OpenSSH\ssh.exe' 
    cmd = [ssh_cmd, HOST, f'cat > {remote_path}']
    
    print(f"Deploying {local_path} to {remote_path}...")
    try:
        # Popen to pipe input
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(input=content.encode('utf-8'))
        
        if process.returncode != 0:
            print(f"Failed to deploy {local_path}: {stderr.decode('utf-8')}")
        else:
            print(f"Successfully uploaded {local_path}")
            
    except Exception as e:
        print(f"Exception during deployment: {e}")

# 1. Deploy Files to /tmp
deploy_file('app/main.py', '/tmp/main.py')
deploy_file('frontend/js/dashboard.js', '/tmp/dashboard.js')

# 2. Docker Copy & Restart
docker_cmd = (
    "docker cp /tmp/main.py biz-retriever-api:/app/app/main.py && "
    "docker cp /tmp/dashboard.js biz-retriever-frontend:/usr/share/nginx/html/js/dashboard.js && "
    "docker compose -f ~/projects/biz-retriever/docker-compose.pi.yml restart api && "
    "echo 'DEPLOYMENT_FINISHED'"
)

print("Applying changes to containers...")
cmd = [r'C:\Windows\System32\OpenSSH\ssh.exe', HOST, docker_cmd]
subprocess.run(cmd, check=True)
