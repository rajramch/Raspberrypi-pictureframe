import os
import io
import time
import logging
import threading
from datetime import datetime
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    url_for,
    flash,
    redirect,
    send_from_directory,
)
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename

# Optional Inky hardware library import (graceful fallback for local development)
try:
    from inky import Inky_Impressions_7
    HAVE_INKY = True
except ImportError:
    HAVE_INKY = False

# Paths & Directories
BASE_DIR = Path(__file__).resolve().parent
IMAGES_DIR = BASE_DIR / "images"
IMAGES_DIR.mkdir(exist_ok=True)
STATE_FILE = BASE_DIR / ".current_image"

# Allowed extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}

# Rotation interval in seconds: 2 hours = 7200 seconds
# Can be overridden via environment variable ROTATION_INTERVAL (e.g. for testing)
DEFAULT_INTERVAL = 2 * 3600
ROTATION_INTERVAL = int(os.environ.get("ROTATION_INTERVAL", DEFAULT_INTERVAL))

SATURATION = 0.5
TARGET_RESOLUTION = (800, 480)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("pictureframe")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "inky-picture-frame-secret")
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32MB max upload limit

# Concurrency & Coordination
display_lock = threading.Lock()
rotation_event = threading.Event()
stop_slideshow = threading.Event()

current_displayed_image = None
inky_device = None


def get_inky():
    """Returns singleton Inky_Impressions_7 device instance."""
    global inky_device
    if not HAVE_INKY:
        return None
    if inky_device is None:
        inky_device = Inky_Impressions_7()
    return inky_device


def get_image_list():
    """Returns a sorted list of all valid image filenames stored in IMAGES_DIR."""
    if not IMAGES_DIR.exists():
        return []
    files = [
        f for f in os.listdir(IMAGES_DIR)
        if Path(f).suffix.lower() in ALLOWED_EXTENSIONS and not f.startswith(".")
    ]
    files.sort()
    return files


def get_current_image_name():
    """Gets the filename of the image currently shown on the display."""
    global current_displayed_image
    if current_displayed_image:
        return current_displayed_image
    if STATE_FILE.exists():
        try:
            name = STATE_FILE.read_text().strip()
            if (IMAGES_DIR / name).exists():
                current_displayed_image = name
                return name
        except Exception as e:
            logger.warning(f"Error reading state file: {e}")
    images = get_image_list()
    return images[0] if images else None


def set_current_image_name(name):
    """Updates in-memory and on-disk state of current image."""
    global current_displayed_image
    current_displayed_image = name
    try:
        STATE_FILE.write_text(name)
    except Exception as e:
        logger.warning(f"Error saving state file: {e}")


def process_image(img_input, orientation="horizontal", vertical_mode="rotate_clockwise"):
    """
    Standardizes image for Inky Impressions 7 (800x480):
    1. EXIF orientation correction (for camera photos)
    2. Convert color space to RGB
    3. Handles orientation & vertical framing:
       - If orientation is 'vertical':
         - 'rotate_clockwise': Rotates 90° clockwise to (800, 480) for upright frame.
         - 'rotate_counterclockwise': Rotates 90° counter-clockwise to (800, 480).
         - 'fit_letterbox': Centers the vertical artwork on 800x480 with neat side borders.
       - If orientation is 'square':
         - Centers the square image on 800x480 with neat side borders.
       - If orientation is 'horizontal':
         - Standardizes to (800, 480).
    4. Guarantees output is exactly (800, 480) RGB.
    """
    if hasattr(img_input, "read"):
        image = Image.open(img_input)
    elif isinstance(img_input, bytes):
        image = Image.open(io.BytesIO(img_input))
    else:
        image = Image.open(img_input)

    # 1. Correct EXIF orientation (if camera photo)
    image = ImageOps.exif_transpose(image)

    # 2. Convert to RGB
    if image.mode != "RGB":
        image = image.convert("RGB")

    target_w, target_h = TARGET_RESOLUTION  # (800, 480)

    # 3. Handle special framing modes
    if orientation == "vertical":
        if vertical_mode == "fit_letterbox":
            canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
            img_copy = image.copy()
            resample_filter = getattr(Image, "Resampling", Image).LANCZOS
            img_copy.thumbnail((target_w, target_h), resample=resample_filter)
            offset_x = (target_w - img_copy.width) // 2
            offset_y = (target_h - img_copy.height) // 2
            canvas.paste(img_copy, (offset_x, offset_y))
            image = canvas
        else:
            # Stand upright: the right side of the frame is the bottom when standing vertically
            # rotate(90, expand=True) rotates counter-clockwise so the bottom maps to the physical right (x=799)
            image = image.rotate(90, expand=True)
    elif orientation == "square":
        canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
        img_copy = image.copy()
        resample_filter = getattr(Image, "Resampling", Image).LANCZOS
        img_copy.thumbnail((target_w, target_h), resample=resample_filter)
        offset_x = (target_w - img_copy.width) // 2
        offset_y = (target_h - img_copy.height) // 2
        canvas.paste(img_copy, (offset_x, offset_y))
        image = canvas

    # Final guarantee: if dimensions are not exactly 800x480, crop/resize to (800, 480)
    if image.size != (target_w, target_h):
        img_aspect = image.width / image.height
        target_aspect = target_w / target_h
        if img_aspect < target_aspect:
            multiplier = image.width / target_w
            new_height = target_h * multiplier
            diff = int((image.height - new_height) / 2)
            crop_image = image.crop((0, diff, image.width, diff + int(new_height)))
        else:
            multiplier = image.height / target_h
            new_width = target_w * multiplier
            diff = int((image.width - new_width) / 2)
            crop_image = image.crop((diff, 0, diff + int(new_width), image.height))

        resample_filter = getattr(Image, "Resampling", Image).LANCZOS
        image = crop_image.resize((target_w, target_h), resample=resample_filter)

    return image


