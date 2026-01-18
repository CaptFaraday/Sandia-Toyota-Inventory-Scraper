# Car Dealership Inventory Scraper

Scrapes vehicle inventory from Sandia Toyota's dealer network (7 dealerships) and generates ready-to-post social media content for Facebook, Instagram, and Twitter.

## Features

- Scrapes 800+ vehicles across 7 dealerships
- Captures dealer name, price, condition, mileage, VIN, colors, and more
- Generates social media posts with proper formatting and hashtags
- Supports New, Used, and Certified Used vehicles
- Interactive CLI with search and filtering
- Exports to CSV, JSON, and social media JSON

## Quick Start

```bash
cd ~/Desktop/car-scraper
source venv/bin/activate
python main.py
```

## Usage

### Interactive Mode (Recommended)
```bash
python main.py
```

Menu options:
- **[1]** Scrape All Inventory (New + Used + Certified)
- **[2]** Scrape New Vehicles Only
- **[3]** Scrape Used Vehicles Only (includes Certified Used)
- **[4]** View Inventory (paginated)
- **[5]** Search Vehicles (by make, model, color, VIN)
- **[6]** Filter by Price Range
- **[7-9]** Export to CSV / JSON / Social Posts
- **[0]** Export All Formats
- **[V]** View Social Post for a Vehicle
- **[Q]** Quit

### Command Line Mode
```bash
python main.py --all      # Scrape all vehicles (813+)
python main.py --new      # New vehicles only (441+)
python main.py --used     # Used + Certified Used (372+)
python main.py --help     # Show help
```

## Dealerships Covered

| Dealership | Inventory | Primary Makes |
|------------|-----------|---------------|
| Group 1 Toyota Albuquerque | ~549 | Toyota (92%) |
| Lexus of Albuquerque | ~73 | Lexus, Toyota |
| Sandia BMW/Mini | ~60 | BMW, MINI |
| Land Rover Albuquerque | ~53 | Land Rover |
| Lexus of Santa Fe | ~34 | Lexus, Toyota |
| Santa Fe BMW | ~28 | BMW |
| Land Rover Santa Fe | ~16 | Land Rover |

## Output Files

All exports saved to `data/` directory:

| File | Description |
|------|-------------|
| `inventory.csv` | Spreadsheet format with all fields |
| `inventory.json` | Full JSON with metadata |
| `social_posts.json` | Ready-to-post social media content |

### Sample Social Post Output

```json
{
  "vehicle": "2024 Toyota Land Cruiser 1958",
  "price": "$59,490",
  "condition": "Certified Used",
  "dealer": "Group 1 Toyota Albuquerque",
  "posts": {
    "facebook": "✅ CERTIFIED USED ARRIVAL! ✅\n\n✨ 2024 Toyota Land Cruiser 1958 ✨\n\n💰 Price: $59,490\n📍 Mileage: 66 mi\n🎨 Color: Black\n📍 Location: Group 1 Toyota Albuquerque\n\n📞 Call or stop by today!\n🌐 Link in comments 👇\n\n#Toyota #SandiaToyota #CarDeals #Albuquerque #NewMexico",
    "instagram": "🔥 2024 Toyota Land Cruiser 1958 🔥\n\n💵 $59,490\n\nReady for a test drive? DM us or click the link in bio!\n\n.\n.\n.\n#Toyota #ToyotaLife #SandiaToyota #CarShopping\n#Albuquerque #NewMexico #CarDealership\n#Toyota #LandCruiser #2024Toyota",
    "twitter": "🚗 CERTIFIED: 2024 Toyota Land Cruiser 1958 - $59,490\n\n#Toyota #LandCruiser #CarDeals"
  }
}
```

## Vehicle Conditions

| Condition | Description | Social Label |
|-----------|-------------|--------------|
| New | Brand new vehicles | "NEW ARRIVAL!" |
| Used | Pre-owned vehicles | "USED ARRIVAL!" |
| Certified Used | CPO vehicles | "CERTIFIED USED ARRIVAL!" |

## Data Fields Captured

- Year, Make, Model, Trim
- Price (sale price or MSRP)
- Condition (New/Used/Certified Used)
- Dealer name
- Mileage
- Exterior & Interior colors
- VIN
- Stock number
- Vehicle URL
- Photos (when available)

## How It Works

1. Connects to sandiatoyota.com
2. Captures Algolia search API credentials from network requests
3. Queries the Algolia API directly for complete inventory
4. Paginates through all results (100 per page)
5. Converts raw data to structured Vehicle objects
6. Generates formatted social media posts
7. Exports to multiple formats

## Requirements

- Python 3.9+
- Chromium browser (installed via Playwright)

## Installation (Fresh Setup)

```bash
# Create project directory
mkdir ~/Desktop/car-scraper
cd ~/Desktop/car-scraper

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

## Dependencies

```
httpx>=0.25.0
playwright>=1.40.0
```

## File Structure

```
car-scraper/
├── main.py              # Main application
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── venv/                # Virtual environment
└── data/
    ├── inventory.csv
    ├── inventory.json
    └── social_posts.json
```

## Tips

- Run `--all` first to get complete inventory
- Use interactive mode to search/filter before exporting
- Social posts are ready to copy-paste to each platform
- The scraper handles rate limiting automatically
- Data refreshes each time you run the scraper
