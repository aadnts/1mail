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

def get_emails(user_id='me', label_ids=[], max_results=10):
    try:
        response = service.users().messages().list(userId=user_id, labelIds=label_ids, maxResults=max_results).execute()
        messages = response.get('messages', [])
        return messages
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

def get_email_details(message_id, user_id='me'):
    try:
        message = service.users().messages().get(userId=user_id, id=message_id, format='full').execute()

        headers = {header['name']: header['value'] for header in message['payload']['headers']}
        from_email = extract_sender_email(headers.get('From', ''))
        internal_date = datetime.fromtimestamp(int(message.get('internalDate')) / 1000).strftime('%Y-%m-%d %H:%M:%S')

        # Create a folder for the email
        folder_name = create_folder_name(from_email, internal_date)

        # Extract the email content
        email_message = extract_latest_text(message['payload'])

        # Extract metadata
        metadata = {
            'id': message_id,
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
        get_attachments(service, user_id, message_id, folder_name)

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

def get_attachments(service, user_id, msg_id, folder_name):
    message = service.users().messages().get(userId=user_id, id=msg_id).execute()
    if 'parts' in message['payload']:
        for part in message['payload']['parts']:
            if part['filename']:
                attachment_id = part['body']['attachmentId']
                attachment = service.users().messages().attachments().get(userId=user_id, messageId=msg_id, id=attachment_id).execute()
                data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
                path = os.path.join(folder_name, part['filename'])
                with open(path, 'wb') as f:
                    f.write(data)
                    print(f'Attachment {part["filename"]} downloaded.')

def main():
    messages = get_emails(max_results=10)  # Retrieve the 10 latest emails
    if messages:
        for msg in messages:
            get_email_details(msg['id'])

if __name__ == '__main__':
    main()
