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
    {"local": "app/services/notification_service.py", "remote": f"{REMOTE_PROJECT_DIR}/app/services/notification_service.py", "container_dest": "/app/app/services/notification_service.py", "service": "api"},
    {"local": "app/api/endpoints/profile.py", "remote": f"{REMOTE_PROJECT_DIR}/app/api/endpoints/profile.py", "container_dest": "/app/app/api/endpoints/profile.py", "service": "api"},
    {"local": "app/worker/tasks.py", "remote": f"{REMOTE_PROJECT_DIR}/app/worker/tasks.py", "container_dest": "/app/app/worker/tasks.py", "service": "api"},
    
    # Frontend
    {"local": "frontend/profile.html", "remote": f"{REMOTE_PROJECT_DIR}/frontend/profile.html", "container_dest": "/usr/share/nginx/html/profile.html", "service": "frontend"},
    {"local": "frontend/js/profile.js", "remote": f"{REMOTE_PROJECT_DIR}/frontend/js/profile.js", "container_dest": "/usr/share/nginx/html/js/profile.js", "service": "frontend"}
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

    # 2. Run DB Patch inside API Container (Remote)
    print("Deploying and running DB patch script...")
    patch_local = "run_db_patch_notification.py"
    patch_remote = f"{REMOTE_PROJECT_DIR}/run_db_patch_notification.py"
    
    sftp = ssh.open_sftp()
    sftp.put(patch_local, patch_remote)
    sftp.close()
    
    ssh.exec_command(f"sudo docker cp {patch_remote} biz-retriever-api:/app/run_db_patch_notification.py")
    
    # Run patch
    stdin, stdout, stderr = ssh.exec_command("sudo docker exec biz-retriever-api python /app/run_db_patch_notification.py")
    print(stdout.read().decode())
    print(stderr.read().decode())

    # 3. Restart API Service to reload code and worker
    print("Restarting API service...")
    ssh.exec_command("sudo docker restart biz-retriever-api")
    
    # Note: Worker is likely inside 'api' container or separate 'worker' container?
    # Based on previous tasks, celery worker code is shared. 
    # If there is a separate worker container, we need to restart it too.
    # Checking docker-compose.yml (from memory/context) -> usually 'worker' service.
    # I will attempt to restart 'biz-retriever-worker' just in case.
    print("Restarting Worker service...")
    ssh.exec_command("sudo docker restart biz-retriever-worker")
    
    print("Deployment Complete.")
    ssh.close()

if __name__ == "__main__":
    deploy()
