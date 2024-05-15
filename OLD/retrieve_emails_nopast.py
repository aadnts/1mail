import os
import base64
import json
import pickle
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
import re

# Load credentials from the token file
creds = None
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)

# If there are no valid credentials, let the user log in
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        raise ValueError("No valid credentials provided.")

# Build the Gmail API service
service = build('gmail', 'v1', credentials=creds)

def get_threads(user_id='me', label_ids=[], max_results=10):
    try:
        response = service.users().threads().list(userId=user_id, labelIds=label_ids, maxResults=max_results).execute()
        threads = response.get('threads', [])
        return threads
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def extract_sender_email(header_from):
    match = re.search(r'<(.+?)>', header_from)
    return match.group(1) if match else header_from

def create_folder_name(from_email, internal_date):
    date_str = internal_date.split(" ")[0]
    time_str = internal_date.split(" ")[1]
    folder_name = f"{from_email}:{date_str}--{time_str.replace(':', '-')}"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    return folder_name

def get_thread_details(thread_id, user_id='me'):
    try:
        thread = service.users().threads().get(userId=user_id, id=thread_id).execute()
        messages = thread.get('messages', [])

        for message in messages:
            process_message(message)

    except HttpError as error:
        print(f'An error occurred: {error}')

def process_message(message):
    try:
        headers = {header['name']: header['value'] for header in message['payload']['headers']}
        from_email = extract_sender_email(headers.get('From', ''))
        internal_date = datetime.fromtimestamp(int(message.get('internalDate')) / 1000).strftime('%Y-%m-%d %H:%M:%S')

        # Create a folder for the email
        folder_name = create_folder_name(from_email, internal_date)

        # Extract the email content
        email_message = extract_latest_text(message['payload'])

        # Remove previous conversations
        email_message = remove_previous_conversations(email_message)

        # Extract metadata
        metadata = {
            'id': message['id'],
            'snippet': message.get('snippet'),
            'historyId': message.get('historyId'),
            'internalDate': internal_date,
            'sizeEstimate': message.get('sizeEstimate'),
            'threadId': message.get('threadId'),
            'labelIds': message.get('labelIds'),
            'headers': headers
        }

        # Save email text to a file
        email_text_file = os.path.join(folder_name, 'email.txt')
        with open(email_text_file, 'w') as f:
            f.write(email_message)

        # Save metadata to a JSON file
        metadata_file = os.path.join(folder_name, 'metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=4)

        # Download and save attachments
        get_attachments(message, folder_name)

    except HttpError as error:
        print(f'An error occurred: {error}')

def extract_latest_text(payload):
    """Extracts the latest email text content."""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and 'body' in part and 'data' in part['body']:
                msg_str = base64.urlsafe_b64decode(part['body']['data'].encode('ASCII'))
                return msg_str.decode('utf-8')
            elif 'parts' in part:
                return extract_latest_text(part)
    elif 'body' in payload and 'data' in payload['body']:
        msg_str = base64.urlsafe_b64decode(payload['body']['data'].encode('ASCII'))
        return msg_str.decode('utf-8')
    return ""

def remove_previous_conversations(email_message, ):
    """Removes previous conversations from the email message."""
    # Regular expression to detect lines indicating previous email content
    previous_email_pattern = re.compile(
        r'(-{2,}|De :|Envoyé :|À :|Objet :)'
    )
    

    lines = email_message.split('\n')
    new_lines = []

    for line in lines:
        if previous_email_pattern.match(line):
            break
        new_lines.append(line)

    return '\n'.join(new_lines)

def get_attachments(message, folder_name):
    if 'parts' in message['payload']:
        for part in message['payload']['parts']:
            if part['filename']:
                attachment_id = part['body']['attachmentId']
                attachment = service.users().messages().attachments().get(userId='me', messageId=message['id'], id=attachment_id).execute()
                data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
                path = os.path.join(folder_name, part['filename'])
                with open(path, 'wb') as f:
                    f.write(data)
                    print(f'Attachment {part["filename"]} downloaded.')

def main():
    threads = get_threads(max_results=10)  # Retrieve the 10 latest threads
    if threads:
        for thread in threads:
            get_thread_details(thread['id'])

if __name__ == '__main__':
    main()
