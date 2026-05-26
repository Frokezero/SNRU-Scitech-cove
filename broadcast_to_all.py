import os
import sys
import json
import urllib.request
from dotenv import load_dotenv

def main():
    load_dotenv()
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    if not token:
        print("[x] Error: LINE_CHANNEL_ACCESS_TOKEN not found in .env file!")
        sys.exit(1)
        
    print("==================================================")
    print("      LINE BOT BROADCAST UTILITY (SciTech)")
    print("==================================================")
    print("[*] Ready to broadcast a message to ALL LINE followers.")
    print("Enter the message you want to broadcast (type 'SEND' on a new line when finished):")
    print("--------------------------------------------------")
    
    lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == "SEND":
                break
            lines.append(line)
        except EOFError:
            break
            
    message_text = "\n".join(lines).strip()
    if not message_text:
        print("[x] Error: Message cannot be empty!")
        sys.exit(1)
        
    print("\n[*] Broadcasting the following message:")
    print("--------------------------------------------------")
    print(message_text)
    print("--------------------------------------------------")
    
    confirm = input("Confirm broadcast to everyone? (y/n): ").strip().lower()
    if confirm != 'y':
        print("[x] Broadcast canceled.")
        sys.exit(0)
        
    print("[*] Sending request to LINE Broadcast API...")
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    payload = {
        "messages": [
            {
                "type": "text",
                "text": message_text
            }
        ]
    }
    
    req_body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=req_body, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req) as resp:
            resp.read()
            print("[+] Broadcast sent successfully to all followers!")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        print(f"[x] LINE API Error: {e.code} {e.reason}")
        print(f"Details: {err_body}")
    except Exception as e:
        print(f"[x] Error sending broadcast: {e}")

if __name__ == "__main__":
    main()
