# tools/weather_tool.py
# WeatherTool ที่ใช้ OpenWeather Geocoding + One Call API 3.0
import requests
from requests.exceptions import RequestException
from env_setup import Config
import os

class WeatherTool:
    @staticmethod
    def get_tool_spec():
        """
        Returns the JSON Schema specification for the Weather tool.
        (ไม่เปลี่ยน)
        """
        return {
            "toolSpec": {
                "name": "Weather_Tool",
                "description": "Get current or daily forecast weather via OpenWeather (supports city/province or lat/lon).",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "latitude": {"type": "string", "description": "Latitude of the location."},
                            "longitude": {"type": "string", "description": "Longitude of the location."},
                            "city": {"type": "string", "description": "City name for OpenWeather geocoding (optional)."},
                            "province": {"type": "string", "description": "Province name (optional). Will be used as 'city' for geocoding)."},
                            "cnt": {"type": "integer", "description": "Number of days for daily forecast (1-16). Optional."}
                        },
                        "required": []
                    }
                },
            }
        }

    @staticmethod
    def _get_api_key():
        # อ่าน API key จาก Colab userdata หรือ environment variable
        return Config.API_OPEN_WEATHER or os.getenv('API_OPEN_WEATHER')

    @staticmethod
    def _geocode_location(name, api_key, limit=1):
        """
        Use OpenWeather Geocoding API to get latitude & longitude for a city/province name.
        Returns dict: {'lat': ..., 'lon': ...} or error dict.
        NOTE: ใช้ /geo/1.0/direct ตามเอกสาร
        """
        base = "https://api.openweathermap.org/geo/1.0/direct"
        params = {"q": name, "limit": limit, "appid": api_key}
        try:
            r = requests.get(base, params=params, timeout=10)
            r.raise_for_status()
            arr = r.json()
            if not arr:
                return {"error": "not_found", "message": f"No geocoding results for '{name}'"}
            first = arr[0]
            return {"lat": first.get("lat"), "lon": first.get("lon"), "raw": first}
        except RequestException as e:
            return {"error": "request_error", "message": str(e)}
        except Exception as e:
            return {"error": type(e).__name__, "message": str(e)}

    @staticmethod
    def _call_daily_forecast(lat, lon, api_key, cnt=3, units="metric", lang="th"):
        """
        Call OpenWeather One Call API 3.0:
        https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude={part}&appid={API key}
        - One Call 3.0 ไม่รับ 'cnt' เป็นพารามิเตอร์; เราจะขอ daily แล้ว slice ผลลัพธ์ตาม cnt (แต่จำกัดสูงสุดเป็น 8)
        - เพื่อประหยัด payload ตั้งค่า exclude เป็น minutely,hourly,alerts (ยังคงได้ current + daily)
        """
        base = "https://api.openweathermap.org/data/3.0/onecall"
        exclude = "minutely,hourly,alerts"
        params = {"lat": lat, "lon": lon, "exclude": exclude, "appid": api_key, "units": units, "lang": lang}
        try:
            r = requests.get(base, params=params, timeout=10)
            # ชี้ชัดกรณี unauthorized (มักเพราะคีย์ไม่มีสิทธิ์ One Call by Call)
            if r.status_code == 401:
                return {"error": "unauthorized", "status_code": 401, "message": "Unauthorized: API key invalid or lacks One Call 3.0 access (One Call by Call subscription required).", "body": r.text}
            if r.status_code == 403:
                return {"error": "forbidden", "status_code": 403, "message": "Forbidden: your API key lacks permission for this endpoint.", "body": r.text}
            r.raise_for_status()
            data = r.json()
            # slice daily (One Call ให้ daily ~ up to 7-8 days) ตาม cnt ที่ผู้เรียกใส่ (จำกัด 1..8)
            try:
                if isinstance(data, dict) and "daily" in data and isinstance(data["daily"], list):
                    cnt_i = int(cnt)
                    if cnt_i < 1:
                        cnt_i = 1
                    if cnt_i > 8:
                        cnt_i = 8
                    data["daily"] = data["daily"][:cnt_i]
            except Exception:
                pass
            return data
        except RequestException as e:
            return {"error": "request_error", "message": str(e)}
        except Exception as e:
            return {"error": type(e).__name__, "message": str(e)}

    @staticmethod
    def _call_current_weather(lat, lon, api_key, units="metric", lang="th"):
        """
        Fallback: call current weather endpoint if daily forecast not available.
        ใช้ endpoint current weather ตามมาตรฐาน: /data/2.5/weather
        """
        base = "https://api.openweathermap.org/data/2.5/weather"
        params = {"lat": lat, "lon": lon, "appid": api_key, "units": units, "lang": lang}
        try:
            r = requests.get(base, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except RequestException as e:
            return {"error": "request_error", "message": str(e)}
        except Exception as e:
            return {"error": type(e).__name__, "message": str(e)}

    @staticmethod
    def _call_timemachine(lat, lon, dt, api_key, units="metric", lang="th"):
        """
        Call: /data/3.0/onecall/timemachine?lat={lat}&lon={lon}&dt={time}&appid={API key}
        dt = unix timestamp (UTC). Data available from 1979-01-01 to 4 days ahead.
        """
        base = "https://api.openweathermap.org/data/3.0/onecall/timemachine"
        params = {"lat": lat, "lon": lon, "dt": int(dt), "appid": api_key, "units": units, "lang": lang}
        try:
            r = requests.get(base, params=params, timeout=12)
            if r.status_code in (401, 403, 429):
                return {"error": "http_error", "status_code": r.status_code, "body": r.text}
            r.raise_for_status()
            return r.json()
        except RequestException as e:
            return {"error": "request_error", "message": str(e)}
        except Exception as e:
            return {"error": type(e).__name__, "message": str(e)}

    @staticmethod
    def _call_day_summary(lat, lon, date_str, api_key, tz=None, units="metric", lang="th"):
        """
        Call: /data/3.0/onecall/day_summary?lat={lat}&lon={lon}&date={YYYY-MM-DD}&appid={API key}
        date available from 1979-01-02 up to 1.5 years ahead.
        Optional tz param: ±HH:MM
        """
        base = "https://api.openweathermap.org/data/3.0/onecall/day_summary"
        params = {"lat": lat, "lon": lon, "date": date_str, "appid": api_key, "units": units, "lang": lang}
        if tz:
            params["tz"] = tz
        try:
            r = requests.get(base, params=params, timeout=12)
            if r.status_code in (401, 403, 429):
                return {"error": "http_error", "status_code": r.status_code, "body": r.text}
            r.raise_for_status()
            return r.json()
        except RequestException as e:
            return {"error": "request_error", "message": str(e)}
        except Exception as e:
            return {"error": type(e).__name__, "message": str(e)}

    @staticmethod
    def _call_overview(lat, lon, api_key, date_str=None, units="metric", lang="th"):
        """
        Call: /data/3.0/onecall/overview?lat={lat}&lon={lon}&date={YYYY-MM-DD}&appid={API key}
        Returns human-readable summary (today or tomorrow). If date omitted -> today.
        """
        base = "https://api.openweathermap.org/data/3.0/onecall/overview"
        params = {"lat": lat, "lon": lon, "appid": api_key, "units": units, "lang": lang}
        if date_str:
            params["date"] = date_str
        try:
            r = requests.get(base, params=params, timeout=12)
            if r.status_code in (401, 403, 429):
                return {"error": "http_error", "status_code": r.status_code, "body": r.text}
            r.raise_for_status()
            return r.json()
        except RequestException as e:
            return {"error": "request_error", "message": str(e)}
        except Exception as e:
            return {"error": type(e).__name__, "message": str(e)}

    @staticmethod
    def fetch_weather_data(input_data):
        """
        New behavior (OpenWeather-based):
         - If 'city' provided -> geocode city -> call daily forecast with cnt (default 3)
         - Else if 'province' provided -> treat as city name for geocoding -> same as above
         - Else if 'latitude' and 'longitude' provided -> call daily forecast directly
         - Else -> return invalid_input
        Returns: {"weather_data": <openweather_json>} or {"error":..., "message":...}
        """
        api_key = WeatherTool._get_api_key()
        if not api_key:
            return {"error": "no_api_key", "message": "OpenWeather API key not configured. Set API_OPEN_WEATHER in Colab userdata or env var."}

        # determine cnt (days) if provided; validate 1..16 (keep backward compatibility, but One Call slice uses max 8)
        cnt = input_data.get("cnt", 3)
        try:
            cnt = int(cnt)
            if cnt < 1:
                cnt = 1
            elif cnt > 16:
                cnt = 16
        except Exception:
            cnt = 3

        # Priority: city -> province -> coords
        city = input_data.get("city")
        province = input_data.get("province")
        lat = input_data.get("latitude")
        lon = input_data.get("longitude")

        # helper to call forecast for given coords
        def _forecast_for_coords(lat_val, lon_val):
            # try One Call endpoint first (ปัจจุบันใช้ URL และ exclude ตามเอกสาร)
            daily = WeatherTool._call_daily_forecast(lat_val, lon_val, api_key, cnt=cnt)
            if isinstance(daily, dict) and daily.get("error"):
                # fallback to current weather
                current = WeatherTool._call_current_weather(lat_val, lon_val, api_key)
                return {"fallback_to_current": True, "current_weather": current, "daily_error": daily}
            else:
                return {"daily_forecast": daily}

        # 1) city provided
        if city:
            ge = WeatherTool._geocode_location(city, api_key)
            if ge.get("error"):
                return {"error": ge.get("error"), "message": ge.get("message")}
            lat_val, lon_val = ge["lat"], ge["lon"]
            res = _forecast_for_coords(lat_val, lon_val)
            return {"weather_data": res, "geocoding": ge.get("raw")}

        # 2) province provided (use geocoding too)
        if province:
            ge = WeatherTool._geocode_location(province, api_key)
            if ge.get("error"):
                return {"error": ge.get("error"), "message": ge.get("message")}
            lat_val, lon_val = ge["lat"], ge["lon"]
            res = _forecast_for_coords(lat_val, lon_val)
            return {"weather_data": res, "geocoding": ge.get("raw")}

        # 3) lat & lon provided
        if lat and lon:
            res = _forecast_for_coords(lat, lon)
            return {"weather_data": res, "coords": {"lat": lat, "lon": lon}}

        # 4) invalid input
        return {"error": "invalid_input", "message": "Please provide 'city' or 'province' or both 'latitude' and 'longitude' in input_data."}
