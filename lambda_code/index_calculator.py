import json
import os
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

DESTINATIONS_TABLE = os.environ['DESTINATIONS_TABLE']
FLIGHT_PRICER_FUNCTION = os.environ['FLIGHT_PRICER_FUNCTION']

# Scoring weights
WEATHER_WEIGHT = 0.30
QOL_WEIGHT = 0.30
FLIGHT_WEIGHT = 0.40

# QoL metric weights (sum to 1.0)
QOL_WEIGHTS = {
    'beer_price': 0.10,
    'michelin_restaurants': 0.20,
    'food_quality': 0.25,
    'walkability': 0.15,
    'public_transport': 0.15,
    'safety': 0.15
}


def convert_from_dynamodb_format(obj):
    """Convert Decimal back to float for JSON response"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_from_dynamodb_format(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_from_dynamodb_format(item) for item in obj]
    return obj


def get_all_destinations():
    """Fetch all destinations with weather data from DynamoDB"""
    try:
        table = dynamodb.Table(DESTINATIONS_TABLE)
        response = table.scan()

        destinations = []
        if 'Items' in response:
            for item in response['Items']:
                destinations.append(convert_from_dynamodb_format(item))

        print(f"Retrieved {len(destinations)} destinations from DynamoDB")
        return destinations

    except Exception as e:
        print(f"Error fetching destinations: {str(e)}")
        return []


def get_flight_prices(departure_airport, destination_codes):
    """Get flight prices by invoking flight_pricer Lambda"""
    try:
        payload = {
            'body': json.dumps({
                'departure_airport': departure_airport,
                'destinations': destination_codes
            })
        }

        print(f"Invoking flight pricer for {len(destination_codes)} destinations")
        response = lambda_client.invoke(
            FunctionName=FLIGHT_PRICER_FUNCTION,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        result = json.loads(response['Payload'].read())

        if result.get('statusCode') == 200:
            body = json.loads(result['body'])
            return body.get('flight_prices', {})
        else:
            print(f"Flight pricer returned error: {result}")
            return {}

    except Exception as e:
        print(f"Error getting flight prices: {str(e)}")
        return {}


def calculate_weather_score(weather_data):
    """
    Calculate weather score based on 3-day average temperature
    Optimal temperature: 20°C
    Score = 1 - (abs(temp - 20) / 30)
    Range: 0.0 to 1.0
    """
    if not weather_data or 'avg_temperature' not in weather_data:
        print("Warning: No weather data available, using default score 0.5")
        return 0.5

    avg_temp = weather_data['avg_temperature']
    temp_diff = abs(avg_temp - 20)
    score = max(0.0, 1.0 - (temp_diff / 30))

    print(f"Weather score: temp={avg_temp}°C, score={score:.3f}")
    return score


def calculate_qol_score(qol_data):
    """
    Calculate quality of life score from multiple metrics
    Each metric is normalized to 0-1 and weighted
    """
    if not qol_data:
        print("Warning: No QoL data available, using default score 0.5")
        return 0.5

    # Normalize each metric to 0-1 scale
    metrics = {}

    # Beer price (lower is better, typical range 3-10 EUR)
    beer_price = qol_data.get('beer_price_eur', 6.5)
    metrics['beer_price'] = max(0.0, 1.0 - ((beer_price - 3) / 7))

    # Michelin restaurants (higher is better, typical range 0-150)
    michelin = qol_data.get('michelin_restaurants', 20)
    metrics['michelin_restaurants'] = min(1.0, michelin / 150)

    # Already normalized scores (0-10, convert to 0-1)
    metrics['food_quality'] = qol_data.get('food_quality_score', 7.0) / 10
    metrics['walkability'] = qol_data.get('walkability_score', 7.0) / 10
    metrics['public_transport'] = qol_data.get('public_transport_score', 7.0) / 10
    metrics['safety'] = qol_data.get('safety_score', 7.0) / 10

    # Calculate weighted QoL score
    qol_score = sum(metrics[key] * QOL_WEIGHTS[key] for key in QOL_WEIGHTS)

    print(f"QoL score: {qol_score:.3f} (breakdown: {metrics})")
    return qol_score


def calculate_flight_score(price):
    """
    Calculate flight price score
    Lower price is better
    Score = 1 - ((price - 50) / 950)
    Assumes price range: 50-1000 EUR
    """
    if price is None or price <= 0:
        print("Warning: No valid flight price, using default score 0.3")
        return 0.3

    # Normalize price to 0-1 scale (inverted, lower price = higher score)
    score = max(0.0, min(1.0, 1.0 - ((price - 50) / 950)))

    print(f"Flight score: price=€{price:.2f}, score={score:.3f}")
    return score


def calculate_total_score(weather_score, qol_score, flight_score):
    """
    Calculate total weighted score
    Weather: 30%, QoL: 30%, Flight: 40%
    """
    total = (weather_score * WEATHER_WEIGHT +
             qol_score * QOL_WEIGHT +
             flight_score * FLIGHT_WEIGHT)

    return total


def handler(event, context):
    """
    Lambda handler to calculate travel index scores
    Endpoint: POST /travel-recommendations
    Body: {
        "departure_airport": "MAD"
    }
    Returns top 3 recommended destinations with scores
    """
    print(f"Index calculator invoked with event: {json.dumps(event)}")

    # Parse request body
    try:
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})

        departure_airport = body.get('departure_airport', '').strip().upper()
        alternatives = body.get('alternatives', [])  # Optional alternative airports

        if not departure_airport:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Missing departure_airport'
                })
            }

        print(f"Calculating travel recommendations from {departure_airport}")
        if alternatives:
            print(f"Alternative airports available: {[alt.get('airport_code') for alt in alternatives]}")

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

    # Get all destinations
    destinations = get_all_destinations()

    if not destinations:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Failed to retrieve destinations'
            })
        }

    # Get flight prices for all destinations
    destination_codes = [dest.get('iata_code') for dest in destinations if dest.get('iata_code')]
    flight_prices = get_flight_prices(departure_airport, destination_codes)

    # Check if we got ANY valid flight prices
    valid_prices = {k: v for k, v in flight_prices.items() if v is not None}

    if not valid_prices and alternatives:
        # No prices available from primary airport, try alternatives
        print(f"No flight prices available from {departure_airport}, trying alternatives...")

        for alt in alternatives:
            alt_code = alt.get('airport_code', '').strip().upper()
            if not alt_code:
                continue

            print(f"Trying alternative airport: {alt_code}")
            alt_flight_prices = get_flight_prices(alt_code, destination_codes)
            alt_valid_prices = {k: v for k, v in alt_flight_prices.items() if v is not None}

            if alt_valid_prices:
                print(f"SUCCESS: Found {len(alt_valid_prices)} flight prices from {alt_code}")
                departure_airport = alt_code  # Switch to this airport
                flight_prices = alt_flight_prices
                break

        if not valid_prices:
            print("Warning: No flight prices available from primary or alternative airports")

    # Calculate scores for each destination
    scored_destinations = []

    for destination in destinations:
        city_id = destination.get('city_id')
        city = destination.get('city')
        country = destination.get('country')
        iata_code = destination.get('iata_code')

        # Extract coordinates
        coordinates = destination.get('coordinates', {})
        latitude = coordinates.get('lat')
        longitude = coordinates.get('lon')

        print(f"\nCalculating scores for {city} ({iata_code})...")

        # Get weather data
        weather_data = destination.get('weather')

        # Get QoL data
        qol_data = destination.get('quality_of_life')

        # Get flight price
        flight_price = flight_prices.get(iata_code)

        # Calculate individual scores
        weather_score = calculate_weather_score(weather_data)
        qol_score = calculate_qol_score(qol_data)
        flight_score = calculate_flight_score(flight_price)

        # Calculate total score
        total_score = calculate_total_score(weather_score, qol_score, flight_score)

        scored_destinations.append({
            'city_id': city_id,
            'city': city,
            'country': country,
            'iata_code': iata_code,
            'latitude': latitude,
            'longitude': longitude,
            'scores': {
                'weather_score': round(weather_score, 3),
                'qol_score': round(qol_score, 3),
                'flight_score': round(flight_score, 3),
                'total_score': round(total_score, 3)
            },
            'details': {
                'avg_temperature': weather_data.get('avg_temperature') if weather_data else None,
                'flight_price': flight_price,
                'quality_of_life': qol_data
            }
        })

        print(f"Total score for {city}: {total_score:.3f}")

    # Sort by total score (descending) and get top 3
    scored_destinations.sort(key=lambda x: x['scores']['total_score'], reverse=True)
    top_3 = scored_destinations[:3]

    print(f"\nTop 3 recommendations:")
    for i, dest in enumerate(top_3, 1):
        print(f"{i}. {dest['city']} - Score: {dest['scores']['total_score']:.3f}")

    # Return top 3 recommendations
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'departure_airport': departure_airport,
            'recommendations': top_3,
            'weights': {
                'weather': WEATHER_WEIGHT,
                'qol': QOL_WEIGHT,
                'flight': FLIGHT_WEIGHT
            }
        })
    }
