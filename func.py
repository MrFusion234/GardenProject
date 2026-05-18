import requests
from datetime import datetime, timedelta


def get_agriculture_schedule_free(region, crop_data):
    def get_region_coordinates(region):
        region_coordinates = {
            'москва': (55.7558, 37.6173),
            'санкт-петербург': (59.9343, 30.3351),
            'новосибирск': (55.0084, 82.9357),
            'екатеринбург': (56.8389, 60.6057),
            'казань': (55.8304, 49.0661),
            'краснодар': (45.0355, 38.9753),
            'уфа': (54.7355, 55.9587),
            'ростов-на-дону': (47.2224, 39.7185),
            'сочи': (43.5855, 39.7231),
            'крым': (44.9521, 34.1024)
        }

        region_lower = region.lower()
        return region_coordinates.get(region_lower)

    def get_free_weather_forecast(lat, lon):
        url = f"https://api.open-meteo.com/v1/forecast"
        params = {
            'latitude': lat,
            'longitude': lon,
            'daily': 'temperature_2m_max',
            'timezone': 'auto',
            'forecast_days': 16
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        forecasts = []
        for i in range(len(data['daily']['time'])):
            forecasts.append({
                'date': data['daily']['time'][i],
                'parts': {
                    'day': {
                        'temp_avg': data['daily']['temperature_2m_max'][i]
                    }
                }
            })

        return {'forecasts': forecasts}

    def find_planting_date(crop_data, weather_forecast):
        required_temp = crop_data['required_temperature']

        # Сначала ищем подходящий день
        for forecast in weather_forecast['forecasts']:
            date = forecast['date']
            day_temp = forecast['parts']['day']['temp_avg']

            if day_temp >= required_temp:
                return date

        # Если не нашли - берём самый тёплый день
        warmest = None
        warmest_temp = -100
        for forecast in weather_forecast['forecasts']:
            temp = forecast['parts']['day']['temp_avg']
            if temp > warmest_temp:
                warmest_temp = temp
                warmest = forecast['date']

        if warmest:
            return warmest

        # Абсолютный fallback
        fallback_date = datetime.now() + timedelta(days=14)
        return fallback_date.strftime('%Y-%m-%d')

    def calculate_next_dates(planting_date, crop_data):
        planting_dt = datetime.strptime(planting_date, '%Y-%m-%d')

        next_watering = planting_dt + timedelta(days=crop_data['watering_frequency'])

        next_fertilizing = planting_dt + timedelta(days=crop_data['fertilizing_frequency'])

        harvesting_date = planting_dt + timedelta(days=crop_data['days_to_harvest'])

        return {
            'planting': planting_date,
            'next_watering': next_watering.strftime('%Y-%m-%d'),
            'next_fertilizing': next_fertilizing.strftime('%Y-%m-%d'),
            'harvesting': harvesting_date.strftime('%Y-%m-%d')
        }

    lat, lon = get_region_coordinates(region)
    weather_forecast = get_free_weather_forecast(lat, lon)

    planting_date = find_planting_date(crop_data, weather_forecast)
    schedule = calculate_next_dates(planting_date, crop_data)

    return {
        'crop_name': crop_data['name'],
        'schedule': schedule,
    }
