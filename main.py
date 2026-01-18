#!/usr/bin/env python3
"""
Car Dealership Inventory Scraper - Interactive CLI
===================================================
Scrapes vehicle listings from dealership websites and formats for social media

Features:
- Interactive menu-driven interface
- Uses Algolia API (used by DealerInspire sites) for complete inventory
- Extracts: price, year, make, model, trim, mileage, VIN, stock #, photos
- Generates social media posts (Facebook, Instagram, Twitter/X)
- Exports to CSV/JSON
- Search and filter inventory
"""

import json
import csv
import re
import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional, List

import httpx

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
# COLORS AND STYLING
# ═══════════════════════════════════════════════════════════════════════════════

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

    @classmethod
    def disable(cls):
        """Disable colors for non-TTY output"""
        cls.HEADER = cls.BLUE = cls.CYAN = cls.GREEN = ''
        cls.YELLOW = cls.RED = cls.BOLD = cls.DIM = cls.RESET = ''


# Check if stdout supports colors
if not sys.stdout.isatty():
    Colors.disable()


def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')


def print_header(text: str):
    """Print a styled header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'═' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'═' * 60}{Colors.RESET}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.CYAN}ℹ {text}{Colors.RESET}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Vehicle:
    """Represents a vehicle listing"""
    year: str
    make: str
    model: str
    trim: Optional[str] = None
    price: Optional[str] = None
    msrp: Optional[str] = None
    mileage: Optional[str] = None
    exterior_color: Optional[str] = None
    interior_color: Optional[str] = None
    vin: Optional[str] = None
    stock_number: Optional[str] = None
    engine: Optional[str] = None
    transmission: Optional[str] = None
    drivetrain: Optional[str] = None
    fuel_type: Optional[str] = None
    mpg: Optional[str] = None
    photos: List[str] = field(default_factory=list)
    url: Optional[str] = None
    condition: str = "New"
    dealer: Optional[str] = None
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def title(self) -> str:
        parts = [self.year, self.make, self.model]
        if self.trim:
            parts.append(self.trim)
        return " ".join(filter(None, parts))

    def to_dict(self) -> dict:
        d = asdict(self)
        d['title'] = self.title
        return d


# ═══════════════════════════════════════════════════════════════════════════════
# SOCIAL MEDIA FORMATTER
# ═══════════════════════════════════════════════════════════════════════════════

class SocialMediaFormatter:
    """Formats vehicle listings for social media posts"""

    @staticmethod
    def facebook(vehicle: Vehicle) -> str:
        is_new = vehicle.condition.lower() == "new"
        emoji = "🚗" if is_new else "✅"
        condition_label = "NEW" if is_new else vehicle.condition.upper()
        lines = [
            f"{emoji} {condition_label} ARRIVAL! {emoji}",
            "",
            f"✨ {vehicle.title} ✨",
            "",
        ]

        if vehicle.price and vehicle.price != "Call":
            lines.append(f"💰 Price: {vehicle.price}")
        else:
            lines.append("💰 Call for Price!")

        if vehicle.mileage and vehicle.condition.lower() != "new":
            lines.append(f"📍 Mileage: {vehicle.mileage}")
        if vehicle.exterior_color:
            lines.append(f"🎨 Color: {vehicle.exterior_color}")
        if vehicle.dealer:
            lines.append(f"📍 Location: {vehicle.dealer}")

        lines.extend([
            "",
            "📞 Call or stop by today!",
            "🌐 Link in comments 👇",
            "",
            "#Toyota #SandiaToyota #CarDeals #Albuquerque #NewMexico"
        ])

        return "\n".join(lines)

    @staticmethod
    def instagram(vehicle: Vehicle) -> str:
        lines = [
            f"🔥 {vehicle.title} 🔥",
            "",
        ]

        if vehicle.price and vehicle.price != "Call":
            lines.append(f"💵 {vehicle.price}")
        else:
            lines.append("💵 Call for special pricing!")

        make_tag = vehicle.make.replace(' ', '') if vehicle.make else 'Toyota'
        model_tag = vehicle.model.replace(' ', '') if vehicle.model else ''

        lines.extend([
            "",
            "Ready for a test drive? DM us or click the link in bio!",
            "",
            ".",
            ".",
            ".",
            f"#Toyota #ToyotaLife #SandiaToyota #CarShopping",
            f"#Albuquerque #NewMexico #CarDealership",
            f"#{make_tag} #{model_tag} #{vehicle.year}{make_tag}"
        ])

        return "\n".join(lines)

    @staticmethod
    def twitter(vehicle: Vehicle) -> str:
        price_str = f" - {vehicle.price}" if vehicle.price and vehicle.price != "Call" else ""
        is_new = vehicle.condition.lower() == "new"
        # Use CERTIFIED for certified vehicles, PRE-OWNED for others
        if is_new:
            condition = "NEW"
        elif "certified" in vehicle.condition.lower():
            condition = "CERTIFIED"
        else:
            condition = "PRE-OWNED"
        base = f"🚗 {condition}: {vehicle.title}{price_str}"

        model_tag = vehicle.model.replace(' ', '') if vehicle.model else ''
        hashtags = f"\n\n#Toyota #{model_tag} #CarDeals"

        if len(base) + len(hashtags) > 280:
            return base[:280 - len(hashtags) - 3] + "..." + hashtags
        return base + hashtags

    @staticmethod
    def all_formats(vehicle: Vehicle) -> dict:
        return {
            'facebook': SocialMediaFormatter.facebook(vehicle),
            'instagram': SocialMediaFormatter.instagram(vehicle),
            'twitter': SocialMediaFormatter.twitter(vehicle)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SCRAPER ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class AlgoliaInventoryScraper:
    """
    Scrapes inventory from DealerInspire-powered dealership sites
    Uses Algolia search API for complete inventory access
    """

    def __init__(self, site_url: str, data_dir: str = "data"):
        self.site_url = site_url.rstrip('/')
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.vehicles: List[Vehicle] = []
        self.algolia_creds = {'api_key': None, 'app_id': None}
        self.index_name = None

    async def _capture_algolia_creds(self) -> bool:
        """Navigate to site and capture Algolia API credentials"""
        if not PLAYWRIGHT_AVAILABLE:
            print_error("Playwright not available! Run: pip install playwright && playwright install chromium")
            return False

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            inventory_data = []

            async def capture_request(request):
                if "algolia" in request.url:
                    key = request.headers.get('x-algolia-api-key')
                    app = request.headers.get('x-algolia-application-id')
                    if key and app:
                        self.algolia_creds['api_key'] = key
                        self.algolia_creds['app_id'] = app

            async def capture_response(response):
                try:
                    if "algolia" in response.url:
                        body = await response.json()
                        if 'results' in body:
                            for r in body['results']:
                                if r.get('hits') and r.get('index'):
                                    inventory_data.append({
                                        'index': r['index'],
                                        'nbHits': r.get('nbHits', 0)
                                    })
                except:
                    pass

            page.on("request", capture_request)
            page.on("response", capture_response)

            print_info(f"Connecting to {self.site_url}...")
            try:
                await page.goto(f"{self.site_url}/used-vehicles/", wait_until="load", timeout=45000)
            except:
                pass

            await page.wait_for_timeout(10000)

            for i in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)

            await browser.close()

            if inventory_data:
                best = max(inventory_data, key=lambda x: x['nbHits'])
                self.index_name = best['index']
                print_success(f"Found inventory index with {best['nbHits']} vehicles")

            return bool(self.algolia_creds['api_key'] and self.index_name)

    async def _fetch_all_vehicles(self, vehicle_type: str = "all", progress_callback=None) -> List[dict]:
        """Fetch all vehicles from Algolia API"""
        if not self.algolia_creds['api_key']:
            print_error("No API credentials available!")
            return []

        all_hits = []
        page_size = 100

        # Build filter - handle all variations of used/pre-owned/certified
        filters = ""
        if vehicle_type == "new":
            filters = 'type:"New"'
        elif vehicle_type == "used":
            # Include all non-new types: Used, Certified Used, Certified Pre-Owned, Pre-Owned, CPO
            filters = 'NOT type:"New"'

        async with httpx.AsyncClient(timeout=30) as client:
            body = {
                "requests": [{
                    "indexName": self.index_name,
                    "params": f"query=&hitsPerPage=1&page=0" + (f"&filters={filters}" if filters else "")
                }]
            }

            resp = await client.post(
                f"https://{self.algolia_creds['app_id'].lower()}-dsn.algolia.net/1/indexes/*/queries",
                headers={
                    "x-algolia-api-key": self.algolia_creds['api_key'],
                    "x-algolia-application-id": self.algolia_creds['app_id'],
                    "Content-Type": "application/json"
                },
                json=body
            )

            data = resp.json()
            total = data['results'][0].get('nbHits', 0) if data.get('results') else 0

            total_pages = (total // page_size) + 1

            for pg in range(total_pages):
                body = {
                    "requests": [{
                        "indexName": self.index_name,
                        "params": f"query=&hitsPerPage={page_size}&page={pg}" + (f"&filters={filters}" if filters else "")
                    }]
                }

                resp = await client.post(
                    f"https://{self.algolia_creds['app_id'].lower()}-dsn.algolia.net/1/indexes/*/queries",
                    headers={
                        "x-algolia-api-key": self.algolia_creds['api_key'],
                        "x-algolia-application-id": self.algolia_creds['app_id'],
                        "Content-Type": "application/json"
                    },
                    json=body
                )

                data = resp.json()
                if data.get('results') and data['results'][0].get('hits'):
                    hits = data['results'][0]['hits']
                    all_hits.extend(hits)

                    if progress_callback:
                        progress_callback(len(all_hits), total)

                    if len(hits) < page_size:
                        break
                else:
                    break

        return all_hits

    def _convert_to_vehicle(self, hit: dict) -> Vehicle:
        """Convert Algolia hit to Vehicle object"""
        price = hit.get('our_price') or hit.get('price') or hit.get('internetPrice') or hit.get('msrp')
        if price:
            try:
                price = f"${int(float(price)):,}"
            except:
                price = "Call"
        else:
            price = "Call"

        miles = hit.get('miles') or hit.get('odometer') or hit.get('mileage')
        if miles:
            try:
                miles = f"{int(float(miles)):,} mi"
            except:
                miles = str(miles)

        photos = []
        if hit.get('images'):
            photos = hit['images'][:5] if isinstance(hit['images'], list) else []
        elif hit.get('image'):
            photos = [hit['image']]

        # Preserve original condition type (New, Used, Certified Used, etc.)
        raw_type = hit.get('type', 'Used')
        condition = raw_type if raw_type else "Used"

        # Get dealer name from Location field or lightning metadata
        dealer = hit.get('Location')
        if not dealer:
            lightning = hit.get('lightning', {})
            locations = lightning.get('locations', {})
            dealer = locations.get('meta_location')

        return Vehicle(
            year=str(hit.get('year', '')),
            make=hit.get('make', ''),
            model=hit.get('model', ''),
            trim=hit.get('trim', ''),
            price=price,
            msrp=hit.get('msrp'),
            mileage=miles,
            exterior_color=hit.get('ext_color') or hit.get('exteriorColor'),
            interior_color=hit.get('int_color') or hit.get('interiorColor'),
            vin=hit.get('vin'),
            stock_number=hit.get('stock'),
            engine=hit.get('engine'),
            transmission=hit.get('transmission'),
            drivetrain=hit.get('drivetrain'),
            fuel_type=hit.get('fuel'),
            photos=photos,
            url=hit.get('link') or hit.get('url'),
            condition=condition,
            dealer=dealer
        )

    async def scrape_inventory(self, vehicle_type: str = "all") -> List[Vehicle]:
        """Main scrape method"""
        self.vehicles = []

        if not await self._capture_algolia_creds():
            print_error("Failed to capture API credentials!")
            return []

        type_label = {"all": "all", "new": "new", "used": "used"}[vehicle_type]
        print_info(f"Fetching {type_label} inventory...")

        def show_progress(current, total):
            pct = int((current / total) * 100) if total > 0 else 0
            bar_width = 30
            filled = int(bar_width * current / total) if total > 0 else 0
            bar = '█' * filled + '░' * (bar_width - filled)
            print(f"\r  {Colors.CYAN}[{bar}] {pct}% ({current}/{total}){Colors.RESET}", end='', flush=True)

        hits = await self._fetch_all_vehicles(vehicle_type, progress_callback=show_progress)
        print()  # New line after progress bar

        seen_vins = set()
        for hit in hits:
            vin = hit.get('vin')
            if vin and vin not in seen_vins:
                seen_vins.add(vin)
                vehicle = self._convert_to_vehicle(hit)
                self.vehicles.append(vehicle)

        print_success(f"Scraped {len(self.vehicles)} unique vehicles")
        return self.vehicles

    def export_csv(self, filename: str = "inventory.csv") -> Path:
        """Export to CSV"""
        filepath = self.data_dir / filename
        if not self.vehicles:
            print_warning("No vehicles to export")
            return filepath

        rows = [v.to_dict() for v in self.vehicles]
        for row in rows:
            row['photos'] = '|'.join(row.get('photos', []))

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        return filepath

    def export_json(self, filename: str = "inventory.json") -> Path:
        """Export to JSON"""
        filepath = self.data_dir / filename

        data = {
            'scraped_at': datetime.now().isoformat(),
            'source': self.site_url,
            'total_vehicles': len(self.vehicles),
            'vehicles': [v.to_dict() for v in self.vehicles]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        return filepath

    def generate_social_posts(self, filename: str = "social_posts.json") -> Path:
        """Generate social media posts"""
        filepath = self.data_dir / filename

        posts = []
        for v in self.vehicles:
            posts.append({
                'vehicle': v.title,
                'price': v.price,
                'condition': v.condition,
                'dealer': v.dealer,
                'vin': v.vin,
                'url': v.url,
                'photo': v.photos[0] if v.photos else None,
                'posts': SocialMediaFormatter.all_formats(v)
            })

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(posts, f, indent=2)

        return filepath

    def search_vehicles(self, query: str) -> List[Vehicle]:
        """Search vehicles by keyword"""
        query = query.lower()
        results = []
        for v in self.vehicles:
            searchable = f"{v.title} {v.exterior_color or ''} {v.vin or ''}".lower()
            if query in searchable:
                results.append(v)
        return results

    def filter_by_price(self, min_price: int = 0, max_price: int = 999999) -> List[Vehicle]:
        """Filter vehicles by price range"""
        results = []
        for v in self.vehicles:
            if v.price and v.price != "Call":
                try:
                    price_num = int(v.price.replace('$', '').replace(',', ''))
                    if min_price <= price_num <= max_price:
                        results.append(v)
                except:
                    pass
        return results


# ═══════════════════════════════════════════════════════════════════════════════
# INTERACTIVE CLI
# ═══════════════════════════════════════════════════════════════════════════════

class InteractiveCLI:
    """Interactive command-line interface"""

    def __init__(self):
        # Use directory relative to script location
        script_dir = Path(__file__).parent.absolute()
        self.scraper = AlgoliaInventoryScraper(
            site_url="https://www.sandiatoyota.com",
            data_dir=str(script_dir / "data")
        )
        self.running = True

    def print_banner(self):
        """Print welcome banner"""
        clear_screen()
        print(f"""
{Colors.CYAN}{Colors.BOLD}
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   {Colors.YELLOW}🚗  CAR DEALERSHIP INVENTORY SCRAPER  🚗{Colors.CYAN}                  ║
    ║                                                               ║
    ║   {Colors.DIM}Sandia Toyota | Powered by Algolia API Discovery{Colors.CYAN}{Colors.BOLD}         ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
{Colors.RESET}""")

    def print_menu(self):
        """Print main menu"""
        vehicle_count = len(self.scraper.vehicles)
        status = f"{Colors.GREEN}{vehicle_count} vehicles loaded{Colors.RESET}" if vehicle_count > 0 else f"{Colors.DIM}No vehicles loaded{Colors.RESET}"

        print(f"""
  {Colors.BOLD}MAIN MENU{Colors.RESET}                              [{status}]
  {'─' * 55}

  {Colors.YELLOW}[1]{Colors.RESET} Scrape All Inventory
  {Colors.YELLOW}[2]{Colors.RESET} Scrape New Vehicles Only
  {Colors.YELLOW}[3]{Colors.RESET} Scrape Used Vehicles Only

  {Colors.YELLOW}[4]{Colors.RESET} View Inventory
  {Colors.YELLOW}[5]{Colors.RESET} Search Vehicles
  {Colors.YELLOW}[6]{Colors.RESET} Filter by Price

  {Colors.YELLOW}[7]{Colors.RESET} Export to CSV
  {Colors.YELLOW}[8]{Colors.RESET} Export to JSON
  {Colors.YELLOW}[9]{Colors.RESET} Generate Social Media Posts
  {Colors.YELLOW}[0]{Colors.RESET} Export All (CSV + JSON + Social)

  {Colors.YELLOW}[V]{Colors.RESET} View Social Post for Vehicle
  {Colors.YELLOW}[Q]{Colors.RESET} Quit

  {'─' * 55}
