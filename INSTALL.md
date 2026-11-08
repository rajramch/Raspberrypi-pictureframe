# Fresh Raspberry Pi Installation Guide

This guide walks you through setting up the **Raspberry Pi E-Ink Picture Frame** project on a completely fresh, brand-new Raspberry Pi from scratch.

---

## 1. Prerequisites & Hardware

* **Raspberry Pi**: Pi Zero W, Pi Zero 2 W, 3, 4, or 5 (equipped with 40-pin GPIO header).
* **Display**: Pimoroni Inky Impression (7.3" or 5.7" 7-color e-paper display).
* **MicroSD Card**: 8GB or larger (Class 10 / A1 recommended).
* **Power Supply**: 5V micro-USB (Pi Zero / 3) or USB-C (Pi 4 / 5).

---

## 2. Flash Raspberry Pi OS

1. Download and open **[Raspberry Pi Imager](https://www.raspberrypi.com/software/)** on your computer.
2. Select your device model (e.g. *Raspberry Pi Zero W*).
3. Select OS: **Raspberry Pi OS Lite (32-bit or 64-bit)** (Lite is recommended for faster boot and minimal RAM usage on Pi Zero).
4. Click **Next**, and when prompted to edit OS customization settings, configure:
   * **Hostname**: `rpizero`
   * **Username and password**: e.g., username `pi`, password `raspberry`
   * **Configure wireless LAN**: Enter your Wi-Fi SSID and password
   * **Services**: Check **Enable SSH** (use password authentication)
5. Flash the OS to your MicroSD card, insert it into the Raspberry Pi, and power it on.

---

## 3. Enable SPI and I2C Hardware Interfaces

The Inky Impression display requires **SPI** (for high-speed pixel data) and **I2C** (for display identification).

1. Connect to your Pi via SSH from your computer terminal:
   ```bash
   ssh pi@rpizero.local
   # Or using its IP: ssh pi@<your-pi-ip>
   ```
2. Enable SPI and I2C non-interactively:
   ```bash
   sudo raspi-config nonint do_spi 0
   sudo raspi-config nonint do_i2c 0
   ```
   *(Alternatively, run `sudo raspi-config` -> **Interface Options** -> enable **SPI** and **I2C**).*

---

## 4. Install System Dependencies

Update packages and install Python 3, virtual environment tools, Git, and imaging libraries required by Pillow:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git libopenjp2-7 libtiff6 libjpeg62-turbo
```

---

## 5. Clone the Repository

Clone this project repository into your home directory:

```bash
cd ~
git clone https://github.com/rajramch/Raspberrypi-pictureframe.git
cd Raspberrypi-pictureframe
```

Create the `images/` directory where uploaded pictures will be stored:

```bash
mkdir -p images
```

---

## 6. Set Up Python Virtual Environment

Modern Raspberry Pi OS uses `PEP 668` (externally managed environment). All Python dependencies must be installed inside a virtual environment:

```bash
# Create virtual environment named 'venv'
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip and install all required libraries
pip install --upgrade pip
pip install -r requirements.txt
```

Verify that the `inky` library recognizes your display:

```bash
python3 -c "from inky import Inky_Impressions_7; inky = Inky_Impressions_7(); print('Display resolution:', inky.resolution)"
# Expected output: Display resolution: (800, 480)
```

---

## 7. Set Up Systemd Service (Auto-Start on Boot)

To run the web server automatically on boot and restart if it ever crashes:

1. Create the systemd service file:
   ```bash
   sudo tee /etc/systemd/system/inkyweb.service > /dev/null << 'EOF'
   [Unit]
   Description=Inky Impression Picture Frame Web App
   After=network.target

   [Service]
   User=pi
   WorkingDirectory=/home/pi/Raspberrypi-pictureframe
   ExecStart=/home/pi/Raspberrypi-pictureframe/venv/bin/python3 app.py
   AmbientCapabilities=CAP_NET_BIND_SERVICE
   CapabilityBoundingSet=CAP_NET_BIND_SERVICE
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   EOF
   ```
   *(Note: `AmbientCapabilities=CAP_NET_BIND_SERVICE` allows Python to bind to privileged Port 80 without running as root!)*

2. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable inkyweb.service
   sudo systemctl start inkyweb.service
   ```

3. Check service status:
   ```bash
   sudo systemctl status inkyweb.service
   ```

---

## 8. Access the Web Dashboard

Open your web browser on any phone, tablet, Mac, or PC connected to the same network:

* **Direct Hostname (Mac, PC, Linux)**: `http://rpizero.local`
* **Direct IP (Android, Phone, Mac, PC)**: `http://<your-pi-ip>` or `http://<your-pi-ip>:5000`

---

## 9. Useful Commands & Troubleshooting

### View Live Logs
```bash
journalctl -u inkyweb.service -f
```

### Restart Service
```bash
sudo systemctl restart inkyweb.service
```

### Stop Service
```bash
sudo systemctl stop inkyweb.service
```

### Custom Rotation Interval
By default, pictures rotate every 2 hours (`7200` seconds). To test or change this, edit `/etc/systemd/system/inkyweb.service` and add an environment variable under `[Service]`:
```ini
Environment="ROTATION_INTERVAL=60"
```
Then run:
```bash
sudo systemctl daemon-reload && sudo systemctl restart inkyweb.service
```

### Prevent HDMI Console from Going Blank (Display Timeout)
On Raspberry Pi OS, the HDMI screen turns black after 10-15 minutes of inactivity (console blanking). If you connect a monitor or TV to view the terminal or debug settings, add `consoleblank=0` to prevent the screen from going blank:

```bash
sudo sed -i 's/$/ consoleblank=0/' /boot/firmware/cmdline.txt
```
*(Pressing any key on a connected keyboard also wakes the screen instantly).*

---

## 10. Standalone Wi-Fi Hotspot Mode (Captive Portal)

If you do not want to rely on an external home router or mobile hotspot (or to avoid mobile data routing conflicts on Android), the Raspberry Pi can broadcast its own dedicated Wi-Fi network:

### Set Up Hotspot Profile
```bash
chmod +x setup_hotspot.sh enable_hotspot.sh connect_wifi.sh
./setup_hotspot.sh
./enable_hotspot.sh
```

> **Technical note for Raspberry Pi Zero W (`brcmfmac`):**
> NetworkManager on Pi Zero W requires Protected Management Frames to be disabled (`pmf 1`) and cipher suites locked to WPA2-PSK (`proto rsn`, `pairwise ccmp`, `group ccmp`), which `setup_hotspot.sh` automatically configures.

* **Wi-Fi SSID**: `PictureFrame`
* **Password**: `raspberry`
* **IP Address**: `192.168.4.1`
* **Captive Portal**: Any Android phone, iPhone, Mac, or PC that connects to `PictureFrame` will automatically receive a *"Sign in to network"* notification or can visit `http://192.168.4.1` (or `http://rpizero.local`) to access the picture frame studio immediately.
* **To switch back to normal Wi-Fi**:
  ```bash
  ./connect_wifi.sh
  ```
