# env_setup.py
import os
from dotenv import load_dotenv

class Config:
    """
    Configuration class to load environment variables from a .env file.
    """

    # Load environment variables from .env file
    load_dotenv()

    # AWS Credentials
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    REGION_NAME = os.getenv('REGION_NAME', 'ap-northeast-1')

    # OpenWeather API
    API_OPEN_WEATHER = os.getenv('API_OPEN_WEATHER')

    @staticmethod
    def print_env():
        print("Environment variables set successfully:")
        print("AWS_ACCESS_KEY_ID:", Config.AWS_ACCESS_KEY_ID)
        print("REGION_NAME:", Config.REGION_NAME)
        print("API_OPEN_WEATHER:", Config.API_OPEN_WEATHER)
