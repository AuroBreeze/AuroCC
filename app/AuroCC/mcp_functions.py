import requests
import yaml
from config import dev
def weather_api()->dict:
    """
    获取曲阜的天气信息
    """
    
    url = "https://restapi.amap.com/v3/weather/weatherInfo"
    params = {
        "city": "370881",
        "key": dev.AMAP_KEY
    }
    
    response = requests.get(url, params=params).json()
    
    if response.get("status") != "1":
        return response
    return response

if __name__ == "__main__":
    print(weather_api())