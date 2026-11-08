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
    # Try Raj or any saved Wi-Fi connection
    if nmcli -t -f NAME connection show | grep -qx "Raj"; then
        sudo nmcli connection up Raj
    else
        # Reconnect to first available saved Wi-Fi connection
        SAVED_CON=$(nmcli -t -f NAME,TYPE connection show | grep ":802-11-wireless$" | grep -v "PictureFrame-Hotspot" | head -n1 | cut -d: -f1)
        if [ -n "$SAVED_CON" ]; then
            sudo nmcli connection up "$SAVED_CON"
        else
            echo "No saved Wi-Fi profile found. Specify SSID and password: ./connect_wifi.sh <SSID> <PASSWORD>"
        fi
    fi
fi