""")

    def get_input(self, prompt: str) -> str:
        """Get user input with styled prompt"""
        try:
            return input(f"  {Colors.CYAN}▶{Colors.RESET} {prompt}").strip()
        except (KeyboardInterrupt, EOFError):
            return 'q'

    def display_vehicles(self, vehicles: List[Vehicle], title: str = "INVENTORY", page_size: int = 15):
        """Display vehicles with pagination"""
        if not vehicles:
            print_warning("No vehicles to display")
            return

        total = len(vehicles)
        page = 0
        total_pages = (total + page_size - 1) // page_size

        while True:
            clear_screen()
            print_header(f"{title} ({total} vehicles)")

            start = page * page_size
            end = min(start + page_size, total)

            print(f"  {Colors.DIM}{'#':<4} {'VEHICLE':<35} {'PRICE':<12} {'MILES':<12} {'COND':<6}{Colors.RESET}")
            print(f"  {'─' * 70}")

            for i, v in enumerate(vehicles[start:end], start + 1):
                title_str = v.title[:33] + ".." if len(v.title) > 35 else v.title
                price = v.price or "Call"
                miles = v.mileage or "N/A"
                cond = "New" if v.condition == "New" else "Used"
                cond_color = Colors.GREEN if cond == "New" else Colors.YELLOW

                print(f"  {i:<4} {title_str:<35} {Colors.GREEN}{price:<12}{Colors.RESET} {miles:<12} {cond_color}{cond:<6}{Colors.RESET}")

            print(f"\n  {Colors.DIM}Page {page + 1}/{total_pages}{Colors.RESET}")
            print(f"\n  {Colors.DIM}[N]ext  [P]rev  [B]ack to menu  [#] View details{Colors.RESET}")

            choice = self.get_input("").lower()

            if choice == 'n' and page < total_pages - 1:
                page += 1
            elif choice == 'p' and page > 0:
                page -= 1
            elif choice == 'b' or choice == '':
                break
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < total:
                    self.show_vehicle_detail(vehicles[idx])

    def show_vehicle_detail(self, vehicle: Vehicle):
        """Show detailed view of a vehicle"""
        clear_screen()
        print_header(f"VEHICLE DETAILS")

        print(f"""
  {Colors.BOLD}{Colors.CYAN}{vehicle.title}{Colors.RESET}
  {'─' * 50}

  {Colors.YELLOW}Dealer:{Colors.RESET}         {vehicle.dealer or 'N/A'}
  {Colors.YELLOW}Price:{Colors.RESET}          {vehicle.price or 'Call'}
  {Colors.YELLOW}Condition:{Colors.RESET}      {vehicle.condition}
  {Colors.YELLOW}Mileage:{Colors.RESET}        {vehicle.mileage or 'N/A'}
  {Colors.YELLOW}Exterior:{Colors.RESET}       {vehicle.exterior_color or 'N/A'}
  {Colors.YELLOW}Interior:{Colors.RESET}       {vehicle.interior_color or 'N/A'}
  {Colors.YELLOW}VIN:{Colors.RESET}            {vehicle.vin or 'N/A'}
  {Colors.YELLOW}Stock #:{Colors.RESET}        {vehicle.stock_number or 'N/A'}
  {Colors.YELLOW}URL:{Colors.RESET}            {vehicle.url or 'N/A'}

  {'─' * 50}

  {Colors.BOLD}SOCIAL MEDIA POSTS:{Colors.RESET}

  {Colors.BLUE}━━━ FACEBOOK ━━━{Colors.RESET}
{self._indent_text(SocialMediaFormatter.facebook(vehicle), 2)}

  {Colors.HEADER}━━━ INSTAGRAM ━━━{Colors.RESET}
{self._indent_text(SocialMediaFormatter.instagram(vehicle), 2)}

  {Colors.CYAN}━━━ TWITTER ━━━{Colors.RESET}
{self._indent_text(SocialMediaFormatter.twitter(vehicle), 2)}
""")

        self.get_input("Press Enter to go back...")

    def _indent_text(self, text: str, spaces: int) -> str:
        """Indent text by spaces"""
        indent = ' ' * spaces
        return '\n'.join(indent + line for line in text.split('\n'))

    async def run_scrape(self, vehicle_type: str):
        """Run the scraper"""
        clear_screen()
        type_name = {"all": "All", "new": "New", "used": "Used"}[vehicle_type]
        print_header(f"SCRAPING {type_name.upper()} INVENTORY")

        print()
        await self.scraper.scrape_inventory(vehicle_type)
        print()

        if self.scraper.vehicles:
            print_success(f"Ready! {len(self.scraper.vehicles)} vehicles loaded.")
        else:
            print_error("No vehicles found.")

        self.get_input("\nPress Enter to continue...")

    def run_search(self):
        """Run search"""
        clear_screen()
        print_header("SEARCH VEHICLES")

        if not self.scraper.vehicles:
            print_warning("No vehicles loaded. Please scrape first.")
            self.get_input("\nPress Enter to continue...")
            return

        query = self.get_input("Enter search term (make, model, color, VIN): ")
        if query:
            results = self.scraper.search_vehicles(query)
            self.display_vehicles(results, f"SEARCH: '{query}'")

    def run_price_filter(self):
        """Filter by price"""
        clear_screen()
        print_header("FILTER BY PRICE")

        if not self.scraper.vehicles:
            print_warning("No vehicles loaded. Please scrape first.")
            self.get_input("\nPress Enter to continue...")
            return

        try:
            min_str = self.get_input("Minimum price (default 0): ") or "0"
            max_str = self.get_input("Maximum price (default 999999): ") or "999999"

            min_price = int(min_str.replace('$', '').replace(',', ''))
            max_price = int(max_str.replace('$', '').replace(',', ''))

            results = self.scraper.filter_by_price(min_price, max_price)
            self.display_vehicles(results, f"PRICE: ${min_price:,} - ${max_price:,}")
        except ValueError:
            print_error("Invalid price format")
            self.get_input("\nPress Enter to continue...")

    def run_export(self, export_type: str):
        """Run export"""
        clear_screen()
        print_header("EXPORT DATA")

        if not self.scraper.vehicles:
            print_warning("No vehicles loaded. Please scrape first.")
            self.get_input("\nPress Enter to continue...")
            return

        if export_type in ['csv', 'all']:
            path = self.scraper.export_csv()
            print_success(f"CSV exported to: {path}")

        if export_type in ['json', 'all']:
            path = self.scraper.export_json()
            print_success(f"JSON exported to: {path}")

        if export_type in ['social', 'all']:
            path = self.scraper.generate_social_posts()
            print_success(f"Social posts exported to: {path}")

        self.get_input("\nPress Enter to continue...")

    def view_social_post(self):
        """View social post for specific vehicle"""
        clear_screen()
        print_header("VIEW SOCIAL POST")

        if not self.scraper.vehicles:
            print_warning("No vehicles loaded. Please scrape first.")
            self.get_input("\nPress Enter to continue...")
            return

        # Show first 20 vehicles
        print(f"\n  {Colors.DIM}Recent vehicles:{Colors.RESET}\n")
        for i, v in enumerate(self.scraper.vehicles[:20], 1):
            print(f"  {Colors.YELLOW}[{i}]{Colors.RESET} {v.title} - {v.price}")

        choice = self.get_input("\nEnter vehicle number: ")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(self.scraper.vehicles):
                self.show_vehicle_detail(self.scraper.vehicles[idx])
        except ValueError:
            print_error("Invalid selection")
            self.get_input("\nPress Enter to continue...")

    async def main_loop(self):
        """Main application loop"""
        while self.running:
            self.print_banner()
            self.print_menu()

            choice = self.get_input("Select an option: ").lower()

            if choice == '1':
                await self.run_scrape('all')
            elif choice == '2':
                await self.run_scrape('new')
            elif choice == '3':
                await self.run_scrape('used')
            elif choice == '4':
                self.display_vehicles(self.scraper.vehicles)
            elif choice == '5':
                self.run_search()
            elif choice == '6':
                self.run_price_filter()
            elif choice == '7':
                self.run_export('csv')
            elif choice == '8':
                self.run_export('json')
            elif choice == '9':
                self.run_export('social')
            elif choice == '0':
                self.run_export('all')
            elif choice == 'v':
                self.view_social_post()
            elif choice == 'q':
                clear_screen()
                print(f"\n  {Colors.CYAN}Thanks for using Car Dealership Scraper!{Colors.RESET}\n")
                self.running = False
            else:
                print_error("Invalid option")
                await asyncio.sleep(1)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """Main entry point"""
    # Check for command line args (non-interactive mode)
    if len(sys.argv) > 1:
        vehicle_type = "all"
        for arg in sys.argv[1:]:
            if arg == "--new":
                vehicle_type = "new"
            elif arg == "--used":
                vehicle_type = "used"
            elif arg in ["-h", "--help"]:
                print(f"""
{Colors.BOLD}Car Dealership Inventory Scraper{Colors.RESET}

{Colors.YELLOW}Usage:{Colors.RESET}
  python main.py           # Interactive mode
  python main.py --new     # Scrape new vehicles only
  python main.py --used    # Scrape used vehicles only (includes Certified)
  python main.py --all     # Scrape all vehicles

{Colors.YELLOW}Output:{Colors.RESET}
  data/inventory.csv       - Spreadsheet format
  data/inventory.json      - JSON format
  data/social_posts.json   - Social media posts
""")
                return

        # Non-interactive mode
        print_header("CAR DEALERSHIP SCRAPER")

        script_dir = Path(__file__).parent.absolute()
        scraper = AlgoliaInventoryScraper(
            site_url="https://www.sandiatoyota.com",
            data_dir=str(script_dir / "data")
        )

        await scraper.scrape_inventory(vehicle_type)

        if scraper.vehicles:
            scraper.export_csv()
            scraper.export_json()
            scraper.generate_social_posts()

            print()
            print_success(f"Exported {len(scraper.vehicles)} vehicles to data/")
    else:
        # Interactive mode
        cli = InteractiveCLI()
        await cli.main_loop()


if __name__ == "__main__":
    asyncio.run(main())
