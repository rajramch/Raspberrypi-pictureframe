#!/usr/bin/env bash
# Usage: ./connect_wifi.sh [SSID] [PASSWORD]
# If no arguments provided, attempts to reconnect to previously saved Wi-Fi (e.g. Raj)

if [ -n "$1" ]; then
    echo "Connecting to Wi-Fi '$1'..."
    sudo nmcli connection down PictureFrame-Hotspot 2>/dev/null || true
    sudo nmcli device wifi connect "$1" password "$2"
else
    echo "Reconnecting to saved Wi-Fi..."
    sudo nmcli connection down PictureFrame-Hotspot 2>/dev/null || true
    sudo nmcli connection up Raj 2>/dev/null || true
fi
