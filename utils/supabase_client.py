import os
from supabase import create_client, Client

_supabase: Client = None

def init_supabase() -> Client:
    global _supabase
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
    _supabase = create_client(url, key)
    return _supabase

def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = init_supabase()
    return _supabase
