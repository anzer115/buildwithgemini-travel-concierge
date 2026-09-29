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

import datetime
import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any
from zoneinfo import ZoneInfo
from google import genai
from google.adk.tools import ToolContext
from google.cloud import firestore, storage
from google.genai import types

PROJECT_ID = "qwiklabs-gcp-01-082e51271375"
BUCKET_NAME = "travel-concierge-assets-qwiklabs-gcp-01-082e51271375"

# Initialize Firestore client using explicit hardcoded project ID
db = firestore.Client(project=PROJECT_ID)
DESTINATIONS_COLLECTION = "destinations"



def search_destinations(
    query: str = "", category: str = "", max_budget_per_day: float = 0.0
) -> list[dict[str, Any]]:
    """Search for destinations in the travel catalog by keyword, category, or daily budget limit.

    Args:
        query: Optional search keyword to match destination name, country, or description.
        category: Optional category filter (e.g. 'Culture & Urban', 'Historical & Nature', 'Beach & Wellness', 'Romance & Art').
        max_budget_per_day: Optional maximum daily budget limit in USD.

    Returns:
        List of matching destination dictionaries.
    """
    try:
        col_ref = db.collection(DESTINATIONS_COLLECTION)
        docs = col_ref.stream()
        results = []

        query_lower = query.lower() if query else ""
        category_lower = category.lower() if category else ""

        for doc in docs:
            data = doc.to_dict()
            data["destination_id"] = doc.id

            if max_budget_per_day > 0 and data.get("avg_cost_per_day_usd", 0) > max_budget_per_day:
                continue

            if category_lower and category_lower not in data.get("category", "").lower():
                continue

            if query_lower:
                text_content = f"{data.get('name', '')} {data.get('country', '')} {data.get('category', '')} {data.get('description', '')}".lower()
                if query_lower not in text_content:
                    continue

            results.append(data)

        return results
    except Exception as e:
        return [{"error": f"Failed to search destinations in Firestore: {str(e)}"}]


def get_destination_details(destination_id: str) -> dict[str, Any]:
    """Retrieve full details for a specific travel destination from Firestore.

    Args:
        destination_id: The ID or name of the destination (e.g., 'tokyo', 'paris', 'bali', 'kyoto').

    Returns:
        Dictionary containing destination details or error message if not found.
    """
    try:
        doc_ref = db.collection(DESTINATIONS_COLLECTION).document(destination_id.lower().replace(" ", "_"))
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
            data["destination_id"] = doc.id
            return data

        # Fallback search by name if document ID match fails
        col_ref = db.collection(DESTINATIONS_COLLECTION)
        for d in col_ref.stream():
            data = d.to_dict()
            if data.get("name", "").lower() == destination_id.lower():
                data["destination_id"] = d.id
                return data

        return {"error": f"Destination '{destination_id}' not found in catalog."}
    except Exception as e:
        return {"error": f"Failed to retrieve destination details from Firestore: {str(e)}"}


def add_destination(
    name: str,
    country: str,
    category: str,
    budget_tier: str,
    avg_cost_per_day_usd: float,
    description: str,
    highlights: list[str],
) -> str:
    """Add a new travel destination to the Firestore catalog.

    Args:
        name: Name of the destination (e.g. 'Rome').
        country: Country where the destination is located (e.g. 'Italy').
        category: Travel category (e.g. 'Culture & Architecture').
        budget_tier: Budget tier description ('Budget', 'Moderate', 'High').
        avg_cost_per_day_usd: Estimated average daily cost in USD.
        description: A brief summary description of the destination.
        highlights: List of top attraction highlight names.

    Returns:
        Success message string with destination ID.
    """
    try:
        doc_id = name.lower().replace(" ", "_")
        doc_ref = db.collection(DESTINATIONS_COLLECTION).document(doc_id)
        
        data = {
            "name": name,
            "country": country,
            "category": category,
            "budget_tier": budget_tier,
            "avg_cost_per_day_usd": avg_cost_per_day_usd,
            "description": description,
            "highlights": highlights,
            "created_at": firestore.SERVER_TIMESTAMP,
        }

        doc_ref.set(data)
        return f"Successfully added destination '{name}' (ID: {doc_id}) to Firestore catalog."
    except Exception as e:
        return f"Error adding destination to Firestore: {str(e)}"


