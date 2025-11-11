import json
import os
import boto3
import requests
from math import radians, cos, sin, asin, sqrt

secrets_client = boto3.client('secretsmanager')

SECRETS_ARN = os.environ['SECRETS_ARN']

# Nominatim API for geocoding (OpenStreetMap)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Amadeus API
AMADEUS_AUTH_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_AIRPORT_URL = "https://test.api.amadeus.com/v1/reference-data/locations/airports"

# Hugging Face API
HF_API_URL = "https://router.huggingface.co/hf-inference/models/mistralai/Mixtral-8x7B-Instruct-v0.1"

# Load local airport dataset
AIRPORTS_DATA = None

def load_airports_data():
    """Load local airports dataset (cached in memory)"""
    global AIRPORTS_DATA
    if AIRPORTS_DATA is None:
        airports_file = os.path.join(os.path.dirname(__file__), 'airports_data.json')
        with open(airports_file, 'r') as f:
            AIRPORTS_DATA = json.load(f)
        print(f"Loaded {len(AIRPORTS_DATA)} airports from local dataset")
    return AIRPORTS_DATA


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    Returns distance in kilometers
    """
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))

    # Radius of earth in kilometers
    r = 6371
    return c * r


def find_nearest_airport_local(latitude, longitude, expected_country_code=None, max_distance_km=500, return_alternatives=False):
    """
    Find nearest airport from local dataset
    Returns airport data with IATA code, name, and coordinates
    If return_alternatives=True, returns list of top 5 nearest airports
    """
    try:
        airports = load_airports_data()

        candidates = []

        for airport in airports:
            distance = haversine_distance(latitude, longitude, airport['lat'], airport['lon'])

            # Apply filters
            if distance > max_distance_km:
                continue

            # Prefer airports in same country
            country_match = not expected_country_code or airport['country'] == expected_country_code

            # Use weighted distance (penalize wrong country by 2x)
            weighted_distance = distance if country_match else distance * 2

            candidates.append({
                'airport_code': airport['iata'],
                'airport_name': airport['name'],
                'latitude': airport['lat'],
                'longitude': airport['lon'],
                'city_name': airport['city'],
                'country_code': airport['country'],
                'distance_km': distance,
                'weighted_distance': weighted_distance
            })

        if not candidates:
            print(f"No airports found in local dataset within {max_distance_km}km")
            return [] if return_alternatives else None

        # Sort by weighted distance
        candidates.sort(key=lambda x: x['weighted_distance'])

        if return_alternatives:
            # Return top 5
            top_airports = candidates[:5]
            print(f"Local dataset found {len(top_airports)} alternative airports")
            for i, apt in enumerate(top_airports):
                print(f"  {i+1}. {apt['airport_code']} - {apt['airport_name']} ({apt['distance_km']:.1f}km)")
            return top_airports
        else:
            # Return only the nearest
            nearest = candidates[0]
            print(f"Local dataset found: {nearest['airport_code']} - {nearest['airport_name']} ({nearest['distance_km']:.1f}km)")
            return nearest

    except Exception as e:
        print(f"Error searching local dataset: {str(e)}")
        return [] if return_alternatives else None


def get_api_keys():
    """Retrieve API keys from Secrets Manager"""
    try:
        response = secrets_client.get_secret_value(SecretId=SECRETS_ARN)
        return json.loads(response['SecretString'])
    except Exception as e:
        print(f"Error retrieving secrets: {str(e)}")
        return None


def geocode_city(city, country):
    """
    Use Nominatim (OpenStreetMap) to geocode a city
    Returns (latitude, longitude, country_code) tuple or None
    """
    try:
        headers = {
            "User-Agent": "TravelHelp/1.0 (AWS Lambda)"
        }

        params = {
            "q": f"{city}, {country}",
            "format": "json",
            "limit": 1
        }

        print(f"Geocoding: {city}, {country}")
        response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        results = response.json()

        if results and len(results) > 0:
            lat = float(results[0]['lat'])
            lon = float(results[0]['lon'])
            # Try multiple ways to get country code
            country_code = results[0].get('address', {}).get('country_code', '').upper()
            if not country_code:
                # Fallback: extract from display_name or other fields
                country_code = results[0].get('country_code', '').upper()
            print(f"Geocoded coordinates: {lat}, {lon}, country: {country_code}")
            return (lat, lon, country_code)
        else:
            print(f"No geocoding results for {city}, {country}")
            return None

    except Exception as e:
        print(f"Error geocoding city: {str(e)}")
        return None


def get_amadeus_access_token(api_key, api_secret):
    """Get Amadeus API access token using client credentials"""
    try:
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "grant_type": "client_credentials",
            "client_id": api_key,
            "client_secret": api_secret
        }

        print("Requesting Amadeus access token...")
        response = requests.post(AMADEUS_AUTH_URL, headers=headers, data=data, timeout=30)
        response.raise_for_status()

        result = response.json()
        access_token = result.get('access_token')
        print("Access token obtained")
        return access_token

    except Exception as e:
        print(f"Error getting Amadeus access token: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
        return None


def find_nearest_airport(access_token, latitude, longitude):
    """
    Call Amadeus Airport Nearest Relevant API
    Returns airport data with IATA code, name, and coordinates
    """
    try:
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "radius": 500,
            "page[limit]": 5,
            "sort": "distance"
        }

        print(f"Searching nearest airport to ({latitude}, {longitude})")
        response = requests.get(AMADEUS_AIRPORT_URL, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        result = response.json()

        if 'data' in result and len(result['data']) > 0:
            # Log all found airports
            print(f"Found {len(result['data'])} airports")
            for idx, apt in enumerate(result['data']):
                distance = apt.get('distance', {}).get('value', 0)
                print(f"  {idx+1}. {apt['iataCode']} - {apt['name']} ({apt['address'].get('cityName')}, {apt['address'].get('countryCode')}) - {distance}km")

            # Pick the first one (closest by distance)
            airport = result['data'][0]

            airport_data = {
                "airport_code": airport['iataCode'],
                "airport_name": airport['name'],
                "detailed_name": airport.get('detailedName', airport['name']),
                "latitude": airport['geoCode']['latitude'],
                "longitude": airport['geoCode']['longitude'],
                "city_name": airport['address']['cityName'],
                "country_code": airport['address']['countryCode'],
                "distance_km": airport.get('distance', {}).get('value', 0)
            }

            print(f"Selected airport: {airport_data['airport_code']} - {airport_data['airport_name']}")
            return airport_data
        else:
            print("No airports found in response")
            return None

    except Exception as e:
        print(f"Error finding nearest airport: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response content: {e.response.text}")
        return None


def resolve_airport_with_llm(hf_api_key, city, country):
    """
    Fallback: Use Hugging Face LLM to resolve airport and coordinates
    Returns airport data with IATA code and coordinates
    """
    try:
        headers = {
            "Authorization": f"Bearer {hf_api_key}",
            "Content-Type": "application/json"
        }

        prompt = f"""You are a travel assistant. Given a city and country, identify the nearest major international airport.

