import json
import os
import boto3
import requests
import time
from datetime import datetime, timedelta
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed

dynamodb = boto3.resource('dynamodb')
secrets_client = boto3.client('secretsmanager')

TRAVEL_INDEX_TABLE = os.environ['TRAVEL_INDEX_TABLE']
SECRETS_ARN = os.environ['SECRETS_ARN']
CACHE_TTL_HOURS = 24

# Amadeus API endpoints
AMADEUS_AUTH_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_FLIGHTS_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"


def get_api_keys():
    """Retrieve API keys from Secrets Manager"""
    try:
        response = secrets_client.get_secret_value(SecretId=SECRETS_ARN)
        return json.loads(response['SecretString'])
    except Exception as e:
        print(f"Error retrieving secrets: {str(e)}")
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
        expires_in = result.get('expires_in', 1799)  # Default 30 minutes

        print(f"Access token obtained, expires in {expires_in} seconds")
        return access_token

    except requests.exceptions.RequestException as e:
        print(f"Error getting Amadeus access token: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
        return None
    except Exception as e:
        print(f"Unexpected error in token retrieval: {str(e)}")
        return None


def check_flight_cache(departure_airport, destination_airport):
    """Check DynamoDB cache for existing flight price"""
    try:
        table = dynamodb.Table(TRAVEL_INDEX_TABLE)
        cache_key = f"{departure_airport}|{destination_airport}"

        response = table.get_item(
            Key={
                'user_id': 'flight_cache',
                'timestamp': cache_key
            }
        )

        if 'Item' in response:
            item = response['Item']
            # Check if TTL hasn't expired
            if 'ttl' in item:
                current_time = int(time.time())
                if item['ttl'] > current_time:
                    print(f"Cache hit for {cache_key}")
                    return float(item.get('price', 0))

        print(f"Cache miss for {cache_key}")
        return None
    except Exception as e:
        print(f"Error checking flight cache: {str(e)}")
        return None


def store_flight_cache(departure_airport, destination_airport, price):
    """Store flight price in DynamoDB cache"""
    try:
        table = dynamodb.Table(TRAVEL_INDEX_TABLE)
        cache_key = f"{departure_airport}|{destination_airport}"
        ttl = int(time.time()) + (CACHE_TTL_HOURS * 60 * 60)

        item = {
            'user_id': 'flight_cache',
            'timestamp': cache_key,
            'price': Decimal(str(price)),
            'ttl': ttl,
            'cached_at': datetime.utcnow().isoformat()
        }

        table.put_item(Item=item)
        print(f"Cached flight price for {cache_key}: €{price}")
        return True
    except Exception as e:
        print(f"Error storing flight cache: {str(e)}")
        return False


def search_flight_price(access_token, departure_airport, destination_airport):
    """Search for round-trip flight price using Amadeus API"""
    try:
        # Calculate dates: departure in 7 days, return in 14 days
        today = datetime.utcnow()
        departure_date = (today + timedelta(days=7)).strftime('%Y-%m-%d')
        return_date = (today + timedelta(days=14)).strftime('%Y-%m-%d')

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-HTTP-Method-Override": "GET"
        }

        # Build request body for round-trip flight
        payload = {
            "currencyCode": "EUR",
            "originDestinations": [
                {
                    "id": "1",
                    "originLocationCode": departure_airport,
                    "destinationLocationCode": destination_airport,
                    "departureDateTimeRange": {
                        "date": departure_date
                    }
                },
                {
                    "id": "2",
                    "originLocationCode": destination_airport,
                    "destinationLocationCode": departure_airport,
                    "departureDateTimeRange": {
                        "date": return_date
                    }
                }
            ],
            "travelers": [
                {
                    "id": "1",
                    "travelerType": "ADULT"
                }
            ],
            "sources": ["GDS"],
            "searchCriteria": {
                "maxFlightOffers": 5  # Get top 5 cheapest options
            }
        }

        print(f"Searching flights: {departure_airport} → {destination_airport} → {departure_airport}")
        print(f"Dates: {departure_date} to {return_date}")

        response = requests.post(AMADEUS_FLIGHTS_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()

        # Extract cheapest price from flight offers
        if 'data' in result and len(result['data']) > 0:
            prices = []
            for offer in result['data']:
                if 'price' in offer and 'total' in offer['price']:
                    price = float(offer['price']['total'])
                    prices.append(price)

            if prices:
                cheapest_price = min(prices)
                print(f"Found {len(prices)} offers, cheapest: €{cheapest_price}")
                return cheapest_price
            else:
                print("No valid prices found in flight offers")
                return None
        else:
            print(f"No flight offers found. Response: {result}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error searching flights: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response content: {e.response.text}")
        return None
    except Exception as e:
        print(f"Unexpected error in flight search: {str(e)}")
        return None


def handler(event, context):
    """
    Lambda handler to fetch flight prices for destinations
    Endpoint: POST /flight-prices
    Body: {
        "departure_airport": "MAD",
        "destinations": ["BCN", "PAR", "LON", ...]
    }
    """
    print(f"Flight pricer invoked with event: {json.dumps(event)}")

    # Parse request body
    try:
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})

        departure_airport = body.get('departure_airport', '').strip().upper()
        destinations = body.get('destinations', [])

        if not departure_airport or not destinations:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Missing departure_airport or destinations'
                })
            }

        print(f"Fetching flight prices from {departure_airport} to {len(destinations)} destinations")

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

    # Get API keys
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

    # Get Amadeus access token
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

    # Helper function to fetch price for a single destination
    def fetch_single_destination_price(destination_code):
        """Fetch price for a single destination (cache or API)"""
        destination_code = destination_code.strip().upper()

        # Check cache first
        cached_price = check_flight_cache(departure_airport, destination_code)

        if cached_price is not None:
            return (destination_code, cached_price)

        # Search for flight price
        price = search_flight_price(access_token, departure_airport, destination_code)

        if price is not None:
            # Store in cache
            store_flight_cache(departure_airport, destination_code, price)
            return (destination_code, price)
        else:
            print(f"Warning: Could not find price for {destination_code}")
            return (destination_code, None)

    # Fetch prices in parallel using ThreadPoolExecutor
    flight_prices = {}

    print(f"Starting parallel price fetching for {len(destinations)} destinations...")
    start_time = time.time()

    # Use ThreadPoolExecutor to make parallel API calls
    # Max 10 workers to avoid overwhelming the API
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all tasks
        future_to_dest = {
            executor.submit(fetch_single_destination_price, dest): dest
            for dest in destinations
        }

        # Collect results as they complete
        for future in as_completed(future_to_dest):
            try:
                destination_code, price = future.result()
                flight_prices[destination_code] = price
                print(f"Completed: {destination_code} = €{price if price else 'N/A'}")
            except Exception as e:
                dest = future_to_dest[future]
                print(f"Error fetching price for {dest}: {str(e)}")
                flight_prices[dest.strip().upper()] = None

    elapsed_time = time.time() - start_time
    print(f"Parallel fetching completed in {elapsed_time:.2f} seconds")

    # Return results
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'departure_airport': departure_airport,
            'flight_prices': flight_prices
        })
    }
