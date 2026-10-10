import os
import json
import urllib.request
import urllib.parse
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VEHICLES_FILE = os.path.join(BASE_DIR, "vehicles.json")
POSTED_FILE = os.path.join(BASE_DIR, "posted_vehicles.json")

# Default Config
CONFIG = {
    "fb_location": "San Jose, California",
    "max_images": 20,
    "post_interval_seconds": 900, # Base interval (15 mins)
    "post_interval_jitter_seconds": 300, # Random variation up to 5 mins
    "clean_title": True
}

def load_posted_vins():
    """Load list of already posted VINs."""
    if os.path.exists(POSTED_FILE):
        try:
            with open(POSTED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {item["vin"]: item for item in data}
        except Exception:
            return {}
    return {}

def save_posted_vin(record):
    """Save newly posted VIN record."""
    current = []
    if os.path.exists(POSTED_FILE):
        try:
            with open(POSTED_FILE, "r", encoding="utf-8") as f:
                current = json.load(f)
        except Exception:
            current = []

    # Update or append
    vin_map = {item["vin"]: item for item in current}
    vin_map[record["vin"]] = record

    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(vin_map.values()), f, indent=2)

def normalize_color(color_str):
    if not color_str:
        return "Black"
    c = color_str.lower()
    for color in ["white", "black", "gray", "silver", "blue", "red", "green", "brown", "tan", "gold", "orange", "yellow", "charcoal"]:
        if color in c:
            return color.capitalize()
    return color_str.split()[0] if color_str else "Black"

def normalize_fuel(fuel_str):
    if not fuel_str:
        return "Gasoline"
    f = fuel_str.lower()
    if "electric" in f:
        return "Electric"
    if "hybrid" in f:
        return "Hybrid"
    if "diesel" in f:
        return "Diesel"
    return "Gasoline"

def normalize_transmission(trans_str, fuel_type):
    if not trans_str or trans_str == "N/A" or fuel_type == "Electric":
        return "Automatic"
    t = trans_str.lower()
    if "manual" in t:
        return "Manual"
    return "Automatic"

def generate_description(v):
    lines = [
        f"🔥 {v.get('year')} {v.get('make')} {v.get('model')} {v.get('trim', '')}".strip(),
        f"💰 Price: ${int(float(v.get('price', 0) or 0)):,}",
        "➕ Dealer fees (not included in listed price):",
        "   • Documentation Processing Charge: $85",
        "   • Electronic Vehicle Registration (EVR): $37",
        "   • Total fees: $122",
        f"📍 Mileage: {int(float(v.get('mileage', 0) or 0)):,} miles",
        f"🎨 Exterior: {v.get('exterior_color', 'N/A')} | Interior: {v.get('interior_color', 'N/A')}",
        f"⚙️ Engine: {v.get('engine', 'N/A')}",
        f"🔑 Stock #: {v.get('stock_number', 'N/A')} | VIN: {v.get('vin', 'N/A')}",
        "",
        "✨ Vehicle Highlights:",
        "- Comprehensive dealer inspection & safety verification",
        "- Clean title & ready for delivery",
        "- Financing options and trade-ins welcome",
        "",
        "📍 Stevens Creek Chevrolet - San Jose, CA",
        "💬 Send us a message today for more details or to schedule a test drive!",
        "",
        "Disclaimer: Listed price does not include the $122 in dealer fees above, or taxes and state fees. Subject to prior sale."
    ]
    return "\n".join(lines)

def load_and_normalize_vehicles():
    """Load vehicles.json and normalize fields for Facebook Marketplace."""
    if not os.path.exists(VEHICLES_FILE):
        return []

    try:
        with open(VEHICLES_FILE, "r", encoding="utf-8") as f:
            raw_vehicles = json.load(f)
    except Exception as e:
        print(f"Error loading {VEHICLES_FILE}: {e}")
        return []

    posted_map = load_posted_vins()
    normalized = []

    for item in raw_vehicles:
        vin = item.get("vin")
        if not vin:
            continue

        fuel_type = normalize_fuel(item.get("fuel_type"))
        ext_color = normalize_color(item.get("exterior_color"))
        int_color = normalize_color(item.get("interior_color"))
        transmission = normalize_transmission(item.get("transmission"), fuel_type)

        raw_mileage = item.get("mileage")
        try:
            mileage = int(raw_mileage) if raw_mileage is not None else 300
        except Exception:
            mileage = 300
        if mileage < 300:
            mileage = 300  # Facebook Marketplace requires >= 300

        photo_url = item.get("photo_url") or ""
        images = item.get("photos") or ([photo_url] if photo_url else [])

        veh = {
            "vin": vin,
            "year": item.get("year", 2024),
            "make": item.get("make", "Chevrolet"),
            "model": item.get("model", ""),
            "trim": item.get("trim", ""),
            "price": float(item.get("price") or 0),
            "mileage": mileage,
            "stock_number": item.get("stock_number", ""),
            "body_style": item.get("body_style") or "SUV",
            "exterior_color": ext_color,
            "raw_exterior_color": item.get("exterior_color", ""),
            "interior_color": int_color,
            "transmission": transmission,
            "fuel_type": fuel_type,
            "condition": "Used",
            "engine": item.get("engine", ""),
            "detail_url": item.get("detail_url", ""),
            "images": images,
            "thumbnail": photo_url,
            "description": generate_description(item),
            "posted": vin in posted_map
        }
        normalized.append(veh)

    return normalized

