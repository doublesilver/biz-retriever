import subprocess
import os
import sys

# Remote info
REMOTE_HOST = "100.75.72.6"
REMOTE_USER = "admin"
SSH_CMD = r'C:\Windows\System32\OpenSSH\ssh.exe'
HOST = f"{REMOTE_USER}@{REMOTE_HOST}"

# Container info
CONTAINER_API = "biz-retriever-api"
CONTAINER_FRONTEND = "biz-retriever-frontend"

# Mapping: Local Path -> (Container Name, Container Path)
FILES_TO_DEPLOY = {
    "app/services/matching_service.py": (CONTAINER_API, "/app/app/services/matching_service.py"),
    "app/api/endpoints/analysis.py": (CONTAINER_API, "/app/app/api/endpoints/analysis.py"),
    "frontend/dashboard.html": (CONTAINER_FRONTEND, "/usr/share/nginx/html/dashboard.html"),
    "frontend/js/api.js": (CONTAINER_FRONTEND, "/usr/share/nginx/html/js/api.js"),
    "frontend/js/dashboard.js": (CONTAINER_FRONTEND, "/usr/share/nginx/html/js/dashboard.js")
}

def deploy_to_container(local_path, container_name, container_path):
    if not os.path.exists(local_path):
        print(f"❌ Error: {local_path} not found")
        return False

    with open(local_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"Deploying {local_path} -> {container_name}:{container_path}...")
    
    # Use docker exec -i ... tee to write file content inside container
    tee_cmd = f"sudo docker exec -i {container_name} tee {container_path} > /dev/null"
    full_cmd = [SSH_CMD, HOST, tee_cmd]
    
    try:
        process = subprocess.Popen(full_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        stdout, stderr = process.communicate(input=content)
        
        if process.returncode != 0:
            print(f"❌ Write failed: {stderr}")
            return False
        else:
            print("✅ Success")
            return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🚀 Starting Smart Search Feature Deployment...")
    
    # Files to copy for deployment
    files_to_scp = [
        "requirements.txt",
        "app/services/matching_service.py",
        "app/api/endpoints/analysis.py",
        "frontend/dashboard.html",
        "frontend/js/api.js",
        "frontend/js/dashboard.js",
        "scripts/remote_deploy_smart_search.sh"
    ]
    
    # 1. SCP all files to a temp location on host
    print("📤 Uploading files to remote host...")
    scp_cmd = f"scp {' '.join(files_to_scp)} {HOST}:~/projects/biz-retriever/deployment_temp/"
    
    # Ensure directory exists first
    subprocess.run([SSH_CMD, HOST, "mkdir -p ~/projects/biz-retriever/deployment_temp"], check=True)
    subprocess.run(scp_cmd, shell=True, check=True)
    
    # 2. Run remote deployment script
    print("⚙️ Executing remote deployment script...")
    deploy_cmd = (
        f"ssh {HOST} \"cd ~/projects/biz-retriever/deployment_temp && "
        "chmod +x remote_deploy_smart_search.sh && "
        "sudo ./remote_deploy_smart_search.sh\""
    )
    subprocess.run(deploy_cmd, shell=True, check=True)
    
    print("\n✅ Deployment complete! Refresh your browser to see the 'AI Smart Search' bar.")

if __name__ == "__main__":
    main()
