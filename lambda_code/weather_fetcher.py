import json
import os
import boto3
import requests
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
secrets_client = boto3.client('secretsmanager')
s3_client = boto3.client('s3')

DESTINATIONS_TABLE = os.environ['DESTINATIONS_TABLE']
SECRETS_ARN = os.environ['SECRETS_ARN']
S3_BUCKET = os.environ['S3_BUCKET']


def get_api_keys():
    """Retrieve API keys from Secrets Manager"""
    try:
        response = secrets_client.get_secret_value(SecretId=SECRETS_ARN)
        return json.loads(response['SecretString'])
    except Exception as e:
        print(f"Error retrieving secrets: {str(e)}")
        return None


def fetch_weather_forecast(lat, lon, api_key):
    """
    Fetch 5-day weather forecast from OpenWeatherMap API
    Returns forecast data in 3-hour intervals
    """
    url = f"https://api.openweathermap.org/data/2.5/forecast"
    params = {
        'lat': lat,
        'lon': lon,
        'appid': api_key,
        'units': 'metric'
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather forecast: {str(e)}")
        return None


def calculate_3day_average(forecast_data):
    """
    Calculate 3-day average temperature from forecast data
    Forecast API returns data every 3 hours for 5 days
    We'll use the next 72 hours (3 days) = approximately 24 data points
    """
    if not forecast_data or 'list' not in forecast_data:
        return None

    forecast_list = forecast_data['list']

    # Get forecast for next 3 days (72 hours / 3-hour intervals = 24 entries)
    three_day_forecast = forecast_list[:24]

    if not three_day_forecast:
        return None

    # Extract temperatures
    temperatures = [item['main']['temp'] for item in three_day_forecast]

    # Calculate statistics
    avg_temp = sum(temperatures) / len(temperatures)
    min_temp = min(temperatures)
    max_temp = max(temperatures)

    # Get most common weather description from first day
    descriptions = [item['weather'][0]['description'] for item in three_day_forecast[:8]]  # First 24 hours
    most_common_desc = max(set(descriptions), key=descriptions.count)

    # Calculate average humidity and wind speed
    humidities = [item['main']['humidity'] for item in three_day_forecast]
    wind_speeds = [item['wind']['speed'] for item in three_day_forecast]

    avg_humidity = sum(humidities) / len(humidities)
    avg_wind_speed = sum(wind_speeds) / len(wind_speeds)

    return {
        'avg_temperature': round(avg_temp, 1),
        'min_temperature': round(min_temp, 1),
        'max_temperature': round(max_temp, 1),
        'description': most_common_desc,
        'avg_humidity': round(avg_humidity, 1),
        'avg_wind_speed': round(avg_wind_speed, 1),
        'forecast_period': '3 days'
    }


def convert_to_dynamodb_format(obj):
    """Convert floats to Decimal for DynamoDB"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_to_dynamodb_format(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_dynamodb_format(item) for item in obj]
    return obj


def handler(event, context):
    """
    Lambda handler to fetch weather data for all destinations
    Can be triggered by API Gateway or EventBridge
    """
    print("Starting weather data fetch...")

    # Get API keys
    secrets = get_api_keys()
    if not secrets or 'openweather_api_key' not in secrets:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to retrieve API keys'})
        }

    api_key = secrets['openweather_api_key']

    # Load destinations from S3
    try:
        s3_response = s3_client.get_object(Bucket=S3_BUCKET, Key='static-data/destinations.json')
        destinations_data = json.loads(s3_response['Body'].read().decode('utf-8'))
        destinations = destinations_data['destinations']
    except Exception as e:
        print(f"Error loading destinations: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to load destinations'})
        }

    # Fetch weather for each destination
    table = dynamodb.Table(DESTINATIONS_TABLE)
    results = []

    for destination in destinations:
        city_id = destination['city_id']
        city_name = destination['city']
        lat = destination['coordinates']['lat']
        lon = destination['coordinates']['lon']

        # Fetch 5-day forecast
        forecast_data = fetch_weather_forecast(lat, lon, api_key)

        if forecast_data:
            # Calculate 3-day average
            weather_stats = calculate_3day_average(forecast_data)

            if weather_stats:
                # Update destination with weather data
                item = convert_to_dynamodb_format(destination)
                item['weather'] = convert_to_dynamodb_format({
                    'avg_temperature': weather_stats['avg_temperature'],
                    'min_temperature': weather_stats['min_temperature'],
                    'max_temperature': weather_stats['max_temperature'],
                    'description': weather_stats['description'],
                    'avg_humidity': weather_stats['avg_humidity'],
                    'avg_wind_speed': weather_stats['avg_wind_speed'],
                    'forecast_period': weather_stats['forecast_period'],
                    'last_updated': context.aws_request_id
                })

                try:
                    table.put_item(Item=item)
                    results.append({
                        'city': city_name,
                        'status': 'success',
                        'weather': {
                            'avg_temperature': weather_stats['avg_temperature'],
                            'min_temperature': weather_stats['min_temperature'],
                            'max_temperature': weather_stats['max_temperature'],
                            'description': weather_stats['description']
                        }
                    })
                    print(f"Updated 3-day forecast for {city_name}: {weather_stats['avg_temperature']}°C avg")
                except Exception as e:
                    print(f"Error updating DynamoDB for {city_id}: {str(e)}")
                    results.append({
                        'city': city_name,
                        'status': 'failed',
                        'error': str(e)
                    })
            else:
                results.append({
                    'city': city_name,
                    'status': 'failed',
                    'error': 'Failed to calculate weather statistics'
                })
        else:
            results.append({
                'city': city_name,
                'status': 'failed',
                'error': 'Weather API request failed'
            })

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'message': 'Weather data fetch completed',
            'results': results
        })
    }
