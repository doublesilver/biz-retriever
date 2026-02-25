import paramiko
import os

# Configuration
HOSTNAME = "100.75.72.6"
USERNAME = "admin"
KEY_FILE = r"C:\Users\korea\.ssh\id_ed25519"
REMOTE_PROJECT_DIR = "/home/admin/projects/biz-retriever"

FILES_TO_DEPLOY = [
    {
        "local": "app/schemas/bid.py",
        "remote": f"{REMOTE_PROJECT_DIR}/app/schemas/bid.py",
        "container_dest": "/app/app/schemas/bid.py", # For API container
        "service": "api"
    },
    {
        "local": "frontend/kanban.html",
        "remote": f"{REMOTE_PROJECT_DIR}/frontend/kanban.html",
        "container_dest": "/usr/share/nginx/html/kanban.html", # For Frontend container
        "service": "frontend"
    },
    {
        "local": "frontend/js/kanban.js",
        "remote": f"{REMOTE_PROJECT_DIR}/frontend/js/kanban.js",
        "container_dest": "/usr/share/nginx/html/js/kanban.js",
        "service": "frontend"
    },
    {
        "local": "frontend/css/kanban.css",
        "remote": f"{REMOTE_PROJECT_DIR}/frontend/css/kanban.css",
        "container_dest": "/usr/share/nginx/html/css/kanban.css",
        "service": "frontend"
    }
]

def deploy():
    print(f"Connecting to {HOSTNAME}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, key_filename=KEY_FILE)

    for file_info in FILES_TO_DEPLOY:
        local_path = file_info["local"]
        remote_path = file_info["remote"]
        
        print(f"Deploying {local_path} -> {remote_path}...")
        
        # Read local content
        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Write to remote file (using cat)
        # We need to escape single quotes slightly or just use a safe method.
        # Simplest is sftp but let's use sftp for reliability
        sftp = ssh.open_sftp()
        try:
            sftp.put(local_path, remote_path)
            print(f"  [OK] Uploaded to host")
        except Exception as e:
            print(f"  [Error] Upload failed: {e}")
            continue
            
        sftp.close()

        # Update Container
        service = file_info["service"]
        container_name = f"biz-retriever-{service}"
        container_dest = file_info["container_dest"]
        
        # docker cp
        cmd = f"sudo docker cp {remote_path} {container_name}:{container_dest}"
        print(f"  Running: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
             print("  [OK] Updated container")
        else:
             print(f"  [Error] Container update failed: {stderr.read().decode()}")

    # Restart Services
    print("Restarting API service to apply schema changes...")
    ssh.exec_command("sudo docker restart biz-retriever-api")
    
    # Frontend/Nginx doesn't technically need restart for static files if mapped, 
    # but since we did `docker cp`, it's immediate. 
    # However, if volume is mounted, cp to container might be redundant if we updated host file?
    # Wait, check docker-compose.
    # Volumes: - ./frontend:/usr/share/nginx/html
    # If using volume, updating host file is enough!
    # But `docker cp` ensures it if volume mapping is different.
    # Let's checked docker-compose.pi.yml earlier. 
    # Validating volume mapping...
    
    print("Deployment Complete.")
    ssh.close()

if __name__ == "__main__":
    deploy()
