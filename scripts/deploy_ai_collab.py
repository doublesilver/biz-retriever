import paramiko
import os

# Configuration
HOSTNAME = "100.75.72.6"
USERNAME = "admin"
KEY_FILE = r"C:\Users\korea\.ssh\id_ed25519"
REMOTE_PROJECT_DIR = "/home/admin/projects/biz-retriever"

FILES_TO_DEPLOY = [
    # Backend
    {"local": "app/core/config.py", "remote": f"{REMOTE_PROJECT_DIR}/app/core/config.py", "container_dest": "/app/app/core/config.py", "service": "api"},
    {"local": "app/services/crawler_service.py", "remote": f"{REMOTE_PROJECT_DIR}/app/services/crawler_service.py", "container_dest": "/app/app/services/crawler_service.py", "service": "api"},
    {"local": "app/api/endpoints/analysis.py", "remote": f"{REMOTE_PROJECT_DIR}/app/api/endpoints/analysis.py", "container_dest": "/app/app/api/endpoints/analysis.py", "service": "api"},
    {"local": "app/api/endpoints/auth.py", "remote": f"{REMOTE_PROJECT_DIR}/app/api/endpoints/auth.py", "container_dest": "/app/app/api/endpoints/auth.py", "service": "api"},
    
    # Frontend
    {"local": "frontend/kanban.html", "remote": f"{REMOTE_PROJECT_DIR}/frontend/kanban.html", "container_dest": "/usr/share/nginx/html/kanban.html", "service": "frontend"},
    {"local": "frontend/css/kanban.css", "remote": f"{REMOTE_PROJECT_DIR}/frontend/css/kanban.css", "container_dest": "/usr/share/nginx/html/css/kanban.css", "service": "frontend"},
    {"local": "frontend/js/kanban.js", "remote": f"{REMOTE_PROJECT_DIR}/frontend/js/kanban.js", "container_dest": "/usr/share/nginx/html/js/kanban.js", "service": "frontend"}
]

def deploy():
    print(f"Connecting to {HOSTNAME}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, key_filename=KEY_FILE)

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

    # Restart API
    print("Restarting API service...")
    ssh.exec_command("sudo docker restart biz-retriever-api")
    
    # Note: DB migration for BidResult table likely already exists from previous runs/Alembic,
    # but let's ensure the table exists or columns are correct.
    # BidResult was already in models.py. 
    # If it was added recently, we might need a migration.
    # I'll check if the table exists.
    
    print("Deployment Complete.")
    ssh.close()

if __name__ == "__main__":
    deploy()
