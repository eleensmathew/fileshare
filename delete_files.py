from datetime import datetime, timedelta
from supabase_file import create_supabase_client

supabase = create_supabase_client()

def delete_old_files(bucket_name, hours):
    time_threshold = datetime.now() - timedelta(hours=hours)
    response = supabase.storage.from_(bucket_name).list()
    if response.get("error") is not None:
        return response.get("error")
    files = response.get("data")
    for file in files:
        try:
            if file.get("created_at") < time_threshold:
                supabase.storage.from_(bucket_name).remove(file.get("name"))
        except Exception as e:
            print(e)

bucket_name = "file_storage"
hours = 24
delete_old_files(bucket_name, hours)