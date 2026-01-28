import subprocess
import os
import sys

# Windows SSH path
SSH_CMD = r'C:\Windows\System32\OpenSSH\ssh.exe'
HOST = "admin@100.75.72.6"
CONTAINER_FRONTEND = "biz-retriever-frontend"
CONTAINER_API = "biz-retriever-api"

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
    print("🚀 Starting PDF Support Deployment...")
    
    # 1. Deploy Files to host /tmp
    deploy_file('app/services/profile_service.py', '/tmp/profile_service.py')
    deploy_file('app/api/endpoints/profile.py', '/tmp/profile.py')
    deploy_file('frontend/profile.html', '/tmp/profile.html')
    
    # 2. Copy files to Containers
    print("\n📦 Copying files to containers...")
    
    # Backend
    run_ssh(f"docker cp /tmp/profile_service.py {CONTAINER_API}:/app/app/services/profile_service.py")
    run_ssh(f"docker cp /tmp/profile.py {CONTAINER_API}:/app/app/api/endpoints/profile.py")
    
    # Frontend
    run_ssh(f"docker cp /tmp/profile.html {CONTAINER_FRONTEND}:/usr/share/nginx/html/profile.html")
    
    # 3. Restart API
    print("\n🔄 Restarting API Server...")
    run_ssh("docker compose -f ~/projects/biz-retriever/docker-compose.pi.yml restart api")
    
    print("\n✅ PDF Support Deployment Complete!")
    print("Refresh your browser to see changes.")

if __name__ == "__main__":
    main()
