import subprocess
import os
import sys

# Windows SSH path
SSH_CMD = r'C:\Windows\System32\OpenSSH\ssh.exe'
HOST = "admin@100.75.72.6"
CONTAINER_FRONTEND = "biz-retriever-frontend"

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
    print("🚀 Starting Complete Frontend Fix Deployment...")
    
    # 2. Deploy directly to Container using tee (more robust than cp)
    print("\n📦 Deploying files directly to Nginx container...")
    
    files_map = {
        'frontend/profile.html': '/usr/share/nginx/html/profile.html',
        'frontend/js/api.js': '/usr/share/nginx/html/js/api.js',
        'frontend/js/profile.js': '/usr/share/nginx/html/js/profile.js',
    }
    
    for local_path, remote_path in files_map.items():
        if not os.path.exists(local_path):
            print(f"❌ Error: {local_path} not found")
            continue
            
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        print(f"Writing {local_path} -> {CONTAINER_FRONTEND}:{remote_path}...")
        
        # Use docker exec -i ... tee to write file content inside container
        # Note: We pipeline content via stdin
        tee_cmd = f"docker exec -i {CONTAINER_FRONTEND} tee {remote_path} > /dev/null"
        full_cmd = [SSH_CMD, HOST, tee_cmd]
        
        try:
            process = subprocess.Popen(full_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
            stdout, stderr = process.communicate(input=content)
            
            if process.returncode != 0:
                print(f"❌ Write failed: {stderr}")
            else:
                print("✅ Success")
        except Exception as e:
            print(f"❌ Error: {e}")
    print("Refresh your browser to see changes.")

if __name__ == "__main__":
    main()
