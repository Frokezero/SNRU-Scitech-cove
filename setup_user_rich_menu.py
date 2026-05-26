import os
import sys
import json
import urllib.request
from dotenv import load_dotenv
from PIL import Image

def get_ngrok_url():
    try:
        url = "http://127.0.0.1:4040/api/tunnels"
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode('utf-8'))
        tunnels = data.get('tunnels', [])
        for t in tunnels:
            if t.get('proto') == 'https' or t.get('public_url', '').startswith('https://'):
                return t.get('public_url')
    except Exception:
        pass
    return "https://synopsis-exponent-peddling.ngrok-free.dev"  # Fallback

def main():
    print("[*] Starting Custom Rich Menu Setup Script...")
    load_dotenv()
    
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    if not token:
        print("[x] Error: LINE_CHANNEL_ACCESS_TOKEN not found in .env file!")
        sys.exit(1)
        
    website_url = get_ngrok_url()
    print(f"[*] Detected Website URL: {website_url}")

    # Path to the user's uploaded image
    uploaded_image_path = r"C:\Users\froke\.gemini\antigravity-ide\brain\4c121381-1d28-4039-99fa-ba866148af3c\media__1779801713130.png"
    resized_image_path = "rich_menu_resized.png"
    
    if not os.path.exists(uploaded_image_path):
        print(f"[x] Error: Uploaded image not found at {uploaded_image_path}!")
        sys.exit(1)
        
    # Resize image to exact LINE standard (2500x1686)
    print(f"[*] Resizing {uploaded_image_path} to 2500x1686...")
    try:
        img = Image.open(uploaded_image_path)
        img_resized = img.resize((2500, 1686), Image.Resampling.LANCZOS)
        img_resized.save(resized_image_path, "PNG")
        print(f"[+] Resized image saved as '{resized_image_path}'")
    except Exception as e:
        print(f"[x] Failed to resize image: {e}")
        sys.exit(1)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # 1. Clean up existing rich menus to avoid conflict/quota limit
    print("[*] Fetching existing Rich Menus to clean up...")
    req_list = urllib.request.Request("https://api.line.me/v2/bot/richmenu", headers={"Authorization": f"Bearer {token}"}, method='GET')
    try:
        with urllib.request.urlopen(req_list) as resp:
            resp_data = json.loads(resp.read().decode('utf-8'))
            menus = resp_data.get("richmenus", [])
            print(f"[*] Found {len(menus)} existing Rich Menus. Deleting them...")
            for menu in menus:
                menu_id = menu.get("richMenuId")
                req_del = urllib.request.Request(f"https://api.line.me/v2/bot/richmenu/{menu_id}", headers={"Authorization": f"Bearer {token}"}, method='DELETE')
                with urllib.request.urlopen(req_del) as d_resp:
                    d_resp.read()
                print(f"  [-] Deleted Rich Menu ID: {menu_id}")
    except Exception as e:
        print(f"[*] Cleanup note: {e}")

    # 2. Register Rich Menu structure matching the user's custom layout
    print("[*] Creating new Rich Menu with the custom 6-button layout...")
    
    rich_menu_data = {
        "size": {
            "width": 2500,
            "height": 1686
        },
        "selected": True,
        "name": "SciTech Custom Rich Menu",
        "chatBarText": "เมนูกิจกรรม",
        "areas": [
            # Row 1, Column 1: เว็บไซต์หลัก
            {
                "bounds": {"x": 0, "y": 0, "width": 833, "height": 843},
                "action": {"type": "uri", "uri": website_url}
            },
            # Row 1, Column 2: กิจกรรมวันนี้
            {
                "bounds": {"x": 833, "y": 0, "width": 833, "height": 843},
                "action": {"type": "message", "text": "กิจกรรม"}
            },
            # Row 1, Column 3: ข้อมูลส่วนตัว
            {
                "bounds": {"x": 1666, "y": 0, "width": 834, "height": 843},
                "action": {"type": "message", "text": "ข้อมูลส่วนตัว"}
            },
            # Row 2, Column 1: คะแนนสะสม
            {
                "bounds": {"x": 0, "y": 843, "width": 833, "height": 843},
                "action": {"type": "message", "text": "คะแนน"}
            },
            # Row 2, Column 2: ประวัติการจอง
            {
                "bounds": {"x": 833, "y": 843, "width": 833, "height": 843},
                "action": {"type": "message", "text": "ประวัติ"}
            },
            # Row 2, Column 3: วิธีใช้งานบอท
            {
                "bounds": {"x": 1666, "y": 843, "width": 834, "height": 843},
                "action": {"type": "message", "text": "ช่วยเหลือ"}
            }
        ]
    }
    
    req_body = json.dumps(rich_menu_data).encode('utf-8')
    req = urllib.request.Request("https://api.line.me/v2/bot/richmenu", data=req_body, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req) as resp:
            resp_data = json.loads(resp.read().decode('utf-8'))
            rich_menu_id = resp_data.get("richMenuId")
            print(f"[+] Rich Menu created successfully! ID: {rich_menu_id}")
    except Exception as e:
        print(f"[x] Failed to create Rich Menu: {e}")
        if hasattr(e, 'read'):
            print(e.read().decode('utf-8'))
        sys.exit(1)
        
    # 3. Upload Image to Rich Menu
    print(f"[*] Uploading '{resized_image_path}' to Rich Menu...")
    with open(resized_image_path, "rb") as f:
        img_data = f.read()
        
    headers_img = {
        "Content-Type": "image/png",
        "Authorization": f"Bearer {token}"
    }
    
    url_img = f"https://api-data.line.me/v2/bot/richmenu/{rich_menu_id}/content"
    req_img = urllib.request.Request(url_img, data=img_data, headers=headers_img, method='POST')
    
    try:
        with urllib.request.urlopen(req_img) as resp:
            resp.read()
            print("[+] Rich Menu image uploaded successfully!")
    except Exception as e:
        print(f"[x] Failed to upload Rich Menu image: {e}")
        if hasattr(e, 'read'):
            print(e.read().decode('utf-8'))
        sys.exit(1)
        
    # 4. Set Rich Menu as Default
    print("[*] Setting Rich Menu as default for all users...")
    url_def = f"https://api.line.me/v2/bot/user/all/richmenu/{rich_menu_id}"
    req_def = urllib.request.Request(url_def, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req_def) as resp:
            resp.read()
            print("[+] Rich Menu set as default successfully!")
    except Exception as e:
        print(f"[x] Failed to set default Rich Menu: {e}")
        if hasattr(e, 'read'):
            print(e.read().decode('utf-8'))
        sys.exit(1)
        
    # Cleanup temp file
    try:
        os.remove(resized_image_path)
    except OSError:
        pass
        
    print("[*] Rich Menu setup completed successfully! Enjoy your new custom layout!")

if __name__ == "__main__":
    main()
