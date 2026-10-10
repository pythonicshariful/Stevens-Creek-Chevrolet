import urllib.request
import json
import time
import os

BASE_URL = "https://www.stevenscreekchevy.com/api/vhcliaa/vehicle-pages/cosmos/srp/vehicles/16823/3165453"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.stevenscreekchevy.com/searchused.aspx"
}

def fetch_all_used_vehicles(output_json="vehicles.json"):
    """
    Fetches all used vehicles from Stevens Creek Chevrolet API and saves to a JSON file.
    """
    all_vehicles = []
    page_number = 1
    page_size = 24
    total_pages = 1

    print("Fetching used vehicles from Stevens Creek Chevrolet API...")

    while page_number <= total_pages:
        display_cards_shown = (page_number - 1) * page_size
        params = (
            f"?host=www.stevenscreekchevy.com"
            f"&baseFilter=dHlwZT0ndSc%3D"
            f"&pt={page_number}"
            f"&pn={page_size}"
            f"&displayCardsShown={display_cards_shown}"
        )
        url = BASE_URL + params
        req = urllib.request.Request(url, headers=HEADERS)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"Error fetching page {page_number}: {e}")
            break

        pagination = data.get("Paging", {}).get("PaginationDataModel", {})
        total_pages = pagination.get("TotalPages", total_pages)
        total_count = pagination.get("TotalCount", 0)

        cards = data.get("DisplayCards", [])
        for card in cards:
            vc = card.get("VehicleCard")
            if vc:
                # Extract photo URL if available
                img_model = vc.get("VehicleImageModel") or {}
                photo_src = img_model.get("VehiclePhotoSrc") or ""
                if photo_src and not photo_src.startswith("http"):
                    photo_src = f"https://www.stevenscreekchevy.com{photo_src}"
                    
                # Extract all photos
                all_photos = []
                carousel = img_model.get("VehicleImageCarouselModel") or {}
                for p in carousel.get("PhotoList", []):
                    if p and not p.startswith("http"):
                        all_photos.append(f"https://www.stevenscreekchevy.com{p}")
                    elif p:
                        all_photos.append(p)

                all_vehicles.append({
                    "vin": vc.get("VehicleVin"),
                    "year": vc.get("VehicleYear"),
                    "make": vc.get("VehicleMake"),
                    "model": vc.get("VehicleModel"),
                    "trim": vc.get("VehicleTrim"),
                    "price": vc.get("VehicleInternetPrice") or vc.get("VehicleMsrp") or vc.get("TaggingPrice"),
                    "mileage": vc.get("VehicleMileage"),
                    "stock_number": vc.get("VehicleStockNumber"),
                    "body_style": vc.get("VehicleBodyStyle"),
                    "exterior_color": vc.get("ExteriorColorLabel"),
                    "interior_color": vc.get("InteriorColorLabel"),
                    "transmission": vc.get("VehicleTransmission"),
                    "drivetrain": vc.get("VehicleDriveTrain"),
                    "engine": vc.get("VehicleEngine"),
                    "fuel_type": vc.get("VehicleFuelType"),
                    "detail_url": vc.get("VehicleDetailUrl"),
                    "photo_url": photo_src,
                    "photos": all_photos
                })

        print(f"Page {page_number}/{total_pages} processed. Retrieved {len(all_vehicles)}/{total_count} vehicles.")
        page_number += 1
        time.sleep(1)

    # Save to JSON file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, output_json)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_vehicles, f, indent=2)

    print(f"\nSuccessfully saved {len(all_vehicles)} vehicles to: {output_path}")
    return all_vehicles

if __name__ == "__main__":
    fetch_all_used_vehicles()
