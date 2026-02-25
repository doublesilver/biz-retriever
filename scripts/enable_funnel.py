import subprocess
import sys

# Windows SSH path
SSH_CMD = r'C:\Windows\System32\OpenSSH\ssh.exe'
HOST = "admin@100.75.72.6"

def main():
    print("🚀 Enabling Tailscale Funnel on Port 3001...")
    
    # 1. Enable Funnel (Background)
    # Using sudo, and --yes to accept prompts if any (though funnel doesn't usually have yes flag)
    # We use --bg to detach.
    setup_cmd = [SSH_CMD, HOST, "sudo tailscale funnel --bg 3001"]
    
    try:
        print(f"Executing: {' '.join(setup_cmd)}")
        print("⌨️  (If prompted for password and nothing appears, type it blindly and press Enter)")
        # Allow interactive input for password
        result = subprocess.run(setup_cmd, text=True, encoding='utf-8')
        
        if result.returncode != 0:
            print(f"⚠️  Setup Warning: Command returned {result.returncode}")
        else:
            print("Setup command sent.")
            
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        return

    # 2. Check Status
    print("\n🔍 Verifying Status...")
    status_cmd = [SSH_CMD, HOST, "sudo tailscale serve status"]
    
    try:
        result = subprocess.run(status_cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode != 0:
            print(f"❌ Status Check Failed: {result.stderr}")
        else:
            output = result.stdout.strip()
            print("✅ Status Output:")
            print(output)
            
            if "https://" in output:
                print("\n🎉 SUCCESS! Your Public URL is in the output above.")
            else:
                print("\n⚠️  No URL found yet. Funnel might be disabled via policy or taking time.")

    except Exception as e:
        print(f"❌ Error checking status: {e}")

if __name__ == "__main__":
    main()
