import paramiko
import os

# Configuration
HOSTNAME = "100.75.72.6"
USERNAME = "admin"
KEY_FILE = r"C:\Users\korea\.ssh\id_ed25519"
REMOTE_PROJECT_DIR = "/home/admin/projects/biz-retriever"

FILES_TO_DEPLOY = [
    {
        "local": "app/db/models.py",
        "remote": f"{REMOTE_PROJECT_DIR}/app/db/models.py",
        "container_dest": "/app/app/db/models.py", # For API container
        "service": "api"
    },
    {
        "local": "app/api/endpoints/profile.py",
        "remote": f"{REMOTE_PROJECT_DIR}/app/api/endpoints/profile.py",
        "container_dest": "/app/app/api/endpoints/profile.py", # For API container
        "service": "api"
    },
    # Note: Frontend files are mapped volume or copied. We force cp for safety.
    {
        "local": "frontend/profile.html",
        "remote": f"{REMOTE_PROJECT_DIR}/frontend/profile.html",
        "container_dest": "/usr/share/nginx/html/profile.html", # For Frontend container
        "service": "frontend"
    },
    {
        "local": "frontend/js/profile.js",
        "remote": f"{REMOTE_PROJECT_DIR}/frontend/js/profile.js",
        "container_dest": "/usr/share/nginx/html/js/profile.js",
        "service": "frontend"
    }
]

def deploy():
    print(f"Connecting to {HOSTNAME} with {KEY_FILE}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, key_filename=KEY_FILE)

    for file_info in FILES_TO_DEPLOY:
        local_path = file_info["local"]
        remote_path = file_info["remote"]
        
        print(f"Deploying {local_path} -> {remote_path}...")
        
        # Sftp Put
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
        
        cmd = f"sudo docker cp {remote_path} {container_name}:{container_dest}"
        print(f"  Running: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
             print("  [OK] Updated container")
        else:
             print(f"  [Error] Container update failed: {stderr.read().decode()}")

    # Database Migration
    print("Running Database Migration (Adding columns)...")
    # Using 'psql' inside db container
    # Columns: credit_rating, employee_count, founding_year, main_bank, standard_industry_codes
    sqls = [
        "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS credit_rating VARCHAR;",
        "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS employee_count INTEGER;",
        "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS founding_year INTEGER;",
        "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS main_bank VARCHAR;",
        "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS standard_industry_codes JSON DEFAULT '[]'::json;"
    ]
    
    for sql in sqls:
        # We need to escape double quotes for shell if any, but simplistic approach here
        db_cmd = f"sudo docker exec -i biz-retriever-db psql -U admin -d biz_retriever -c \"{sql}\""
        print(f"  Executing SQL: {sql}")
        stdin, stdout, stderr = ssh.exec_command(db_cmd)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            print(f"    [Error]: {stderr.read().decode()}")
        else:
            print("    [OK]")

    # Restart Services
    print("Restarting API service...")
    ssh.exec_command("sudo docker restart biz-retriever-api")
    
    print("Deployment Complete.")
    ssh.close()

if __name__ == "__main__":
    deploy()
