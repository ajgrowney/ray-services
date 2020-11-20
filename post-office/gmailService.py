import sys
import base64
from flask import Flask, request
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from gmail_auth import get_auth

## Constants
DEFAULT_MAX_EMAILS = 10
GMAIL_LABEL="jarvis"

## Credential Configuration
creds = get_auth()
gmail_svc = build('gmail', 'v1', credentials=creds)
gmail_msg_api = gmail_svc.users().messages()

def message_summarize(email_body:str):
    return email_body

def mark_msg_as_read(msg_id:str):
    read_label = { 'removeLabelIds': ['UNREAD'], 'addLabelIds': [] }
    res = gmail_msg_api.modify(userId='me', id=msg_id, body=read_label).execute()
    return res

def read_message(msg_id, mark_read:bool, summarize = True):
    email = gmail_msg_api.get(userId='me', id=msg_id).execute()
    msg_mimetype = email['payload']["mimeType"]
    
    if msg_mimetype == "multipart/alternative":
        raw_email = base64.urlsafe_b64decode(email['payload']['parts'][0]['body']['data'].encode('ASCII')).decode('utf-8')
        email_body = BeautifulSoup(raw_email, features='html.parser').get_text()
    elif msg_mimetype == "text/html":
        raw_email = base64.urlsafe_b64decode(email['payload']['body']['data'].encode('ASCII')).decode('utf-8')
        email_body = BeautifulSoup(raw_email, features='html.parser').get_text()
    else:
        print(f'DEBUG | TODO Mimetype: {msg_mimetype}')
        raise Exception(f'Unhandled mimetype: {msg_mimetype}')

    if mark_read:
        mark_msg_as_read(msg_id)
    
    return message_summarize(email_body) if summarize else email_body
    
def read_messages(msg_ids:list = [], mark_read:bool = False):
    results, errors = [], []
    for msg_id in msg_ids:
        try:
            email_body = read_message(msg_id, mark_read)
            results.append(email_body)
        except Exception as e:
            errors.append(str(e))
    return results, errors


def check_mail(max_read:int = 10, time_filter:str = "", only_unread:bool = True):
    results, errors = [], [] 
    filter_query = " ".join(["label:"+GMAIL_LABEL, time_filter]) 
    if only_unread:
        filter_query += " is:unread"
    print(f'DEBUG | Filter Query: {filter_query}')
    list_response = gmail_msg_api.list(userId='me', q=filter_query).execute()
    if list_response['resultSizeEstimate'] == 0:
        return [], []
    for msg in list_response['messages'][0:max_read]:
        try:
            email = gmail_msg_api.get(userId='me', id=msg['id']).execute()
            headers = email['payload']['headers']
            header_dict = { item['name'].lower():item['value'] for item in headers }
            msg_response = { 'message_id': email['id'], 'subject': header_dict['subject'], 'date': header_dict['date'] }
            results.append(msg_response)
        except Exception as e:
            errors.append(str(e))
    return results, errors


if __name__ == '__main__':
    max_read = int(sys.argv[1]) if len(sys.argv) == 2 else DEFAULT_MAX_EMAILS
    mailbox, errs = check_mail(max_read, "newer_than:3d", True)
    print(mailbox)
    to_read = [m['message_id'] for m in mailbox]
    messages, _ = read_messages(to_read)
    print(messages)