City: {city}
Country: {country}

Return ONLY a JSON object with this exact format (no additional text):
{{"airport_code": "XXX", "airport_name": "Airport Name", "latitude": 00.0000, "longitude": 00.0000}}

Requirements:
- Use the IATA 3-letter airport code
- Airport MUST be in the SAME country as the city
- Provide accurate coordinates for the airport
- Return ONLY valid JSON, no explanations"""

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 150,
                "temperature": 0.1,
                "return_full_text": False
            }
        }

        print(f"Calling LLM fallback for {city}, {country}")
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()

        # Extract the generated text
        if isinstance(result, list) and len(result) > 0:
            generated_text = result[0].get('generated_text', '').strip()
        elif isinstance(result, dict):
            generated_text = result.get('generated_text', '').strip()
        else:
            print(f"Unexpected LLM response format: {result}")
            return None

        print(f"LLM response: {generated_text}")

        # Parse JSON from response
        # Sometimes the model adds extra text, so try to extract JSON
        import re
        json_match = re.search(r'\{.*\}', generated_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            airport_data = json.loads(json_str)

            # Validate required fields
            if all(key in airport_data for key in ['airport_code', 'airport_name', 'latitude', 'longitude']):
                print(f"LLM resolved: {airport_data['airport_code']} - {airport_data['airport_name']}")
                return airport_data
            else:
                print("LLM response missing required fields")
                return None
        else:
            print("Could not extract JSON from LLM response")
            return None

    except Exception as e:
        print(f"Error in LLM fallback: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
        return None


def handler(event, context):
    """
    Lambda handler to resolve user's departure airport using Amadeus API
    Endpoint: POST /resolve-airport
    Body: {"city": "London", "country": "England"}
    """
    print(f"Airport resolver invoked with event: {json.dumps(event)}")

    # Parse request body
    try:
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})

        city = body.get('city', '').strip()
        country = body.get('country', '').strip()

        if not city or not country:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Missing city or country'
                })
            }

        print(f"Resolving airport for: {city}, {country}")

    except Exception as e:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f'Invalid request: {str(e)}'
            })
        }

    # Step 1: Geocode the city to get coordinates
    coords = geocode_city(city, country)
    if not coords:
        return {
            'statusCode': 404,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f'Could not geocode {city}, {country}'
            })
        }

    latitude, longitude, expected_country_code = coords

    # Step 2: Get Amadeus API credentials
    secrets = get_api_keys()
    if not secrets or 'amadeus_api_key' not in secrets or 'amadeus_api_secret' not in secrets:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Failed to retrieve Amadeus API keys'
            })
        }

    # Step 3: Get Amadeus access token
    access_token = get_amadeus_access_token(
        secrets['amadeus_api_key'],
        secrets['amadeus_api_secret']
    )

    if not access_token:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Failed to get Amadeus access token'
            })
        }

    # Step 4: Find nearest airport using Amadeus API (primary)
    airport_data = find_nearest_airport(access_token, latitude, longitude)

    # Step 5: Validate Amadeus result - check if too far or wrong country
    use_llm_fallback = False
    if not airport_data:
        print("Amadeus API returned no airports, trying LLM fallback...")
        use_llm_fallback = True
    elif airport_data.get('distance_km', 0) > 200:
        print(f"Amadeus airport too far ({airport_data['distance_km']}km), trying LLM fallback...")
        use_llm_fallback = True
    elif expected_country_code and airport_data.get('country_code', '').upper() != expected_country_code:
        print(f"Amadeus airport in wrong country ({airport_data.get('country_code')} vs {expected_country_code}), trying LLM fallback...")
        use_llm_fallback = True

    # Step 6: Use local dataset fallback if needed
    if use_llm_fallback:
        print("Falling back to local airport dataset...")
        airport_data = find_nearest_airport_local(latitude, longitude, expected_country_code, max_distance_km=500)

        if not airport_data:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Could not resolve airport using Amadeus API or local dataset'
                })
            }

    # Get alternative airports from local dataset (for fallback if no flights available)
    alternatives = []
    try:
        all_alternatives = find_nearest_airport_local(latitude, longitude, expected_country_code, max_distance_km=500, return_alternatives=True)
        # Filter out the primary airport and take top 3 alternatives
        alternatives = [
            {
                'airport_code': apt['airport_code'],
                'airport_name': apt['airport_name'],
                'distance_km': apt['distance_km'],
                'latitude': apt['latitude'],
                'longitude': apt['longitude']
            }
            for apt in all_alternatives
            if apt['airport_code'] != airport_data['airport_code']
        ][:3]
        print(f"Including {len(alternatives)} alternative airports in response")
    except Exception as e:
        print(f"Error getting alternatives: {str(e)}")

    # Return result (frontend expects this format)
    # Return CITY coordinates (for map marker) + airport code (for flights)
    response_body = {
        'airport_code': airport_data['airport_code'],
        'airport_name': airport_data['airport_name'],
        'city': city,
        'country': country,
        'latitude': latitude,           # CITY coordinates (where user is)
        'longitude': longitude,         # CITY coordinates (where user is)
        'airport_latitude': airport_data['latitude'],    # Airport location (optional)
        'airport_longitude': airport_data['longitude']   # Airport location (optional)
    }

    # Add alternatives if available
    if alternatives:
        response_body['alternatives'] = alternatives

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(response_body)
    }
