import requests
import sys
import cmd
from bs4 import BeautifulSoup
from re import compile, findall
from getpass import getpass
from pprint import pprint
from time import sleep
from threading import Thread

if sys.platform == "win32":
    RESET = ''
    RED = ''
    GREEN = ''
    BLUE = ''
    YELLOW = ''
else:
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
        self.post_key = "" # Value provided in MyBB HTML which is necessary for requesting resources.
        self.new_pms = False
        self.pmlist = []
    
    def fetcher(self):
        "Periodically updates the PM list. Intended to run in background thread"
        while True:
            self.getPms(verbose=False)
            if self.new_pms:
                print("\nNew Private Message")
                self.new_pms = False
            sleep(180) # 3 minutes

    def login(self, username, password, startFetcher=True):
        "Authenticate with GreySec"
        # Returns None if authentication was successful and sets self.logged_in to True, raises exception otherwise.
        self.session = requests.Session()
        response = self.session.get("https://greysec.net")
        # Search the HTML for the "my_post_key" value. It's used in MyBB sessions and required to login.
        html = BeautifulSoup(response.text, "html.parser")
        results = html.find(attrs={"name": "my_post_key"})
        my_post_key = results.attrs["value"]
        self.post_key = my_post_key

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
        "Log out of Greysec"
        # Sets self.logged_in to False
        response = self.session.get("https://greysec.net/index.php")
        html = BeautifulSoup(response.text, "html.parser")
        logout_link = html.find("a", href=compile("\w*action=logout\w*")).attrs["href"]
        self.session.get("https://greysec.net/" + logout_link)
        self.logged_in = False

    def getPms(self, page=1, verbose=True):
        "Retrieves PMs from account. Need to be authenticated first."
        # page: <int> The page number of the PMs to get. Gets just the first page by default. No need to get all the PMs at once.
        # verbose: <bool> Whether to output info to the user. It's only set to False when used by the fetcher method.
        mid = 0
        private_messages = []
        # {title:example, sender:example, contents:example, isUnread:true}
        if page == 1:
            response = self.session.get("https://greysec.net/private.php")
        else:
            response = self.session.get("https://greysec.net/private.php", params={"fid":"0", "page":page})

        # Find PMs
        # Example 'pm' dictionary:
        # {"title": "test", "isunread":"True", "msgid": "3", "sender":"Friend", "pmid":"2377", "contents":"hello world"}
        html = BeautifulSoup(response.text, "html.parser")
        
        results = [result for result in html.find_all("a", class_=["old_pm", "new_pm"])]
        for result in results:
            pm = {}
            if result.attrs["class"][0] == "new_pm":
                pm["isunread"] = True
                self.new_pms = True
            elif result.attrs["class"][0] == "old_pm":
                pm["isunread"] = False
            else:
                pm["isunread"] = "Unknown"
            
            # mid: message id. used by the command interpreter to index the messages
            pm["msgid"] = mid
            pm["title"] = result.text
            nextTd = result.find_next("td")
            pm["sender"] = nextTd.text
            pmUrl = result.attrs["href"]
            pmPage = self.session.get("https://greysec.net/" + pmUrl)
            # pmid: used by greysec for replying to PMs
            pm["pmid"] = findall("pmid=\d{1,7}", pmPage.url)[0].strip("pmid=")
            pmHtml = BeautifulSoup(pmPage.text, "html.parser")
            pm["contents"] = pmHtml.find("div", class_="post_body scaleimages").text
            
            pmDate = pmHtml.find(class_="post_date")
            try:
                pmRecvdDate = findall("\d{1,2}-\d{1,2}-\d{4}", str(pmDate))[0]
                pmRecvdTime = findall("\d{1,2}:\d{1,2} [AP]M", pmDate.text)[0]
            except:
                pmRecvdDate, pmRecvdTime = findall("\d{2}-\d{2}-\d{4}, \d{2}:\d{2} [AP]M", str(pmDate))[0].split(",")
                
            pm["timestamp"] = f"{pmRecvdDate} {pmRecvdTime}"

            # Show progress of message retrieval
            if verbose:
                if (mid + 1) % 2 == 0:
                    percentage = round((mid + 1) / len(results) * 100, 1)
                    print(f"Retrieved: {percentage}%")
            
            private_messages.append(pm)
            mid += 1

        self.pmlist = private_messages
        if verbose:
            print("Retrieval complete")

    def sendPm(self, subject, msg, recipient, pmid=0):
        "Send a PM to a user"
        # subject <string> - the subject of the message.
        # msg <string> - the message to send
        # recipient <string> - username of account to send PM to.
        # pmid <int> - The PM id we're replying to, or 0 if composing new message
        # returns: True on successful sending, False otherwise.
        # Only specify pmid if you're replying to a message. Not for composing new messages.
        if bot.logged_in:
            # Get my_post_key
            # Need to get new post key. Greysec was complaining about the program using the original post key used for logging in for some reason.
            response = self.session.get("https://greysec.net/private.php")
            pmPage = BeautifulSoup(response.text, "html.parser")
            self.post_key = pmPage.find("input", attrs={"name":"my_post_key"}).attrs["value"]
            postData = {
                    "my_post_key":self.post_key,
                    "to": recipient,
                    "bcc": "",
                    "subject": subject,
                    "action": "do_send",
                    "pmid": pmid,
                    "do": "reply",
                    "options[signature]": "0",
                    "options[savecopy]": "1",
                    "options[readreceipt]": "1",
                    "message": msg
                    }
            response = self.session.post("https://greysec.net/private.php", data=postData)
            # The following isn't going to handle errors very well. Further testing is required to determine what could go wrong so it can be handled.
            if response.status_code == 200:
                return True
            else:
                return False