def get_weather(query: str) -> str:
    """Gets real-time current weather conditions and temperature for any destination city or region.

    Args:
        query: The destination city or location name.

    Returns:
        Formatted real-time weather summary string.
    """
    try:
        encoded_query = urllib.parse.quote(query.strip())
        url = f"https://wttr.in/{encoded_query}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        current = data.get("current_condition", [{}])[0]
        temp_c = current.get("temp_C", "N/A")
        temp_f = current.get("temp_F", "N/A")
        desc = current.get("weatherDesc", [{}])[0].get("value", "Clear")
        humidity = current.get("humidity", "N/A")
        wind_mph = current.get("windspeedMiles", "N/A")

        return (
            f"Current live weather in '{query}': {desc}, {temp_c}°C ({temp_f}°F), "
            f"Humidity: {humidity}%, Wind Speed: {wind_mph} mph."
        )
    except Exception as e:
        return f"Could not fetch live weather for '{query}': {str(e)}"



def get_current_time(query: str) -> str:
    """Gets the current local time for a specified city.

    Args:
        query: City name.

    Returns:
        Formatted local time string.
    """
    query_lower = query.lower()
    tz_map = {
        "sf": "America/Los_Angeles",
        "san francisco": "America/Los_Angeles",
        "tokyo": "Asia/Tokyo",
        "kyoto": "Asia/Tokyo",
        "paris": "Europe/Paris",
        "bali": "Asia/Makassar",
    }

    tz_identifier = None
    for k, v in tz_map.items():
        if k in query_lower:
            tz_identifier = v
            break

    if not tz_identifier:
        tz_identifier = "UTC"

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"Current time in '{query}' ({tz_identifier}): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"


def convert_currency(amount: float, from_currency: str = "USD", to_currency: str = "JPY") -> str:
    """Convert an amount from one currency to another using real-time exchange rates.

    Args:
        amount: The monetary amount to convert.
        from_currency: 3-letter source currency code (e.g. 'USD', 'EUR', 'JPY', 'GBP').
        to_currency: 3-letter target currency code (e.g. 'JPY', 'EUR', 'USD', 'IDR').

    Returns:
        Formatted currency conversion result string.
    """
    try:
        from_curr = from_currency.upper().strip()
        to_curr = to_currency.upper().strip()
        url = f"https://open.er-api.com/v6/latest/{from_curr}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        rates = data.get("rates", {})
        if to_curr not in rates:
            return f"Currency code '{to_curr}' is not supported."

        rate = rates[to_curr]
        converted = amount * rate
        return f"{amount:,.2f} {from_curr} = {converted:,.2f} {to_curr} (Exchange Rate: 1 {from_curr} = {rate:.4f} {to_curr})"
    except Exception as e:
        return f"Currency conversion failed: {str(e)}"


