import google.generativeai as genai
import os
import time
import pathlib
import platform
from datetime import datetime
from pydantic import BaseModel
from isKeyWordHere import check_containment_probability

import googleAPI

class task(BaseModel):
    title: str
    description: str
    deadline: str
    interlocutor: str

def get_audio_creation_date(file_path):
    """
    Get the creation date of an audio file in natural language.
    
    Args:
        file_path (str): Path to the audio file
    
    Returns:
        str: The creation date in natural language format (e.g., "October 9, 2025 at 5:44 PM")
             Returns None if the file doesn't exist or there's an error
    """
    try:
        if not os.path.exists(file_path):
            return None
        
        stat = os.stat(file_path)
        
        # On Windows, st_ctime is creation time
        # On Unix, st_ctime is the last metadata change time
        if platform.system() == 'Windows':
            creation_time = datetime.fromtimestamp(stat.st_ctime)
        else:
            # On Unix-like systems, try to get birth time if available
            # otherwise fall back to modification time (st_mtime)
            creation_time_timestamp = getattr(stat, 'st_birthtime', stat.st_mtime)
            creation_time = datetime.fromtimestamp(creation_time_timestamp)
        
        # Format in natural language
        return creation_time.strftime("%B %d, %Y at %I:%M %p")
        
    except Exception as e:
        print(f"Error getting file date: {e}")
        return None

def get_audio_creation_datetime(file_path):
    """
    Get the creation datetime of an audio file as a datetime object.
    
    Args:
        file_path (str): Path to the audio file
    
    Returns:
        datetime: The creation datetime object
                  Returns None if the file doesn't exist or there's an error
    """
    try:
        if not os.path.exists(file_path):
            return None
        
        stat = os.stat(file_path)
        
        # On Windows, st_ctime is creation time
        # On Unix, st_ctime is the last metadata change time
        if platform.system() == 'Windows':
            creation_time = datetime.fromtimestamp(stat.st_ctime)
        else:
            # On Unix-like systems, try to get birth time if available
            # otherwise fall back to modification time (st_mtime)
            creation_time_timestamp = getattr(stat, 'st_birthtime', stat.st_mtime)
            creation_time = datetime.fromtimestamp(creation_time_timestamp)
        
        return creation_time
        
    except Exception as e:
        print(f"Error getting file date: {e}")
        return None

# --- API Key Loading Logic ---

GEMINI_API_KEY_FILE = "GEMINI_API_KEY"

# 1. Attempt to load API Key from the local file
key_file_path = pathlib.Path(GEMINI_API_KEY_FILE)

if key_file_path.exists():
    try:
        # Read the key, stripping any leading/trailing whitespace or newlines
        key_from_file = key_file_path.read_text().strip()
        if key_from_file:
            # Set the environment variable 'API_KEY' with the key from the file
            os.environ["API_KEY"] = key_from_file
            genai.configure(api_key=key_from_file)
            print(f"API key successfully loaded from '{GEMINI_API_KEY_FILE}' and configured.")
        else:
            print(f"Warning: '{GEMINI_API_KEY_FILE}' is empty. Checking system environment variable 'API_KEY' instead.")
    except Exception as e:
        print(f"Error reading API key file: {e}. Checking system environment variable 'API_KEY' instead.")
