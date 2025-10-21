from pymediainfo import MediaInfo

def get_media_created_date(file_path):
    media_info = MediaInfo.parse(file_path)
    
    for track in media_info.tracks:
        if track.track_type == "General":
            # Try different possible metadata fields
            if track.encoded_date:
                return track.encoded_date
            elif track.tagged_date:
                return track.tagged_date
            elif track.recorded_date:
                return track.recorded_date
    
    return None

# Example usage
date = get_media_created_date("AMTV.m4a")
print(f"Media created: {date}")