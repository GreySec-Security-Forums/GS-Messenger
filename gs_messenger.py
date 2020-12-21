#!/usr/bin/env python3
import requests
import sys
import cmd
from bs4 import BeautifulSoup
from re import compile
from getpass import getpass
from pprint import pprint
from time import sleep

RESET = '\x1b[39m'
RED = '\x1b[31m'
GREEN = '\x1b[92m'
BLUE = '\x1b[34m'
YELLOW = '\x1b[33m'

def welcome():
    banner_lines = [
            "   _____  _____   __  __                                 ",
            "  / ____|/ ____| |  \/  |                                         ",
            " | |  __| (___   | \  / | ___  ___ ___  ___ _ __   __ _  ___ _ __ ",
            " | | |_ |\___ \  | |\/| |/ _ \/ __/ __|/ _ \ '_ \ / _` |/ _ \ '__|",
            " | |__| |____) | | |  | |  __/\__ \__ \  __/ | | | (_| |  __/ |   ",
            "  \_____|_____/  |_|  |_|\___||___/___/\___|_| |_|\__, |\___|_|   ",
            "                                                   __/ |          ",
            "                                                  |___/           ",
            "Created by DeepLogic"
            ]
    for line in banner_lines:
        print(line)
        sleep(0.25)

class GSBot:
    def __init__(self):
        self.session = None
        self.logged_in = False
        self.pmlist = []

    def login(self, username, password):
        self.session = requests.Session()
        response = self.session.get("https://greysec.net")
        # Search the HTML for the "my_post_key" value. It's used in MyBB sessions and required to login.
        html = BeautifulSoup(response.text, "html.parser")
        results = html.find(attrs={"name": "my_post_key"})
        my_post_key = results.attrs["value"]

        # HTTP POST to log in
        postData = {
            "my_post_key": my_post_key,
            "username":username,
            "password": password,
            "remember":"yes",
            "submit": "Login",
            "action": "do_login",
            "url": "https://greysec.net/index.php"
        }

        response = self.session.post("https://greysec.net/member.php", data=postData)
        if response.url != "https://greysec.net/index.php" or \
                len(response.history) != 1:
            raise Exception("Error occurred. Couldn't login.")
        else:
            self.logged_in = True
            return
    def logout(self):
        response = self.session.get("https://greysec.net/index.php")
        html = BeautifulSoup(response.text, "html.parser")
        logout_link = html.find("a", href=compile("\w*action=logout\w*")).attrs["href"]
        self.session.get("https://greysec.net/" + logout_link)
        self.logged_in = False

    def getPms(self, page=1):
        mid = 0
        private_messages = []
        # {pm_title:example, pm_sender:example, pm_contents}
        if page == 1:
            response = self.session.get("https://greysec.net/private.php")
        else:
            response = self.session.get("https://greysec.net/private.php", params={"fid":"0", "page":page})

        # Find PMs
        html = BeautifulSoup(response.text, "html.parser")
        
        for result in html.find_all("a", class_=["old_pm", "new_pm"]):
            pm = {}
            pm["msgid"] = mid
            pm["title"] = result.text
            nextTd = result.find_next("td")
            pm["sender"] = nextTd.text
            pmUrl = result.attrs["href"]
            pmPage = self.session.get("https://greysec.net/" + pmUrl).text
            pmHtml = BeautifulSoup(pmPage, "html.parser")
            pm["contents"] = pmHtml.find("div", class_="post_body scaleimages").text
            private_messages.append(pm)
            mid += 1

        self.pmlist = private_messages

class CommandInterpreter(cmd.Cmd):
    prompt = f"{BLUE}[GS Messenger]{RESET} > "
    file = None
    
    def postloop(self):
        print("\nGoodbye friend")

    def do_login(self, arg):
        "Log into your GreySec account"
        while True:
            username = input("Username: ").strip()
            password = getpass("Password: ")
            try:
                bot.login(username, password)
            except:
                print(f"{RED}Login Failed{RESET}")

            if bot.logged_in:
                print(f"{GREEN}Login Successful{RESET}")
                break

    def do_retrieve(self, arg=1):
        "Get PMs from GreySec. showpms <pagenumber>"
        print("Retrieving PMs...")
        bot.getPms(page=arg)
        #for message in bot.pmlist:
        #    print(f"{message['msgid']} {YELLOW}{message['sender']}{RESET} - {BLUE}{message['title']}{RESET}")
    
    def do_list(self, arg):
        "List the retrieved PMs"
        if len(bot.pmlist) > 0:
            for message in bot.pmlist:
                print(f"{message['msgid']} {YELLOW}{message['sender']}{RESET} - {BLUE}{message['title']}{RESET}")
        else:
            print("{RED}No messages found{RESET}. Try downloading some with 'retrieve'")


    def do_read(self, arg):
        "Read a PM. read <int>"
        found = False
        for p in bot.pmlist:
            if p["msgid"] == int(arg.strip()):
                found = True
                print("\n" + "=" * 20)
                print(p["title"])
                print("=" * 20)
                print(p["sender"])
                print("=" * 20)
                print(p["contents"])
        if not found:
            print("Message not found")

## Main ####

welcome()
bot = GSBot()
CommandInterpreter().cmdloop()
bot.logout()
