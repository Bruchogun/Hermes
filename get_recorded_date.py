from pymediainfo import MediaInfo
from datetime import datetime
import os

def get_media_created_date(file_path):
    try:
        media_info = MediaInfo.parse(file_path)
        
        for track in media_info.tracks:
            if track.track_type == "General":
                if track.recorded_date:
                    return track.recorded_date
                elif track.encoded_date:
                    return track.encoded_date
                elif track.tagged_date:
                    return track.tagged_date
        
        # Fallback to file creation date
        if os.path.exists(file_path):
            file_stat = os.stat(file_path)
            return datetime.fromtimestamp(file_stat.st_ctime)
    except Exception as e:
        print(f"⚠️ Error getting media date: {e}")
    
    # Last resort: current date
    return datetime.now()