def display_image_on_inky(image_filename):
    """
    Safely draws an image from IMAGES_DIR onto the Inky Impressions display
    under display_lock to prevent hardware bus collision.
    """
    filepath = IMAGES_DIR / image_filename
    if not filepath.exists():
        logger.error(f"Cannot display {image_filename}: File does not exist")
        return False

    with display_lock:
        logger.info(f"Writing image to Inky display: {image_filename}")
        try:
            img = Image.open(filepath)
            if img.size != TARGET_RESOLUTION or img.mode != "RGB":
                img = process_image(img)

            if HAVE_INKY:
                inky = get_inky()
                inky.set_image(img, saturation=SATURATION)
                inky.show()
            else:
                logger.info(f"[SIMULATION] Inky display update completed for {image_filename}")

            set_current_image_name(image_filename)
            logger.info(f"Display refreshed successfully with {image_filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh Inky display: {e}", exc_info=True)
            return False


def rotate_to_next_image():
    """Picks the next picture in the sequence and displays it."""
    images = get_image_list()
    if not images:
        logger.info("No images in rotation folder.")
        return

    current = get_current_image_name()
    if len(images) == 1:
        # If there is only one image, only show it if not already displayed
        if current == images[0]:
            logger.info("Single image already on display. Skipping re-flash.")
            return
        next_image = images[0]
    else:
        if current in images:
            curr_idx = images.index(current)
            next_idx = (curr_idx + 1) % len(images)
        else:
            next_idx = 0
        next_image = images[next_idx]

    logger.info(f"Rotating display from '{current}' to '{next_image}'")
    display_image_on_inky(next_image)


def slideshow_worker():
    """
    Background worker thread:
    - Waits for ROTATION_INTERVAL (2 hours).
    - If a new upload occurs, rotation_event is set, waking the worker to
      reset the 2-hour countdown immediately.
    - Otherwise, automatically advances to the next picture every 2 hours.
    """
    logger.info(
        f"Slideshow rotation worker active. Interval: {ROTATION_INTERVAL}s "
        f"({ROTATION_INTERVAL / 3600:.1f} hours)"
    )
    # Wait briefly for server startup
    time.sleep(3)

    # Initial check: if there are pictures and none currently active, display the first
    images = get_image_list()
    current = get_current_image_name()
    if images and not current:
        display_image_on_inky(images[0])

    while not stop_slideshow.is_set():
        # Wait up to ROTATION_INTERVAL or until woken up by an upload / manual display
        interrupted = rotation_event.wait(timeout=ROTATION_INTERVAL)
        if stop_slideshow.is_set():
            break

        if interrupted:
            # An upload or manual switch happened: reset timer and wait full interval
            logger.info("Slideshow timer reset following user update.")
            rotation_event.clear()
            continue

        # 2 hours elapsed -> rotate to next image!
        logger.info("2-hour rotation interval reached. Transitioning to next picture...")
        rotate_to_next_image()


