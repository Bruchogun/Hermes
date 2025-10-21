import google.generativeai as genai
from google.genai import types
import os
import time
import pathlib
from datetime import datetime
from pydantic import BaseModel
from isKeyWordHere import check_containment_probability
import googleAPI
import json
from get_recorded_date import get_media_created_date as get_audio_creation_date

IDENTIFIER_PATH = "identifier.m4a"

class task(BaseModel):
    title: str
    description: str
    deadline: str
    interlocutor: str

# --- API Key Loading Logic ---

GEMINI_API_KEY_FILE = "GEMINI_API_KEY"

# 1. Attempt to load API Key from the local file
key_file_path = pathlib.Path(GEMINI_API_KEY_FILE)

if key_file_path.exists():
    try:
        key_from_file = key_file_path.read_text().strip()
        if key_from_file:
            os.environ["API_KEY"] = key_from_file
            genai.configure(api_key=key_from_file)
        else:
            print(f"ERROR: '{GEMINI_API_KEY_FILE}' is empty.")
            exit(1)
    except Exception as e:
        print(f"ERROR reading API key file: {e}")
        exit(1)
else:
    api_key = os.getenv("API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
    else:
        print(f"ERROR: No API key found. Create '{GEMINI_API_KEY_FILE}' file or set 'API_KEY' environment variable.")
        exit(1)


# --- Main Script Execution ---



def ask(audio, prompt, ai_model, prompt_index, is_structured=False):
    from google import genai as google_genai
    
    audio_file_path = pathlib.Path(audio)
    
    if not audio_file_path.exists():
        print(f"ERROR: Audio file not found: '{audio}'")
        exit()

    print(f"📤 Uploading: {audio_file_path.name}")

    client = google_genai.Client(api_key=os.environ["API_KEY"])
    
    with open(audio_file_path, 'rb') as f:
        audio_file = client.files.upload(file=f, config={'mime_type': 'audio/mp4'})
    
    with open(IDENTIFIER_PATH, 'rb') as f:
        identifier_file = client.files.upload(file=f, config={'mime_type': 'audio/mp4'})

    # Wait for file processing
    while audio_file.state == "PROCESSING" or identifier_file.state == "PROCESSING":
        time.sleep(5)
        audio_file = client.files.get(name=audio_file.name)
        identifier_file = client.files.get(name=identifier_file.name)

    if audio_file.state == "FAILED":
        raise ValueError("Audio file processing failed.")

    print(f"🤖 Processing with Gemini...")

    if is_structured:
        response = client.models.generate_content(
            model=ai_model,
            contents=[prompt, audio_file, identifier_file],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=list[task]
            )
        )
    else:
        response = client.models.generate_content(
            model=ai_model,
            contents=[prompt, audio_file, identifier_file]
        )

    client.files.delete(name=audio_file.name)
    client.files.delete(name=identifier_file.name)

    return response
            

if __name__ == "__main__":
    
    AI_MODEL = "gemini-2.5-flash"

    # Define prompt templates as functions that take audio_file_path as parameter
    def get_prompts(audio_file_path):
        return [
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
    
    if len(important_task_list_id) == 0:
        print("ERROR: Task lists 'Taionca' or 'University' not found in Google Tasks.")
        exit(1)
    
    print(f"✅ Found {len(important_task_list_id)} task lists")
    
    
    for folder_id in FOLDERS_ID:
        print(f"\n{'='*60}\n📁 Processing folder: {folder_id[:20]}...\n{'='*60}")
        
        for audio in googleAPI.list_files_in_folder(folder_id):
            print(f"\n🎵 Processing: {audio['name']}")
            
            googleAPI.download_file_from_drive(audio['id'], audio['name'])
            audio_file_path = audio['name']

            events = []
            creation_dt = get_audio_creation_date(audio_file_path)
            
            if creation_dt:
                if hasattr(creation_dt, 'isoformat'):
                    events = googleAPI.getEvent(creation_dt.isoformat(), audio_file_path.split(".")[0])
                else:
                    try:
                        dt = datetime.fromisoformat(str(creation_dt).replace('UTC ', '').replace(' UTC', ''))
                        events = googleAPI.getEvent(dt.isoformat(), audio_file_path.split(".")[0])
                    except:
                        print(f"⚠️ Could not parse date: {creation_dt}")
            
            if len(events) == 0:
                print(f"⚠️ No matching calendar events found, skipping...")
                os.remove(audio_file_path)
                continue
            
            print(f"📅 Found {len(events)} calendar event(s)")

            for event in events:
                probability = check_containment_probability(event[1], audio_file_path.split(".")[0])
                
                if probability >= 40:
                    print(f"✅ Matched event: {event[1]} ({probability}%)")

                    PROMPTS = get_prompts(audio_file_path)
                    
                    for i in range(len(PROMPTS)):
                        response = ask(audio_file_path, PROMPTS[i]["prompt"], AI_MODEL, i, PROMPTS[i]["is_structured"]) 
                        
                        if PROMPTS[i]["type"] == "Tasks":
                            response_text = response.text
                            tasks_data = json.loads(response_text)
                            print(f"✅ Found {len(tasks_data)} tasks")
                            
                            for task_item in tasks_data:
                                target_id = None
                                
                                if folder_id == FOLDERS_ID[0]: # Taionca
                                    for important_list in important_task_list_id:
                                        if important_list["title"] == "Taionca":
                                            target_id = important_list['id']
                                            break
                                    if target_id:
                                        googleAPI.create_task("Auto - "+task_item["title"], task_item["description"], task_item["deadline"], target_id)
                                    else:
                                        print("ERROR: Taionca task list not found")
                                        
                                elif folder_id == FOLDERS_ID[1]: # University
                                    for important_list in important_task_list_id:
                                        if important_list["title"] == "University":
                                            target_id = important_list['id']
                                            break
                                    if target_id:
                                        googleAPI.create_task("Auto - "+audio_file_path.split(".")[0]+" "+task_item["title"], task_item["description"], task_item["deadline"], target_id)
                                    else:
                                        print("ERROR: University task list not found")
                        else:
                            doc_type = "Emociones" if PROMPTS[i]["type"] == "Feelings" else "Resumen"
                            doc_id, doc_url = googleAPI.create_google_doc(f"{doc_type} {audio_file_path.split('.')[0]}")
                            
                            if not doc_id:
                                print(f"❌ Failed to create {doc_type} doc")
                                break
                            
                            if not googleAPI.add_content_to_doc(doc_id, response.text):
                                print(f"❌ Failed to add content to {doc_type} doc")
                                break

                            if googleAPI.attach_doc_to_event(event[2], doc_url, doc_type):
                                print(f"✅ {doc_type} doc attached to calendar event")
                    
                    break

            # Clean up
            googleAPI.delete_file_from_drive(audio['id'])
            os.remove(audio_file_path)
            print(f"🗑️ Cleaned up: {audio['name']}")

    