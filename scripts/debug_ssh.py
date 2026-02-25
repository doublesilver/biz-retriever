import paramiko

HOSTNAME = "100.75.72.6"
USERNAME = "admin"
KEY_FILE = r"C:\Users\korea\.ssh\id_ed25519"

def test_ssh():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print(f"Connecting to {HOSTNAME}...")
        ssh.connect(HOSTNAME, username=USERNAME, key_filename=KEY_FILE, timeout=10)
        print("Connected!")
        
        commands = [
            "echo '--- DOCKER NAMES ---'; sudo docker ps --format '{{.Names}}'",
            "echo '--- DOCKER PORTS ---'; sudo docker ps --format '{{.Names}}: {{.Ports}}'",
            "echo '--- NETSTAT ---'; sudo netstat -tulpn | grep LISTEN",
            "echo '--- NGINX ---'; ls /etc/nginx/sites-enabled"
        ]
        
        for cmd in commands:
            print(f"\nExecuting: {cmd}")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            if out: print(f"STDOUT:\n{out}")
            if err: print(f"STDERR:\n{err}")
            if not out and not err: print("No output from command.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    test_ssh()
