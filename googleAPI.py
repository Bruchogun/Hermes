import os.path
import io
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

# If modifying these scopes, delete the file token.json.
# Added Drive scope for the new functions.
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/drive" # Scope for Google Drive
]


def get_credentials():
    """
    Authenticates and returns valid credentials.
    Reuses existing token or prompts for authentication.
    """
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    
    return creds

# --- Existing Functions (Unchanged) ---

def getEvent(target_date, target_name=""):
    creds = get_credentials()
    
    if isinstance(target_date, str):
        target_date = datetime.fromisoformat(target_date.replace('Z', '+00:00'))
    
    target_date = target_date - timedelta(hours=2)
    target_date_str = target_date.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
    
    params = {
        "calendarId": "primary",
        "timeMin": target_date_str,
        "maxResults": 10,
        "singleEvents": True,
        "orderBy": "startTime"
    }
    if target_name:
        params["q"] = target_name
        params["maxResults"] = 1

    try:
        service = build("calendar", "v3", credentials=creds)
        events_result = service.events().list(**params).execute()
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return
        
        simple_events = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            summary = event["summary"]
            simple_events.append([start, summary, event.get("id")])
        
        return simple_events

    except HttpError as error:
        print(f"An error occurred: {error}")

def create_google_doc(title):
    creds = get_credentials()
    try:
        docs_service = build("docs", "v1", credentials=creds)
        print(f"\n📄 Creating a Google Doc titled '{title}'...")
        document = docs_service.documents().create(body={'title': title}).execute()
        doc_id = document.get('documentId')
        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        print(f"✅ Doc created successfully: {doc_url}")
        return doc_id, doc_url
    except HttpError as err:
        print(f"An error occurred while creating doc: {err}")
        return None, None

def add_content_to_doc(doc_id, content):
    creds = get_credentials()
    try:
        docs_service = build("docs", "v1", credentials=creds)
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={
                'requests': [{
                    'insertText': {
                        'location': {'index': 1},
                        'text': content
                    }
                }]
            }
        ).execute()
        print("✅ Content added to the doc.")
        return True
    except HttpError as err:
        print(f"An error occurred while adding content: {err}")
        return False

def attach_doc_to_event(event_id, doc_url, doc_title):
    creds = get_credentials()
    try:
        calendar_service = build("calendar", "v3", credentials=creds)
        print("📎 Attaching the doc to the calendar event...")
        event = calendar_service.events().get(calendarId='primary', eventId=event_id).execute()
        existing_attachments = event.get('attachments', [])
        new_attachment = {
            'fileUrl': doc_url,
            'title': doc_title,
            'mimeType': 'application/vnd.google-apps.document'
        }
        updated_attachments = existing_attachments + [new_attachment]
        body = {'attachments': updated_attachments}
        calendar_service.events().patch(
            calendarId='primary',
            eventId=event_id,
            body=body,
            supportsAttachments=True
        ).execute()
        print("✅ Doc attached successfully.")
        return True
    except HttpError as err:
        print(f"An error occurred while attaching doc: {err}")
        return False

def create_task(title, notes="", deadline=None, task_list_id="@default"):
    creds = get_credentials()
    try:
        deadline1 = datetime.strptime(deadline, "%B %d, %Y")
        due_date = deadline1.strftime("%Y-%m-%d")
        tasks_service = build("tasks", "v1", credentials=creds)
        task_body = {'title': title}
        if notes:
            task_body['notes'] = notes
        if due_date:
            if isinstance(due_date, datetime):
                due_date = due_date.strftime('%Y-%m-%d')
            task_body['due'] = f"{due_date}T00:00:00.000Z"
        
        print(f"📋 Creating task: '{title}'...")
        task = tasks_service.tasks().insert(
            tasklist=task_list_id,
            body=task_body
        ).execute()
        print(f"✅ Task created successfully with ID: {task.get('id')}")
        return task
    except HttpError as err:
        print(f"An error occurred while creating task: {err}")
        pass

# --- ✨ NEW FUNCTIONS ✨ ---

def list_task_lists():
    """Lists the user's task lists from Google Tasks."""
    creds = get_credentials()
    try:
        service = build("tasks", "v1", credentials=creds)
        results = service.tasklists().list(maxResults=10).execute()
        items = results.get("items", [])

        if not items:
            print("No task lists found.")
            return None

        print("\n📋 Your Task Lists:")

        for item in items:
            print(f"- {item['title']} (ID: {item['id']})")

        return items
    except HttpError as err:
        print(f"An error occurred while listing task lists: {err}")
        return None

def list_files_in_folder(folder_id):
    """Lists all files and folders within a specific Google Drive folder."""
    creds = get_credentials()
    try:
        service = build("drive", "v3", credentials=creds)
        query = f"'{folder_id}' in parents and trashed = false"
        files = []
        page_token = None
        
        print(f"\n📁 Listing files in folder (ID: {folder_id})...")
        while True:
            response = service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, mimeType)',
                pageToken=page_token
            ).execute()
            
            for file in response.get('files', []):
                print(f"  - Name: {file.get('name')}, ID: {file.get('id')}")
                files.append(file)
            
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        
        if not files:
            print("No files found in this folder.")
        
        return files
    except HttpError as err:
        print(f"An error occurred while listing files: {err}")
        return None

def download_file_from_drive(file_id, destination_path):
    """Downloads a file from Google Drive to a local path."""
    creds = get_credentials()
    try:
        service = build("drive", "v3", credentials=creds)
        file_metadata = service.files().get(fileId=file_id).execute()
        file_name = file_metadata.get('name')
        
        print(f"\n⬇️ Downloading '{file_name}' to '{destination_path}'...")
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"   Download progress: {int(status.progress() * 100)}%")
        
        fh.seek(0)
        with open(destination_path, 'wb') as f:
            f.write(fh.read())
            
        print(f"✅ File downloaded successfully.")
        return True
    except HttpError as err:
        print(f"An error occurred while downloading the file: {err}")
        return False

def delete_file_from_drive(file_id):
    """Permanently deletes a file from Google Drive."""
    creds = get_credentials()
    try:
        service = build("drive", "v3", credentials=creds)
        print(f"\n🗑️ Deleting file with ID: {file_id}...")
        service.files().delete(fileId=file_id).execute()
        print("✅ File deleted successfully.")
        return True
    except HttpError as err:
        print(f"An error occurred while deleting the file: {err}")
        return False

# --- Example Usage ---
if __name__ == "__main__":
    
    print(list_task_lists())

    # 2. List all files in a specific Google Drive folder
    # FOLDER_ID = "11vTiK6WAR6jE3gyOg_C5ay-ZpD3rEfLg"  # e.g., "1a2b3c4d5e6f7g8h9i0j"
    # list_files_in_folder(FOLDER_ID)
    
    # 3. Download a file from Google Drive
    # FILE_ID_TO_DOWNLOAD = "1uEWqT67ERVMMQVL9HWd0DWoMUNXuw3q8"
    # DESTINATION_PATH = "audio.m4a" # Change the name/extension as needed
    # download_file_from_drive(FILE_ID_TO_DOWNLOAD, DESTINATION_PATH)

    # 4. Delete a file from Google Drive (Use with caution!)
    # FILE_ID_TO_DELETE = "1uEWqT67ERVMMQVL9HWd0DWoMUNXuw3q8"
    # delete_file_from_drive(FILE_ID_TO_DELETE) 
    
    # print("\nScript finished. Uncomment examples in '__main__' to run functions.")