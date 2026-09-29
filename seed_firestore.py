# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Seed script for Firestore 'destinations' collection."""

from google.cloud import firestore

# Hardcode project ID explicitly as requested
PROJECT_ID = "qwiklabs-gcp-01-082e51271375"

SEED_DESTINATIONS = [
    {
        "id": "tokyo",
        "name": "Tokyo",
        "country": "Japan",
        "category": "Culture & Urban",
        "budget_tier": "Mid-to-High",
        "avg_cost_per_day_usd": 150.0,
        "best_season": "Spring, Autumn",
        "highlights": [
            "Shinjuku Gyoen National Garden",
            "Shibuya Crossing",
            "Tsukiji Outer Market",
            "Senso-ji Temple",
        ],
        "description": "Vibrant metropolis blending ultra-modern skyscrapers, historic temples, culinary innovation, and rich traditional culture.",
    },
    {
        "id": "kyoto",
        "name": "Kyoto",
        "country": "Japan",
        "category": "Historical & Nature",
        "budget_tier": "Moderate",
        "avg_cost_per_day_usd": 120.0,
        "best_season": "Spring, Autumn",
        "highlights": [
            "Fushimi Inari Shrine",
            "Arashiyama Bamboo Grove",
            "Kinkaku-ji (Golden Pavilion)",
            "Gion Geisha District",
        ],
        "description": "Cultural heart of Japan famed for classical Buddhist temples, serene zen gardens, imperial palaces, and geisha traditions.",
    },
    {
        "id": "paris",
        "name": "Paris",
        "country": "France",
        "category": "Romance & Art",
        "budget_tier": "High",
        "avg_cost_per_day_usd": 200.0,
        "best_season": "Spring, Summer",
        "highlights": [
            "Eiffel Tower",
            "Louvre Museum",
            "Montmartre & Sacré-Cœur",
            "Sainte-Chapelle",
            "Seine River Cruise",
        ],
        "description": "Global center for art, fashion, gastronomy, and culture with iconic architecture, historic museums, and romantic boulevards.",
    },
    {
        "id": "bali",
        "name": "Bali",
        "country": "Indonesia",
        "category": "Beach & Wellness",
        "budget_tier": "Budget",
        "avg_cost_per_day_usd": 65.0,
        "best_season": "May to September",
        "highlights": [
            "Ubud Monkey Forest",
            "Tegallalang Rice Terraces",
            "Uluwatu Sea Temple",
            "Seminyak Sunset Beach",
        ],
        "description": "Tropical paradise known for volcanic mountains, iconic rice paddies, sandy beaches, coral reefs, and spiritual wellness retreats.",
    },
    {
        "id": "san_francisco",
        "name": "San Francisco",
        "country": "USA",
        "category": "Urban & Coastal",
        "budget_tier": "High",
        "avg_cost_per_day_usd": 220.0,
        "best_season": "Autumn",
        "highlights": [
            "Golden Gate Bridge",
            "Alcatraz Island",
            "Fisherman's Wharf",
            "Chinatown & Cable Cars",
        ],
        "description": "Iconic West Coast city known for steep rolling hills, cool summer fog, Golden Gate Bridge, and vibrant culinary scene.",
    },
]


def seed_firestore():
    print(f"Connecting to Firestore for project: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection("destinations")

    print("Seeding destinations collection...")
    for item in SEED_DESTINATIONS:
        doc_id = item["id"]
        data = {k: v for k, v in item.items() if k != "id"}
        collection_ref.document(doc_id).set(data)
        print(f"  ✓ Seeded document '{doc_id}' ({item['name']}, {item['country']})")

    print("\nFirestore seeding completed successfully!")


if __name__ == "__main__":
    seed_firestore()
