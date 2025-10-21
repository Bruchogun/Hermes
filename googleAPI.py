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
    Automatically refreshes expired tokens.
    """
    creds = None
    
    # Load existing credentials
    if os.path.exists("token.json"):
        try:
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        except Exception as e:
            print(f"⚠️ Error loading token.json: {e}. Re-authenticating...")
            creds = None
    
    # Refresh or re-authenticate if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("✅ Token refreshed successfully")
            except Exception as e:
                print(f"⚠️ Token refresh failed: {e}. Re-authenticating...")
                creds = None
        
        if not creds:
            if not os.path.exists("credentials.json"):
                print("ERROR: credentials.json not found. Cannot authenticate.")
                exit(1)
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials
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
        document = docs_service.documents().create(body={'title': title}).execute()
        doc_id = document.get('documentId')
        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        return doc_id, doc_url
    except HttpError as err:
        print(f"❌ Error creating doc: {err}")
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
        return True
    except HttpError as err:
        print(f"❌ Error adding content to doc: {err}")
        return False

def attach_doc_to_event(event_id, doc_url, doc_title):
    creds = get_credentials()
    try:
        calendar_service = build("calendar", "v3", credentials=creds)
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
        return True
    except HttpError as err:
        print(f"❌ Error attaching doc to event: {err}")
        return False

def create_task(title, notes="", deadline=None, task_list_id="@default"):
    creds = get_credentials()
    try:
        # Try to parse the deadline in multiple formats
        due_date = None
        if deadline:
            try:
                # Try ISO format first (YYYY-MM-DD)
                deadline1 = datetime.strptime(deadline, "%Y-%m-%d")
                due_date = deadline1.strftime("%Y-%m-%d")
            except ValueError:
                try:
                    # Try full text format (October 22, 2025)
                    deadline1 = datetime.strptime(deadline, "%B %d, %Y")
                    due_date = deadline1.strftime("%Y-%m-%d")
                except ValueError:
                    try:
                        # Try another common format (10/22/2025)
                        deadline1 = datetime.strptime(deadline, "%m/%d/%Y")
                        due_date = deadline1.strftime("%Y-%m-%d")
                    except ValueError:
                        print(f"Warning: Could not parse deadline '{deadline}', skipping due date")
                        due_date = None
        
        tasks_service = build("tasks", "v1", credentials=creds)
        task_body = {'title': title}
        if notes:
            task_body['notes'] = notes
        if due_date:
            if isinstance(due_date, datetime):
                due_date = due_date.strftime('%Y-%m-%d')
            task_body['due'] = f"{due_date}T00:00:00.000Z"
        
        task = tasks_service.tasks().insert(
            tasklist=task_list_id,
            body=task_body
        ).execute()
        print(f"✅ Task: '{title}'")
        return task
    except HttpError as err:
        print(f"❌ Error creating task: {err}")
        pass

# --- ✨ NEW FUNCTIONS ✨ ---

def list_task_lists():
    """Lists the user's task lists from Google Tasks."""
    creds = get_credentials()
    try:
        service = build("tasks", "v1", credentials=creds)
        results = service.tasklists().list(maxResults=10).execute()
        items = results.get("items", [])
        return items if items else []
    except HttpError as err:
        print(f"❌ Error listing task lists: {err}")
        return []

def list_files_in_folder(folder_id):
    """Lists all files and folders within a specific Google Drive folder."""
    creds = get_credentials()
    try:
        service = build("drive", "v3", credentials=creds)
        query = f"'{folder_id}' in parents and trashed = false"
        files = []
        page_token = None
        
        while True:
            response = service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, mimeType)',
                pageToken=page_token
            ).execute()
            
            files.extend(response.get('files', []))
            
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        
        return files
    except HttpError as err:
        print(f"❌ Error listing files: {err}")
        return []

def download_file_from_drive(file_id, destination_path):
    """Downloads a file from Google Drive to a local path."""
    creds = get_credentials()
    try:
        service = build("drive", "v3", credentials=creds)
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        fh.seek(0)
        with open(destination_path, 'wb') as f:
            f.write(fh.read())
            
        return True
    except HttpError as err:
        print(f"❌ Error downloading file: {err}")
        return False

def delete_file_from_drive(file_id):
    """Permanently deletes a file from Google Drive."""
    creds = get_credentials()
    try:
        service = build("drive", "v3", credentials=creds)
        service.files().delete(fileId=file_id).execute()
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