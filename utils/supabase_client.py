import os
from supabase import create_client, Client

def get_supabase() -> Client:
    url: str = os.environ.get("SUPABASE_URL", "")
    key: str = os.environ.get("SUPABASE_KEY", "")
    return create_client(url, key)
