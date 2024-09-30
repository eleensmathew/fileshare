from dotenv import load_dotenv
import os
from supabase import Client, create_client

load_dotenv()

api_url: str = os.getenv("PROJECT_URL")
key: str = os.getenv("API_KEY")

def create_supabase_client():
    supabase: Client = create_client(api_url, key)
    return supabase