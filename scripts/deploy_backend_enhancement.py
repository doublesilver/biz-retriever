import subprocess
import os
import sys

# Windows SSH path
SSH_CMD = r'C:\Windows\System32\OpenSSH\ssh.exe'
HOST = "admin@100.75.72.6"

def run_ssh(cmd_str):
    full_cmd = [SSH_CMD, HOST, cmd_str]
    subprocess.run(full_cmd, check=True)

def deploy_file(local_path, remote_path):
    if not os.path.exists(local_path):
        print(f"❌ Error: {local_path} not found")
        sys.exit(1)

    with open(local_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"deployment: {local_path} -> {remote_path}")
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
    print("🚀 Starting Backend Enhancement Deployment...")
    
    # 1. Deploy Files to host /tmp
    deploy_file('scripts/add_ai_columns.py', '/tmp/add_ai_columns.py')
    deploy_file('app/db/models.py', '/tmp/models.py')
    deploy_file('app/schemas/bid.py', '/tmp/bid.py')
    
    # 2. Copy files to Container
    print("\n📦 Copying files to container...")
    cmds = [
        "docker cp /tmp/add_ai_columns.py biz-retriever-api:/app/scripts/add_ai_columns.py",
        "docker cp /tmp/models.py biz-retriever-api:/app/app/db/models.py",
        "docker cp /tmp/bid.py biz-retriever-api:/app/app/schemas/bid.py"
    ]
    for cmd in cmds:
        run_ssh(cmd)
        
    # 3. Run DB Migration (Add Columns)
    print("\n🗄️  Running DB Migration...")
    run_ssh("docker exec biz-retriever-api python scripts/add_ai_columns.py")
    
    # 4. Restart API to pick up code changes
    print("\n🔄 Restarting API Server...")
    # Use up -d --force-recreate to be super safe about environment loading? 
    # Actually restart is faster and we only changed python code, not env vars.
    # But schemas/models are imported at startup. Restart is required.
    run_ssh("docker compose -f ~/projects/biz-retriever/docker-compose.pi.yml restart api")
    
    print("\n✅ Deployment & Migration Complete!")

if __name__ == "__main__":
    main()