def geocode_address(address: str) -> dict[str, Any]:
    """Convert an address or location name into geographic coordinates (latitude and longitude).

    Args:
        address: The address, city, or landmark to geocode (e.g. 'Eiffel Tower, Paris' or 'Kyoto, Japan').

    Returns:
        Dictionary with formatted address and location coordinates (latitude, longitude).
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable not set."}

    try:
        encoded_address = urllib.parse.quote(address.strip())
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        if data.get("status") != "OK" or not data.get("results"):
            return {"error": f"Geocoding failed for '{address}': {data.get('status')}"}

        result = data["results"][0]
        location = result["geometry"]["location"]
        return {
            "address": result.get("formatted_address", address),
            "location": {"latitude": location["lat"], "longitude": location["lng"]},
        }
    except Exception as e:
        return {"error": f"Geocoding failed: {str(e)}"}


def search_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "restaurant",
    radius_meters: float = 2000.0,
) -> list[dict[str, Any]]:
    """Search for nearby places of a given type around coordinates using Places API (New).

    Args:
        latitude: Center latitude coordinate.
        longitude: Center longitude coordinate.
        place_type: Place type filter (e.g. 'restaurant', 'tourist_attraction', 'museum', 'lodging', 'park').
        radius_meters: Search radius in meters (default 2000m).

    Returns:
        List of place dictionaries containing name, address, and location.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY environment variable not set."}]

    try:
        url = "https://places.googleapis.com/v1/places:searchNearby"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
        }
        body = json.dumps(
            {
                "includedTypes": [place_type],
                "maxResultCount": 5,
                "locationRestriction": {
                    "circle": {
                        "center": {"latitude": latitude, "longitude": longitude},
                        "radius": radius_meters,
                    }
                },
            }
        ).encode("utf-8")

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        results = []
        for place in data.get("places", []):
            display_name = place.get("displayName", {}).get("text", "Unknown Place")
            formatted_address = place.get("formattedAddress", "")
            loc = place.get("location", {})
            results.append(
                {
                    "name": display_name,
                    "address": formatted_address,
                    "location": loc,
                }
            )

        return results if results else [{"message": f"No nearby {place_type} places found."}]
    except Exception as e:
        return [{"error": f"Places search failed: {str(e)}"}]


def generate_destination_image(prompt: str, tool_context: ToolContext = None) -> str:
    """Generate a visual image for a travel destination using gemini-3.1-flash-lite-image model.

    Saves the generated image to Playground artifacts and uploads image bytes directly to public GCS bucket.

    Args:
        prompt: Description of the image to generate (e.g. 'Scenic postcard of Mount Fuji during cherry blossom season').
        tool_context: ADK tool context for saving artifacts.

    Returns:
        Public GCS HTTPS URL of the uploaded image.
    """
    try:
        # 1. Generate image using gemini-3.1-flash-lite-image in global region
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
        )

        image_bytes = None
        mime_type = "image/jpeg"
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not image_bytes:
            return f"Error: No image was generated for prompt '{prompt}'."

        ext = "png" if "png" in mime_type else "jpg"
        timestamp = int(time.time())
        filename = f"generated_destination_{timestamp}.{ext}"

        # 2. Save artifact using tool_context.save_artifact if context is present
        if tool_context is not None:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 3. Upload image bytes directly to Cloud Storage bucket (no local file path used)
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob_name = f"destinations/{filename}"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"
        return public_url
    except Exception as e:
        return f"Image generation failed: {str(e)}"


def generate_destination_video(prompt: str, tool_context: ToolContext = None) -> str:
    """Generate a short video for a travel destination or landmark using Google's Omni model (gemini-omni-flash-preview).

    Saves the generated video to Playground artifacts and uploads video bytes directly to public GCS bucket.

    Args:
        prompt: Description of the short video to generate (e.g. 'Short cinematic video of waves crashing on Bali beach at sunset').
        tool_context: ADK tool context for saving artifacts.

    Returns:
        Public GCS HTTPS URL of the uploaded video.
    """
    try:
        # 1. Generate video using gemini-omni-flash-preview in global region
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
        response = client.models.generate_content(
            model="gemini-omni-flash-preview",
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["TEXT", "VIDEO"]),
        )

        video_bytes = None
        mime_type = "video/mp4"
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    video_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "video/mp4"
                    break

        if not video_bytes:
            return f"Error: No video was generated for prompt '{prompt}'."

        ext = "mp4"
        timestamp = int(time.time())
        filename = f"generated_video_{timestamp}.{ext}"

        # 2. Save artifact using tool_context.save_artifact if context is present
        if tool_context is not None:
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 3. Upload video bytes directly to Cloud Storage bucket (no local file path used)
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob_name = f"destinations/{filename}"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"
        return public_url
    except Exception as e:
        return f"Video generation failed: {str(e)}"




