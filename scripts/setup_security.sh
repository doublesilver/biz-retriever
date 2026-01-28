#!/bin/bash

# Biz-Retriever Security Setup Script
# Target: Raspberry Pi / Ubuntu

set -e

echo "🛡️ Starting Security Hardening..."

# 1. Update and install dependencies
echo "📦 Installing security tools..."
sudo apt update
sudo apt install -y ufw fail2ban unattended-upgrades

# 2. Configure Firewall (UFW)
echo "🔥 Configuring UFW..."
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow standard ports
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 3001/tcp    # Frontend Nginx (Funnel Port)
sudo ufw allow 8000/tcp    # API (Optional - internal use)

# Allow Tailscale traffic
sudo ufw allow in on tailscale0

# Enable UFW
echo "y" | sudo ufw enable
sudo ufw status verbose

# 3. Configure Fail2Ban
echo "🚫 Configuring Fail2Ban..."
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Create a local jail for SSH if it doesn't exist
if [ ! -f /etc/fail2ban/jail.local ]; then
    echo "[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
maxretry = 5
bantime = 3600" | sudo tee /etc/fail2ban/jail.local
fi
sudo systemctl restart fail2ban

# 4. Configure Unattended-Upgrades (Auto security patches)
echo "🔄 Configuring Unattended-Upgrades..."
sudo dpkg-reconfigure -f noninteractive unattended-upgrades
echo 'APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";' | sudo tee /etc/apt/apt.conf.d/20auto-upgrades

echo "✅ Security Hardening Complete!"
sudo ufw status
sudo fail2ban-client status sshd
