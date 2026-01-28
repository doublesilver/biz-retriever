import subprocess
import os
import sys

# Windows SSH path
SSH_CMD = r'C:\Windows\System32\OpenSSH\ssh.exe'
HOST = "admin@100.75.72.6"
CONTAINER = "biz-retriever-frontend"

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
    print("🚀 Starting APIJS Fix Deployment...")
    
    # 1. Deploy File to host /tmp
    deploy_file('frontend/js/api.js', '/tmp/api.js')
    
    # 2. Copy file to Container
    print("\n📦 Copying file to Nginx container...")
    run_ssh(f"docker cp /tmp/api.js {CONTAINER}:/usr/share/nginx/html/js/api.js")
        
    print("\n✅ APIJS Fix Deployment Complete!")
    print("Refresh your browser to see changes.")

if __name__ == "__main__":
    main()
