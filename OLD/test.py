import os
import base64
import pickle
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

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

def get_emails(user_id='me', label_ids=[]):
    try:
        response = service.users().messages().list(userId=user_id, labelIds=label_ids).execute()
        messages = response.get('messages', [])
        return messages
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def get_email_details(message_id, user_id='me'):
    try:
        message = service.users().messages().get(userId=user_id, id=message_id, format='raw').execute()
        msg_str = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))
        save_eml_file(msg_str, f'{message_id}.eml')
        get_attachments(service, user_id, message_id)
    except HttpError as error:
        print(f'An error occurred: {error}')

def save_eml_file(data, filename):
    with open(filename, 'wb') as f:
        f.write(data)

def get_attachments(service, user_id, msg_id):
    message = service.users().messages().get(userId=user_id, id=msg_id).execute()
    for part in message['payload']['parts']:
        if part['filename']:
            attachment_id = part['body']['attachmentId']
            attachment = service.users().messages().attachments().get(userId=user_id, messageId=msg_id, id=attachment_id).execute()
            data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
            path = part['filename']
            with open(path, 'wb') as f:
                f.write(data)
                print(f'Attachment {part["filename"]} downloaded.')

def main():
    messages = get_emails()
    if messages:
        for msg in messages:
            get_email_details(msg['id'])

if __name__ == '__main__':
    main()
