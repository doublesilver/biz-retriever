import subprocess
import os
import sys

# Windows SSH path
SSH_CMD = r'C:\Windows\System32\OpenSSH\ssh.exe'
HOST = "admin@100.75.72.6"
REMOTE_PROJECT_DIR = "~/projects/biz-retriever/frontend"

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
    print("🚀 Starting Frontend Rebuild Deployment...")
    
    # 1. Update Source Files on Host
    print("\n📦 Updating source files on host...")
    files_map = {
        'frontend/profile.html': f'{REMOTE_PROJECT_DIR}/profile.html',
        'frontend/js/api.js': f'{REMOTE_PROJECT_DIR}/js/api.js',
        'frontend/js/profile.js': f'{REMOTE_PROJECT_DIR}/js/profile.js',
        'frontend/js/dashboard.js': f'{REMOTE_PROJECT_DIR}/js/dashboard.js',
        'frontend/css/dashboard.css': f'{REMOTE_PROJECT_DIR}/css/dashboard.css',
    }
    
    for local, remote in files_map.items():
        deploy_file(local, remote)
        
    # 2. Rebuild and Restart Container
    print("\n🔄 Rebuilding and Restarting Frontend Container...")
    # Navigate to project root (one level up from frontend)
    cwd = "~/projects/biz-retriever"
    
    # Build only frontend
    run_ssh(f"cd {cwd} && docker compose -f docker-compose.pi.yml build frontend")
    
    # Up frontend (recreate)
    run_ssh(f"cd {cwd} && docker compose -f docker-compose.pi.yml up -d --no-deps frontend")
        
    print("\n✅ Frontend Rebuild Complete!")
    print("This guarantees the new files are served. Refresh your browser.")

if __name__ == "__main__":
    main()
