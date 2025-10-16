# Audio Meeting Transcription & Analysis Tool

This project processes audio recordings of meetings using Google's Gemini AI to generate transcriptions, emotional analysis, summaries, and task lists. It then automatically attaches these documents to the corresponding Google Calendar events.

## Overview

The tool analyzes meeting audio files and:
- Identifies speakers and their emotions during the conversation
- Generates compact summaries with key points
- Extracts tasks with deadlines
- Creates Google Docs with the analysis
- Attaches documents to matching Google Calendar events
- Creates Google Tasks for identified action items

## Prerequisites

### Required Software
- Python 3.8 or higher
- pip (Python package manager)

### Required Python Packages

Install the following dependencies:

```sh
pip install google-generativeai google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client pydantic
```

### Required API Keys and Credentials

1. **Gemini API Key**: Obtain from [Google AI Studio](https://aistudio.google.com/apikey)
2. **Google Cloud Credentials**: Create a project in [Google Cloud Console](https://console.cloud.google.com/) and enable:
   - Google Calendar API
   - Google Docs API
   - Google Tasks API
   
   Download the credentials.json file and place it in the project root.

## Setup

1. **Clone or download this repository**

2. **Create the Gemini API key file**:
   Create a file named GEMINI_API_KEY in the project root and paste your Gemini API key inside it (plain text, no quotes).

3. **Add Google credentials**:
   Place your credentials.json file in the project root directory.

4. **Prepare audio files**:
   - Place your meeting audio file (`.m4a` format) in the project root
   - Place an identifier.m4a file containing speaker introductions for better speaker identification

5. **First run authentication**:
   On first run, the script will open a browser window for Google OAuth authentication. This creates a token.json file for subsequent runs.

## Project Structure

```
.
├── .gitignore              # Git ignore rules
├── credentials.json        # Google API credentials (not in repo)
├── token.json             # Google OAuth token (auto-generated)
├── GEMINI_API_KEY         # Gemini API key (not in repo)
├── googleAPI.py           # Google API integration functions
├── isKeyWordHere.py       # String matching utility
├── ola.py                 # Main application script
└── README.md              # This file
```

## File Descriptions

### ola.py
Main application script that orchestrates the entire workflow:
- **`get_audio_creation_date(file_path)`**: Returns the creation date of an audio file in natural language format
- **`get_audio_creation_datetime(file_path)`**: Returns the creation datetime as a datetime object
- **[`ask(audio, prompt, ai_model, prompt_index, is_structured)`](ola.py)**: Sends audio to Gemini AI with a prompt and returns the response

### googleAPI.py
Handles all Google API interactions:
- **`get_credentials()`**: Authenticates and returns valid Google API credentials
- **[`getEvent(target_date, target_name)`](googleAPI.py)**: Retrieves calendar events matching a date and optional name
- **`create_google_doc(title)`**: Creates a new Google Doc and returns its ID and URL
- **[`add_content_to_doc(doc_id, content)`](googleAPI.py)**: Adds text content to an existing Google Doc
- **[`attach_doc_to_event(event_id, doc_url, doc_title)`](googleAPI.py)**: Attaches a Google Doc to a calendar event
- **[`create_google_task(title, notes, due_date, task_list_id)`](googleAPI.py)**: Creates a new task in Google Tasks

### [`isKeyWordHere.py`](isKeyWordHere.py)
String matching utility for fuzzy text comparison:
- **[`check_containment_probability(container_str, search_str, case_sensitive)`](isKeyWordHere.py)**: Calculates the probability (0-100%) that one string contains another using multiple matching strategies (exact match, word-level match, character sequence, fragments)

## How to Run

1. **Update the audio file path** in ola.py:
   ```python
   AUDIO_FILE_PATH = "your_meeting_audio.m4a"
   ```

2. **Run the main script**:
   ```sh
   python ola.py
   ```

3. **The script will**:
   - Load your Gemini API key
   - Upload the audio files to Gemini
   - Process three different prompts (emotions, summary, tasks)
   - Find matching calendar events
   - Create Google Docs with the analysis
   - Attach documents to the calendar event

## How to Test

### Test Individual Components

**Test Google API authentication**:
```sh
python googleAPI.py
```
This runs the `if __name__ == "__main__"` block which creates a test task.

**Test string matching**:
```sh
python isKeyWordHere.py
```
This runs an interactive mode where you can test the fuzzy string matching algorithm.

**Test the main workflow**:
Ensure you have:
- A valid audio file (`.m4a` format)
- An identifier.m4a file for speaker identification
- A corresponding calendar event within 2 hours of the audio file's creation time

## Configuration

### Prompts
The analysis is based on three prompts defined in `PROMPTS` in ola.py:

1. **Feelings**: Extracts emotions expressed by each speaker
2. **Resume**: Generates a compact summary with key points and tasks
3. **Tasks**: Structured extraction of tasks with deadlines (JSON format)

### AI Model
The default model is `gemini-2.5-flash`. You can change this in ola.py:
```python
AI_MODEL = "gemini-2.5-flash"
```

### Business Rules
The script assumes:
- Weekly meetings occur every Wednesday
- Accounting closures happen on the 15th and last day of each month
- Audio file creation time is adjusted by -2 hours for calendar event matching

## Important Notes

1. **File Formats**: Audio files must be in `.m4a` format
2. **Token Storage**: After first authentication, credentials are stored in token.json
3. **API Quotas**: Be aware of Google API and Gemini API usage limits
4. **Language**: Prompts are in Spanish; responses will be in Spanish
5. **Timeout**: Gemini requests have a 900-second (15-minute) timeout
6. **Event Matching**: Events are matched using a fuzzy matching algorithm with a 40% threshold

## Security

The following files are excluded from version control (see .gitignore):
- credentials.json - Google OAuth credentials
- token.json - Google OAuth token
- GEMINI_API_KEY - Gemini API key
- `*.m4a` - Audio files
- `*.md` - Generated markdown files (except README.md)
- __pycache__ - Python cache
- venv - Virtual environment

**Never commit sensitive credentials to version control!**

## Troubleshooting

- **"No API key found"**: Ensure GEMINI_API_KEY file exists and contains your API key
- **"File not found"**: Check that your audio file path is correct
- **"No upcoming events found"**: Verify calendar events exist near the audio file creation time
- **Authentication errors**: Delete token.json and re-authenticate
- **API quota exceeded**: Wait for quota reset or upgrade your API plan

## License

This project uses Google APIs and Gemini AI, subject to their respective terms of service.