#!/usr/bin/env bash
set -e

echo "=== Configuring PictureFrame Standalone Wi-Fi Hotspot ==="

# 1. Configure Captive Portal DNS via NetworkManager dnsmasq-shared
sudo mkdir -p /etc/NetworkManager/dnsmasq-shared.d
sudo tee /etc/NetworkManager/dnsmasq-shared.d/captive.conf > /dev/null << 'EOF'
address=/#/192.168.4.1
EOF

# 2. Remove existing Hotspot connection if present
sudo nmcli connection delete PictureFrame-Hotspot 2>/dev/null || true

# 3. Create NetworkManager Hotspot profile
sudo nmcli connection add \
    type wifi \
    ifname wlan0 \
    con-name PictureFrame-Hotspot \
    autoconnect yes \
    ssid PictureFrame \
    mode ap \
    802-11-wireless.band bg \
    802-11-wireless.channel 6 \
    802-11-wireless-security.key-mgmt wpa-psk \
    802-11-wireless-security.psk "raspberry" \
    ipv4.method shared \
    ipv4.addresses 192.168.4.1/24 \
    connection.autoconnect-priority 100

echo "Hotspot profile 'PictureFrame-Hotspot' configured successfully!"
