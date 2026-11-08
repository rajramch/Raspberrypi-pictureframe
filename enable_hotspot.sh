#!/usr/bin/env bash
# Activates the PictureFrame standalone Wi-Fi hotspot
echo "Switching to PictureFrame Hotspot..."
sudo nmcli connection up PictureFrame-Hotspot
echo "PictureFrame hotspot is now active!"
echo "Connect to Wi-Fi SSID: PictureFrame (Open network, no password required)"
echo "Picture Frame Dashboard: http://192.168.4.1"
