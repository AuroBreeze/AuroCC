import requests
import yaml

try:
    with open('_config.yml', 'r',encoding='utf-8') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
except FileNotFoundError:
    print("Config file not found.")
def weather_api()->dict:
    """
    获取曲阜的天气信息
    """
    
    url = "https://restapi.amap.com/v3/weather/weatherInfo"
    params = {
        "city": "370881",
        "key": config["basic_settings"]["Weather_api_key"]
    }
    
    response = requests.get(url, params=params).json()
    
    if response.get("status") != "1":
        return response
    return response

if __name__ == "__main__":
    print(weather_api())