class CommandInterpreter(cmd.Cmd):
    prompt = f"{BLUE}[GS Messenger]{RESET} > "
    file = None
    ruler = "#"
    doc_header = "GS Messenger Commands:"
    
    def do_login(self, arg):
        "Log into your GreySec account"
        if bot.logged_in: print("You're already logged in"); return

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
        print("Retrieving PMs")
        bot.getPms()
        # Start fetcher
        fetcher = Thread(target=bot.fetcher)
        fetcher.start()

        # change prompt
        self.prompt = f"{BLUE}[{username}@greysec.net]{RESET} > "

    def do_retrieve(self, arg=1):
        "Get PMs from GreySec. retrieve <pagenumber> (automatically done when program starts)"
        if bot.logged_in:
            print("Retrieving PMs...")
            bot.getPms(page=arg)
            #for message in bot.pmlist:
            #    print(f"{message['msgid']} {YELLOW}{message['sender']}{RESET} - {BLUE}{message['title']}{RESET}")
        else:
            print("Not logged in. Use 'login' to login.")
    
    def do_list(self, arg):
        "List the retrieved PMs"
        if bot.logged_in:
            if len(bot.pmlist) > 0:
                print(f"{YELLOW}Messages\n{RED}*{RESET} = New message")
                for message in bot.pmlist:
                    if message["isunread"]:
                        print(f"{message['msgid']} {YELLOW}{message['sender']}{RESET} - {RED}*{RESET}{BLUE}{message['title']}{RESET}")
                    else:
                        print(f"{message['msgid']} {YELLOW}{message['sender']}{RESET} - {BLUE}{message['title']}{RESET}")
            else:
                print("{RED}No messages found{RESET}. Try downloading some with 'retrieve'")
        else:
            print("Not logged in. Use 'login' to login.")


    def do_read(self, arg):
        "Read a PM. read <int>"
        if bot.logged_in:
            found = False
            for p in bot.pmlist:
                if p["msgid"] == int(arg.strip()):
                    found = True
                    print("\n" + "=" * 40)
                    print("Subject:", p["title"])
                    print("=" * len(p["title"]))
                    print("Sender:", p["sender"])
                    print("=" * len(p["title"]))
                    print("Timestamp:", p["timestamp"])
                    print("=" * len(p["timestamp"]))
                    print(p["contents"])
            if not found:
                print("Message not found")
        else:
            print("Not logged in. Use 'login' to login.")
    
    def do_reply(self, arg):
        "Reply to a PM. Example: reply 11"
        if bot.logged_in: # Check that bot is logged in
            found = False
            reply_msg = ""

            for p in bot.pmlist: # Find the PM the user wants to reply to
                if p["msgid"] == int(arg.strip()):
                    print("\n" + "=" * 20)
                    print(p["title"])
                    print("=" * 20)
                    print(p["sender"])
                    print("=" * 20)
                    print(p["contents"])

                    # Prompt user to reply
                    print("Enter your message. When you are done, type EOF and press enter\n")
                    while True:
                        try:
                            userinput = input("> ")
                        except KeyboardInterrupt:
                            print("\nCancelled!")
                            break
                        if len(userinput) == 3 and userinput == "EOF":
                            # Send PM
                            subject = "RE:" + p["title"]
                            recipient = p["sender"]
                            msgPmid = p["pmid"]
                            print("Sending PM...")

                            successful = bot.sendPm(subject, reply_msg, recipient, pmid=msgPmid)
                            if successful:
                                print("PM sent successfully")
                            else:
                                print("Error sending PM")
                            break
                        else:
                            reply_msg += userinput + "\r\n"
            if not found:
                print("Message not found")

        else:
            print("Not logged in. Use 'login' to login.")
    
    def do_compose(self, arg):
        "Compose a PM"
        if bot.logged_in: # Check that bot is logged in
            found = False
            msg = ""

            # Prompt user to reply
            print("Enter the username of recipient")
            recipient = input("Recipient: ")

            print("Enter the subject")
            subject = input("Subject: ")
            print("Enter your message. When you are done, type EOF and press enter. Press Ctrl + C to cancel.\n")
            while True:
                try:
                    userinput = input("> ")
                except KeyboardInterrupt:
                    print("\nCancelled!")
                    break
                if len(userinput) == 3 and userinput == "EOF":
                    # Send PM
                    print("Sending PM...")

                    successful = bot.sendPm(subject, msg, recipient, pmid=0)
                    if successful:
                        print("PM sent successfully")
                    else:
                        print("Error sending PM")
                    break
                else:
                    msg += userinput + "\r\n\r\n"

        else:
            print("Not logged in. Use 'login' to login.")


    def do_quit(self, arg):
        "Exit the program"
        print("Bye friend!")
        sys.exit(0)

## Main ####

welcome()
bot = GSBot()
try:
    CommandInterpreter().cmdloop()
except Exception as exception:
    print("Exception:", exception)

# Make sure to logout
bot.logout()
