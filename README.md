# GS-Messenger
GreySec PM Messenger Program

![a picture](https://i.imgur.com/h79xCLT.png "GS Messenger")

## Usage
### Unix
`$ python3 gs_messenger.py`
### Windows
`.\path\to\gs_messenger.exe`

## Commands
* login - Log in to GreySec.net
* retrieve - Get PMs from greysec. Only gets first page of PMs by default. Specify a page number to get other PMs
* list - Show the list of PMs
* read - Read a PM. Example: read 3
* reply - Reply to a PM. Example: reply 3
* compose - Write a new PM to another user

## Notes
* There's a quit command, but it doesn't really work yet...
* PMs are automatically retrieved when you log in and every 3 minutes after that. So really you only need to use 'retrieve' if you're impatient about checking your PMs.
