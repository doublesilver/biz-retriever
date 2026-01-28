import subprocess
import sys

# Windows SSH path
SSH_CMD = r'C:\Windows\System32\OpenSSH\ssh.exe'
HOST = "admin@100.75.72.6"

def main():
    print("🔍 Checking Tailscale Funnel Status...")
    cmd = [SSH_CMD, HOST, "tailscale serve status"]
    
    try:
        # Capture output
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode != 0:
            print(f"❌ Command failed (Exit {result.returncode})")
            print(f"Stderr: {result.stderr}")
        else:
            print("✅ Status Output:")
            print(result.stdout)
            
            if not result.stdout.strip():
                print("⚠️ Output was empty. Trying 'sudo tailscale serve status'...")
                # Fallback to sudo if needed (might prompt password)
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
