# Raspberry Pi E-Ink Picture Frame

An automated e-ink digital picture frame using a Raspberry Pi and Pimoroni Inky Impression (7.3" 7-color display, 800x480 resolution).

## Features

- **Interactive Cropping & Zooming Studio**:
  - Pan & Drag: move the image inside the crop box to frame exactly what you want.
  - Zoom Controls: pinch-to-zoom on touchscreens, mouse scroll wheel, zoom buttons (+/-), and range slider.
  - Rotation: Rotate 90° clockwise/counter-clockwise before uploading.
- **Orientation Modes (Horizontal, Vertical, Square)**:
  - **Horizontal (Landscape)**: Fits 800×480 screen perfectly.
  - **Vertical (Portrait / Digital Art)**:
    - *Stand Upright*: Rotates 90° so the right side of the screen is the bottom when your frame is turned vertically.
    - *Fit Horizontal*: Centers the vertical artwork with clean side borders so no part is cropped.
  - **Square (1:1)**: Centers square artwork on the 800×480 display with neat borders.
- **Automatic Image Optimization**: 
  - Detects and corrects EXIF rotation (e.g. photos taken vertically on smartphones).
  - High-quality Lanczos resampling and conversion to RGB for optimal 7-color e-ink dithering.
- **2-Hour Auto Slideshow**:
  - Automatically cycles through all uploaded images every 2 hours.
  - Newly uploaded images display immediately and reset the 2-hour timer.
  - Skips redundant e-ink refresh cycles if only 1 image exists to protect the screen.
- **Dual Port Support (Port 80 & Port 5000)**:
  - Accessible on `http://rpizero.local` or `http://<pi-ip>` without typing `:5000`.
  - Also backwards-compatible on `:5000`.
- **Picture Rotation Gallery**:
  - View all stored pictures in rotation.
  - "Display Now" button to instantly push any photo to the frame.
  - Delete photos from the rotation.

## Systemd Service

The application is configured to run automatically as a background service:

```bash
sudo systemctl status inkyweb.service
sudo systemctl restart inkyweb.service
```

## Running Manually

```bash
# In the project directory:
source venv/bin/activate
python3 app.py
```

By default, the server runs on port `5000` (e.g. `http://<pi-ip>:5000/`).
To change the rotation interval (e.g., for testing every 30 seconds):
```bash
ROTATION_INTERVAL=30 python3 app.py
```