# ── API ENDPOINTS ────────────────────────────────────────────────────────────

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(CONFIG)

@app.route("/api/stats", methods=["GET"])
def get_stats():
    vehicles = load_and_normalize_vehicles()
    posted_map = load_posted_vins()
    total_posted = sum(1 for v in vehicles if v["vin"] in posted_map)
    total_unposted = len(vehicles) - total_posted

    return jsonify({
        "total_inventory": len(vehicles),
        "total_posted": total_posted,
        "total_unposted": total_unposted,
        "total_sold": 0
    })

@app.route("/api/vehicles", methods=["GET"])
def get_vehicles():
    vehicles = load_and_normalize_vehicles()
    search = request.args.get("search", "").strip().lower()
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 30))

    if search:
        filtered = []
        for v in vehicles:
            match_str = f"{v['year']} {v['make']} {v['model']} {v['trim']} {v['vin']} {v['stock_number']}".lower()
            if search in match_str:
                filtered.append(v)
        vehicles = filtered

    total = len(vehicles)
    total_pages = max(1, (total + per_page - 1) // per_page)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_items = vehicles[start_idx:end_idx]

    return jsonify({
        "vehicles": page_items,
        "total": total,
        "total_pages": total_pages,
        "page": page,
        "per_page": per_page
    })

@app.route("/api/vehicle/<vin>", methods=["GET"])
def get_vehicle_by_vin(vin):
    vehicles = load_and_normalize_vehicles()
    for v in vehicles:
        if v["vin"] == vin:
            return jsonify(v)
    return jsonify({"error": "Vehicle not found"}), 404

@app.route("/api/queue", methods=["GET"])
def get_queue():
    vehicles = load_and_normalize_vehicles()
    unposted = [v for v in vehicles if not v["posted"]]
    return jsonify({"vehicles": unposted})

@app.route("/api/track-posted", methods=["POST"])
def track_posted():
    data = request.get_json(force=True, silent=True) or {}
    vin = data.get("vin")
    if not vin:
        return jsonify({"error": "Missing VIN"}), 400

    save_posted_vin(data)
    print(f"[Tracker] Successfully marked vehicle as posted: {vin} - {data.get('title')}")
    return jsonify({"status": "success", "vin": vin})

@app.route("/api/proxy-image", methods=["GET"])
def proxy_image():
    image_url = request.args.get("url")
    if not image_url:
        return Response("Missing url param", status=400)

    try:
        req = urllib.request.Request(
            image_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.stevenscreekchevy.com/"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            img_data = resp.read()
            return Response(img_data, mimetype=content_type)
    except Exception as e:
        print(f"[Proxy] Error fetching image {image_url}: {e}")
        return Response(f"Error fetching image: {e}", status=502)

@app.route("/api/bot/heartbeat", methods=["POST"])
def bot_heartbeat():
    data = request.get_json(force=True, silent=True) or {}
    # Status ping from Tampermonkey
    return jsonify({"status": "ok", "command": None})

@app.route("/api/bot/log", methods=["POST"])
def bot_log():
    data = request.get_json(force=True, silent=True) or {}
    level = data.get("level", "info")
    message = data.get("message", "")
    print(f"[Bot][{level.upper()}] {message}")
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    print("=" * 65)
    print("🚗 Stevens Creek Chevrolet - Marketplace Automation Server")
    print("📍 Location: San Jose, California")
    print("🌐 Running on http://127.0.0.1:5000")
    print("=" * 65)
    app.run(host="127.0.0.1", port=5000, debug=False)