# Routes
@app.route("/", methods=("GET", "POST"))
def index():
    if request.method == "POST":
        if "img" not in request.files:
            flash("No file part in upload request.")
            return redirect(request.url)

        file = request.files["img"]
        if file.filename == "":
            flash("No image selected.")
            return redirect(request.url)

        raw_stem = Path(file.filename).stem or "picture"
        ext = Path(file.filename).suffix.lower()
        if not ext or ext == ".blob":
            ext = ".jpg"

        if ext not in ALLOWED_EXTENSIONS:
            flash(f"Unsupported file format '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
            return redirect(request.url)

        orientation = request.form.get("orientation", "horizontal")
        vertical_mode = request.form.get("vertical_mode", "rotate_clockwise")

        try:
            # 1. Process image: EXIF transpose, RGB, orientation, interactive crop framing
            processed = process_image(file, orientation=orientation, vertical_mode=vertical_mode)

            # 2. Generate unique filename preserving timestamp and original clean name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            clean_stem = secure_filename(raw_stem) or "picture"
            saved_filename = f"{timestamp}_{clean_stem}.jpg"
            saved_path = IMAGES_DIR / saved_filename

            # 3. Save optimized JPEG
            processed.save(saved_path, "JPEG", quality=95)
            logger.info(f"Saved new image: {saved_filename} (orientation={orientation}, mode={vertical_mode})")

            # 4. Display immediately on Inky and reset 2-hour rotation timer in background
            def display_and_signal():
                display_image_on_inky(saved_filename)
                rotation_event.set()

            threading.Thread(target=display_and_signal, daemon=True).start()
            return redirect(url_for("done"))

        except Exception as e:
            logger.error(f"Error handling upload: {e}", exc_info=True)
            flash(f"Could not process image: {e}")
            return redirect(request.url)

    images = get_image_list()
    current_image = get_current_image_name()
    return render_template(
        "index.html",
        image_count=len(images),
        current_image=current_image,
        interval_hours=round(ROTATION_INTERVAL / 3600, 1),
    )


@app.route("/done")
def done():
    return render_template("done.html")


@app.route("/gallery")
def gallery():
    images = get_image_list()
    current_image = get_current_image_name()
    return render_template(
        "gallery.html",
        images=images,
        current_image=current_image,
        interval_hours=round(ROTATION_INTERVAL / 3600, 1),
    )


@app.route("/display/<filename>", methods=["POST"])
def force_display(filename):
    safe_name = secure_filename(filename)
    filepath = IMAGES_DIR / safe_name
    if filepath.exists():
        def display_and_signal():
            display_image_on_inky(safe_name)
            rotation_event.set()

        threading.Thread(target=display_and_signal, daemon=True).start()
        flash(f"Displaying '{safe_name}' on the frame.")
    else:
        flash("Image not found.")
    return redirect(url_for("gallery"))


@app.route("/delete/<filename>", methods=["POST"])
def delete_image(filename):
    safe_name = secure_filename(filename)
    filepath = IMAGES_DIR / safe_name
    if filepath.exists():
        try:
            filepath.unlink()
            global current_displayed_image
            if current_displayed_image == safe_name:
                current_displayed_image = None
                if STATE_FILE.exists():
                    STATE_FILE.unlink()
            flash(f"Removed '{safe_name}' from the rotation.")
        except Exception as e:
            flash(f"Error deleting image: {e}")
    else:
        flash("Image not found.")
    return redirect(url_for("gallery"))


@app.route("/images/<filename>")
def serve_image(filename):
    safe_name = secure_filename(filename)
    return send_from_directory(IMAGES_DIR, safe_name)


@app.route("/favicon.ico")
def favicon():
    # Return 204 No Content so browsers don't loop on missing favicon
    return ("", 204)


# Captive portal probe redirects (for automatic popup on Android, iOS, Windows, Mac)
@app.route("/generate_204")
@app.route("/gen_204")
@app.route("/hotspot-detect.html")
@app.route("/canonical.html")
@app.route("/ncsi.txt")
@app.route("/connecttest.txt")
@app.route("/redirect")
def captive_portal():
    return redirect("http://192.168.4.1/")


@app.errorhandler(404)
def handle_404(e):
    # Never redirect static assets or common browser probe files to avoid ERR_TOO_MANY_REDIRECTS
    path = request.path.lower()
    if path.endswith((".ico", ".png", ".jpg", ".jpeg", ".css", ".js", ".map", ".json", ".txt")):
        return ("Not Found", 404)

    host = request.host.split(":")[0]
    if host in {"192.168.4.1", "rpizero.local", "127.0.0.1", "localhost"}:
        return redirect(url_for("index"))
    return redirect("http://192.168.4.1/")


# Start the slideshow worker thread once
if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
    slideshow_thread = threading.Thread(target=slideshow_worker, daemon=True)
    slideshow_thread.start()


if __name__ == "__main__":
    from werkzeug.serving import run_simple

    # Run on both port 5000 and port 80 so all URLs work
    def run_port_5000():
        try:
            logger.info("Serving on http://0.0.0.0:5000")
            run_simple("0.0.0.0", 5000, app, threaded=True)
        except Exception as e:
            logger.error(f"Error serving on port 5000: {e}")

    thread_5000 = threading.Thread(target=run_port_5000, daemon=True)
    thread_5000.start()

    try:
        logger.info("Serving on http://0.0.0.0:80")
        run_simple("0.0.0.0", 80, app, threaded=True)
    except Exception as e:
        logger.warning(f"Could not bind port 80 ({e}). Port 5000 remains active.")
        thread_5000.join()

