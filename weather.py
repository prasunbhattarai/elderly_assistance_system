import requests
import os

def get_weather(city="Kathmandu"):
    API_KEY = "23ac14c0b98c5a47cc9c48fe49bf0f6b"
    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&units=metric&appid={API_KEY}"
    )
    res = requests.get(url, timeout=5)
    data = res.json()
    temp = data["main"]["temp"]
    condition = data["weather"][0]["description"]

    return f"It is {temp} degree Celsius. The weather is {condition}"

# print(get_weather())