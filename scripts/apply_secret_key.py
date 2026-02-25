import subprocess
import os
import sys
import re

# Configuration
NEW_KEY = "REPLACEME" # API Key should be managed via .env, not committed to git!
SSH_CMD = r'C:\Windows\System32\OpenSSH\ssh.exe'
HOST = "admin@100.75.72.6"
REMOTE_ENV_PATH = "~/projects/biz-retriever/.env"

def run_ssh_command(cmd, input_data=None):
    full_cmd = [SSH_CMD, HOST, cmd]
    try:
        if input_data:
            process = subprocess.Popen(full_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
            stdout, stderr = process.communicate(input=input_data)
        else:
            process = subprocess.Popen(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
            stdout, stderr = process.communicate()
            
        if process.returncode != 0:
            print(f"Error executing remote command: {cmd}")
            print(stderr)
            return None
        return stdout
    except Exception as e:
        print(f"SSH Error: {e}")
        return None

def update_env_file():
    print("1. Reading remote .env file...")
    content = run_ssh_command(f"cat {REMOTE_ENV_PATH}")
    if not content:
        print("Failed to read .env file. Aborting.")
        return False
    
    print("2. Updating GEMINI_API_KEY...")
    # Regex replace to be safe
    new_content = re.sub(
        r'^GEMINI_API_KEY=.*$', 
        f'GEMINI_API_KEY={NEW_KEY}', 
        content, 
        flags=re.MULTILINE
    )
    
    # If key didn't exist, append it
    if f'GEMINI_API_KEY={NEW_KEY}' not in new_content:
        new_content += f"\nGEMINI_API_KEY={NEW_KEY}\n"

    print("3. Writing updated .env file...")
    # Use cat > to overwrite
    # Note: We pass new_content as input to stdin
    # We need to construct the command differently for run_ssh_command helper to handle stdin properly
    # Re-implementing simplified logic here for the write specifically
    full_cmd = [SSH_CMD, HOST, f"cat > {REMOTE_ENV_PATH}"]
    try:
        process = subprocess.Popen(full_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        stdout, stderr = process.communicate(input=new_content)
        if process.returncode != 0:
            print(f"Failed to write .env: {stderr}")
            return False
    except Exception as e:
        print(f"Write Error: {e}")
        return False

    print("✅ .env updated successfully.")
    return True

def restart_api():
    print("4. Recreating API container to apply env vars...")
    # restart does NOT reload env files. Must use up -d --force-recreate
    cmd = "docker compose -f ~/projects/biz-retriever/docker-compose.pi.yml up -d --force-recreate api"
    result = run_ssh_command(cmd)
    if result is not None:
        print("✅ API Container recreated.")
        return True
    return False

def run_verification():
    print("5. Redeploying verification script...")
    # 1. SCP to host tmp (redundant if already there, but safe)
    # We assume verify_rag.py is in local scripts/ folder
    local_verify_script = 'scripts/verify_rag.py'
    remote_tmp_path = '/tmp/verify_rag.py'
    
    with open(local_verify_script, 'r', encoding='utf-8') as f:
        content = f.read()

    # Write to remote tmp
    full_cmd = [SSH_CMD, HOST, f"cat > {remote_tmp_path}"]
    try:
        process = subprocess.Popen(full_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        stdout, stderr = process.communicate(input=content)
    except Exception as e:
        print(f"Failed to upload verify script: {e}")
        return

    # 2. Docker cp to new container
    print("   Copying to new container...")
    run_ssh_command(f"docker cp {remote_tmp_path} biz-retriever-api:/app/scripts/verify_rag.py")

    print("6. Running RAG verification...")
    cmd = "docker exec biz-retriever-api python scripts/verify_rag.py"
    # Execute directly via subprocess to stream output to user
    full_cmd = [SSH_CMD, HOST, cmd]
    subprocess.run(full_cmd)

def main():
    print("🔒 Applying new API Key securely...")
    
    if update_env_file():
        if restart_api():
            print("\n⏳ Waiting 5 seconds for service to stabilize...")
            import time
            time.sleep(5)
            run_verification()

if __name__ == "__main__":
    main()
