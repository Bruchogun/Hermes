import os.path
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/tasks"]


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

def getEvent(target_date, target_name=""):
  creds = get_credentials()
  print(target_date, target_name, 'oaaaa')
  
  # Convert string to datetime if needed
  if isinstance(target_date, str):
    target_date = datetime.fromisoformat(target_date.replace('Z', '+00:00'))
  
  # Subtract 2 hours from current time
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

    # Call the Calendar API
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
    """
    Creates a new Google Doc with the given title.
    Returns the document ID and URL.
    """
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
    """
    Adds text content to an existing Google Doc.
    """
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
    """
    Attaches a Google Doc to a calendar event.
    """
    try:
        calendar_service = build("calendar", "v3", credentials=creds)
        
        print("📎 Attaching the doc to the calendar event...")
        
        # Get the event to retrieve existing attachments
        event = calendar_service.events().get(calendarId='primary', eventId=event_id).execute()
        existing_attachments = event.get('attachments', [])
        
        # Define the new attachment
        new_attachment = {
            'fileUrl': doc_url,
            'title': doc_title,
            'mimeType': 'application/vnd.google-apps.document'
        }
        
        # Combine old and new attachments
        updated_attachments = existing_attachments + [new_attachment]
        
        # Update the event
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


def create_google_task(title, notes="", due_date=None, task_list_id="@default"):
    """
    Creates a new task in Google Tasks.
    
    Args:
        title (str): The title of the task
        notes (str): Additional notes/description for the task
        due_date (str): Due date in ISO format (YYYY-MM-DD) or datetime object
        task_list_id (str): The task list ID. Defaults to "@default" (primary list)
    
    Returns:
        dict: The created task object with id, title, etc.
        None: If there was an error
    """
    creds = get_credentials()
    
    try:
        tasks_service = build("tasks", "v1", credentials=creds)
        
        # Prepare the task body
        task_body = {
            'title': title,
        }
        
        if notes:
            task_body['notes'] = notes
        
        if due_date:
            # Convert datetime to RFC 3339 format if needed
            if isinstance(due_date, datetime):
                due_date = due_date.strftime('%Y-%m-%d')
            # Google Tasks expects RFC 3339 format with time set to midnight UTC
            task_body['due'] = f"{due_date}T00:00:00.000Z"
        
        print(f"📋 Creating task: '{title}'...")
        
        # Create the task
        task = tasks_service.tasks().insert(
            tasklist=task_list_id,
            body=task_body
        ).execute()
        
        print(f"✅ Task created successfully with ID: {task.get('id')}")
        return task
        
    except HttpError as err:
        print(f"An error occurred while creating task: {err}")
        return None

if __name__ == "__main__":
     create_google_task("Test Task from API", "This is a test task created via Google Tasks API", "2024-12-31")