else:
    # If file doesn't exist, try to get from environment variable
    api_key = os.getenv("API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        print("API key loaded from environment variable 'API_KEY'.")
    else:
        print("Error: No API key found. Please create a 'GEMINI_API_KEY' file or set the 'API_KEY' environment variable.")
        exit(1)


# --- Main Script Execution ---



def ask(audio, prompt, ai_model, prompt_index, is_structured=False):
    audio_file_path = pathlib.Path(audio)
    identifier_file_path = pathlib.Path("identifier.m4a")

    if not audio_file_path.exists():
        print(f"Error: File not found at '{audio}'. Please ensure the audio file exists in the current directory.")
        exit()

    print(f"Uploading file: {audio_file_path.name}...")

    audio_file = genai.upload_file(path=audio_file_path)
    identifier_file = genai.upload_file(path=identifier_file_path)

    print(f"Completed upload: {audio_file.name}")

    # WAIT FOR THE FILE TO BE PROCESSED
    print("Waiting for file to finish processing (this may take a few moments)...")
    while audio_file.state.name == "PROCESSING" or identifier_file.state.name == "PROCESSING":
        print("File is still processing...")
        time.sleep(5)
        # Get the latest status of the file.
        audio_file = genai.get_file(name=audio_file.name)
        identifier_file = genai.get_file(name=identifier_file.name)

    if audio_file.state.name == "FAILED":
        raise ValueError("Audio file processing failed.")

    print(f"File is now ACTIVE.")

    model = genai.GenerativeModel(model_name=ai_model)

    print("Sending prompts to Gemini...")

    if is_structured:
        response = model.generate_content(
            [prompt, audio_file, identifier_file],
            request_options={"timeout": 900},
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": list[task],
            }
        )
    else:
        response = model.generate_content([prompt, audio_file, identifier_file], request_options={"timeout": 900})

    genai.delete_file(name=audio_file.name)
    genai.delete_file(name=identifier_file.name)
    print("Cleanup complete.")

    return response


if __name__ == "__main__":
    
    AI_MODEL = "gemini-2.5-flash"

    AUDIO_FILE_PATH = "Taionca meeting.m4a" 

    PROMPTS = [
        {"type": "Feelings", "is_structured": False, "prompt": "Crea una lista de las emociones que manifestó cada interlocutor durante la conversación sin agregar la marca de tiempo del momento en que identificaste la emoción, Utiliza el audio 'identifier.m4a' para identificar el nombre de los interlocutores, si no lo logras enumeralos. Esta resppuesta debe ser en formato markdown en español."},
        {"type": "Resume", "is_structured": False, "prompt": f"Responde en español, generando un resumen ultra compacto, extrayendo y explicando los puntos claves además de identificando las tareas establecidas y su respectiva fecha de cumplimiento que debes expresar de manera absoluta teniendo en cuenta que el audio tuvo lugar en la fecha {get_audio_creation_date(AUDIO_FILE_PATH)} y que se realizan reuniones cada miércoles y que los cierres contables de la empresa son los 15 y último de cada mes. Toda tu respuesta debe ser estructurada en formato markdown utilizando tablas y listas. Utiliza el audio 'identifier.m4a' para identificar el nombre de los interlocutores, si no lo logras enumeralos."},
        {"type": "Tasks", "is_structured": True, "prompt": f"Responde en español, Generando una lista de las tareas establecidas y su respectiva fecha de cumplimiento que debes expresar de manera absoluta teniendo en cuenta que el audio tuvo lugar en la fecha {get_audio_creation_date(AUDIO_FILE_PATH)} y que se realizan reuniones cada miércoles y que los cierres contables de la empresa son los 15 y último de cada mes. Utiliza el audio 'identifier.m4a' para identificar el nombre de los interlocutores, si no lo logras enumeralos."},
    ]
    
    events = []
    creation_dt = get_audio_creation_datetime(AUDIO_FILE_PATH)
    if creation_dt:
        events = googleAPI.getEvent(creation_dt.isoformat(), AUDIO_FILE_PATH.split(".")[0])

    for event in events:
        if check_containment_probability(event[1], AUDIO_FILE_PATH.split(".")[0]) >= 40:
            print(f"Found matching event: {event}")

            for i in range(len(PROMPTS)):
                response = ask(AUDIO_FILE_PATH, PROMPTS[i]["prompt"], AI_MODEL, i, PROMPTS[i]["is_structured"]) 
                if PROMPTS[i]["type"] == "Tasks":
                    print("Detected structured tasks response:")
                else:
                    # Create doc
                    doc_id, doc_url = googleAPI.create_google_doc(f"{ "Emociones " if PROMPTS[i]["type"] == "Feelings" else "Resumen"} "+AUDIO_FILE_PATH.split(".")[0])
                    if not doc_id:
                        break
                    
                    # Add content
                    if not googleAPI.add_content_to_doc(doc_id, response.text):
                        break

                    if googleAPI.attach_doc_to_event(event[2], doc_url, "Feelings " if PROMPTS[i]["type"] == "Feelings" else "Resume"):
                        print(f"Document attached to event successfully: {event}")
            
            break

        else:
            print(f"No significant match for event: {event}")