import google.generativeai as genai
import os
import time
import pathlib
import platform
from datetime import datetime
from pydantic import BaseModel
from isKeyWordHere import check_containment_probability
import googleAPI
import json

IDENTIFIER_PATH = "identifier.m4a"

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
    # Simply upload without additional parameters
    audio_file = genai.upload_file(path=audio_file_path)
    identifier_file = genai.upload_file(path=IDENTIFIER_PATH)

    if not audio_file_path.exists():
        print(f"Error: File not found at '{audio}'. Please ensure the audio file exists in the current directory.")
        exit()

    print(f"Uploading file: {audio_file_path.name}...")

    audio_file = genai.upload_file(path=audio_file_path)
    identifier_file = genai.upload_file(path=IDENTIFIER_PATH)

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


    # with open(f"prompt-{prompt_index+1}.md", "r", encoding="utf-8") as file:
    #     if prompt_index == 2:
    #         response = json.load(file)
    #     else:
    #         response = file.read()
    # return response
            

if __name__ == "__main__":
    
    AI_MODEL = "gemini-2.5-flash"

    audio_file_path = "default" 

    PROMPTS = [
        {"type": "Feelings", "is_structured": False, "prompt": "Crea una lista de las emociones que manifestó cada interlocutor durante la conversación sin agregar la marca de tiempo del momento en que identificaste la emoción, Utiliza el audio 'identifier.m4a' para identificar el nombre de los interlocutores, si no lo logras enumeralos. Esta resppuesta debe ser en formato markdown en español."},
        {"type": "Resume", "is_structured": False, "prompt": f"Responde en español, generando un resumen ultra compacto, extrayendo y explicando los puntos claves además de identificando las tareas establecidas y su respectiva fecha de cumplimiento que debes expresar de manera absoluta teniendo en cuenta que el audio tuvo lugar en la fecha {get_audio_creation_date(audio_file_path)} y que se realizan reuniones cada miércoles y que los cierres contables de la empresa son los 15 y último de cada mes. Toda tu respuesta debe ser estructurada en formato markdown utilizando tablas y listas. Utiliza el audio 'identifier.m4a' para identificar el nombre de los interlocutores, si no lo logras enumeralos."},
        {"type": "Tasks", "is_structured": True, "prompt": f"Responde en español, Generando una lista de las tareas establecidas y su respectiva fecha de cumplimiento que debes expresar de manera absoluta teniendo en cuenta que el audio tuvo lugar en la fecha {get_audio_creation_date(audio_file_path)} y que se realizan reuniones cada miércoles y que los cierres contables de la empresa son los 15 y último de cada mes. Utiliza el audio 'identifier.m4a' para identificar el nombre de los interlocutores, si no lo logras enumeralos. Si identificas una tarea pero no tienes su fecha de cumplimiento, no la incluyas en tu respuesta."},
    ]

    USER = "mauro"
    FOLDERS_ID = ["11vTiK6WAR6jE3gyOg_C5ay-ZpD3rEfLg", # Taionca
                "19f5WZNz6uYSnvbfq3isjIgRTYLWv9Ssk"] # University
    

    
    IMPORTANT_TASK_LISTS = ["Taionca", "University"]
    tasks_lists = googleAPI.list_task_lists()
    important_task_list_id = []
    for task_list in tasks_lists:
        if task_list['title'] in IMPORTANT_TASK_LISTS:
            important_task_list_id.append({"id":task_list['id'], "title":task_list['title']})


    
    
    for folder_id in FOLDERS_ID:
        for audio in googleAPI.list_files_in_folder(folder_id):

            googleAPI.download_file_from_drive(audio['id'], audio['name'])
            audio_file_path = audio['name']

            events = []
            creation_dt = get_audio_creation_datetime(audio_file_path)
            if creation_dt:
                events = googleAPI.getEvent(creation_dt.isoformat(), audio_file_path.split(".")[0])

            for event in events:
                if check_containment_probability(event[1], audio_file_path.split(".")[0]) >= 40:
                    print(f"Found matching event: {event}")

                    for i in range(len(PROMPTS)):
                        response = ask(audio_file_path, PROMPTS[i]["prompt"], AI_MODEL, i, PROMPTS[i]["is_structured"]) 
                        if PROMPTS[i]["type"] == "Tasks":
                            print("Detected structured tasks response:")

                            for task_item in list(response):
                                if task_item["interlocutor"].lower() == USER:
                                    if folder_id == FOLDERS_ID[0]: # Taionca
                                        for important_list in important_task_list_id:
                                            if important_list["title"] == "Taionca":
                                                target_id = important_list['id']
                                        googleAPI.create_task("Auto - "+task_item["title"], task_item["description"], task_item["deadline"], target_id )
                                    elif folder_id == FOLDERS_ID[1]: # University
                                        for important_list in important_task_list_id:
                                            if important_list["title"] == "University":
                                                target_id = important_list['id']
                                        googleAPI.create_task("Auto - "+" "+audio_file_path.split(".")[0]+task_item["title"], task_item["description"], task_item["deadline"], target_id )
                        else:
                            # Create doc
                            doc_id, doc_url = googleAPI.create_google_doc(f"{ "Emociones " if PROMPTS[i]["type"] == "Feelings" else "Resumen"} "+audio_file_path.split(".")[0])
                            if not doc_id:
                                break
                            
                            # Add content
                            if not googleAPI.add_content_to_doc(doc_id, response):
                                break

                            if googleAPI.attach_doc_to_event(event[2], doc_url, "Feelings " if PROMPTS[i]["type"] == "Feelings" else "Resume"):
                                print(f"Document attached to event successfully: {event}")
                    
                    break

                else:
                    print(f"No significant match for event: {event}")

            # googleAPI.delete_file_from_drive(audio['id'])
            os.remove(audio_file_path)

    