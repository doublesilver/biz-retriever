import paramiko
import os

# Configuration
HOSTNAME = "100.75.72.6"
USERNAME = "admin"
KEY_FILE = r"C:\Users\korea\.ssh\id_ed25519"
REMOTE_PROJECT_DIR = "/home/admin/projects/biz-retriever"

FILES_TO_DEPLOY = [
    # Backend
    {"local": "app/db/models.py", "remote": f"{REMOTE_PROJECT_DIR}/app/db/models.py", "container_dest": "/app/app/db/models.py", "service": "api"},
    {"local": "app/core/config.py", "remote": f"{REMOTE_PROJECT_DIR}/app/core/config.py", "container_dest": "/app/app/core/config.py", "service": "api"},
    {"local": "app/api/endpoints/auth.py", "remote": f"{REMOTE_PROJECT_DIR}/app/api/endpoints/auth.py", "container_dest": "/app/app/api/endpoints/auth.py", "service": "api"},
    
    # Frontend
    {"local": "frontend/index.html", "remote": f"{REMOTE_PROJECT_DIR}/frontend/index.html", "container_dest": "/usr/share/nginx/html/index.html", "service": "frontend"},
    {"local": "frontend/css/main.css", "remote": f"{REMOTE_PROJECT_DIR}/frontend/css/main.css", "container_dest": "/usr/share/nginx/html/css/main.css", "service": "frontend"},
    {"local": "frontend/js/dashboard.js", "remote": f"{REMOTE_PROJECT_DIR}/frontend/js/dashboard.js", "container_dest": "/usr/share/nginx/html/js/dashboard.js", "service": "frontend"}
]

def deploy():
    print(f"Connecting to {HOSTNAME}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, key_filename=KEY_FILE)

    # 1. Upload files and Update Containers
    for file_info in FILES_TO_DEPLOY:
        local_path = file_info["local"]
        remote_path = file_info["remote"]
        
        print(f"Deploying {local_path}...")
        sftp = ssh.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()

        # Update Container
        service = file_info["service"]
        container_name = f"biz-retriever-{service}"
        container_dest = file_info["container_dest"]
        
        cmd = f"sudo docker cp {remote_path} {container_name}:{container_dest}"
        ssh.exec_command(cmd)

    # 2. Run DB Patch inside API Container (Since we did it manually, we need to apply it on Remote too)
    # We will upload the patch script and run it.
    print("Deploying and running DB patch script...")
    patch_local = "run_db_patch.py"
    patch_remote = f"{REMOTE_PROJECT_DIR}/run_db_patch.py"
    
    sftp = ssh.open_sftp()
    sftp.put(patch_local, patch_remote)
    sftp.close()
    
    ssh.exec_command(f"sudo docker cp {patch_remote} biz-retriever-api:/app/run_db_patch.py")
    
    # Run patch
    stdin, stdout, stderr = ssh.exec_command("sudo docker exec biz-retriever-api python /app/run_db_patch.py")
    print(stdout.read().decode())
    print(stderr.read().decode())

    # 3. Restart API Service to reload code
    print("Restarting API service...")
    ssh.exec_command("sudo docker restart biz-retriever-api")
    
    print("Deployment Complete.")
    ssh.close()

if __name__ == "__main__":
    deploy()
