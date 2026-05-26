import os
import sys
import json
import urllib.request
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

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

def get_font(font_name, size):
    font_paths = [
        f"C:\\Windows\\Fonts\\{font_name}.ttf",
        f"C:\\Windows\\Fonts\\LeelawUI.ttf",
        f"C:\\Windows\\Fonts\\Leelawdb.ttf",
        f"C:\\Windows\\Fonts\\tahoma.ttf",
        f"C:\\Windows\\Fonts\\arial.ttf"
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_gradient(draw, x_start, y_start, x_end, y_end, color_start, color_end):
    r1, g1, b1 = color_start
    r2, g2, b2 = color_end
    h = y_end - y_start
    for y in range(y_start, y_end):
        ratio = (y - y_start) / h
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        draw.line([(x_start, y), (x_end, y)], fill=(r, g, b))

def main():
    print("[*] Starting Premium Rich Menu Setup Script...")
    load_dotenv()
    
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    if not token:
        print("[x] Error: LINE_CHANNEL_ACCESS_TOKEN not found in .env file!")
        sys.exit(1)
        
    website_url = get_ngrok_url()
    print(f"[*] Detected Website URL (Website Button): {website_url}")

    # 1. Generate Stunning Rich Menu Image (2500x1686)
    print("[*] Generating Rich Menu image with glassmorphic cards...")
    img = Image.new("RGB", (2500, 1686), "#0f172a")
    overlay = Image.new("RGBA", (2500, 1686), (0, 0, 0, 0))
    draw_bg = ImageDraw.Draw(img)
    draw_overlay = ImageDraw.Draw(overlay)
    
    col_width = 833
    row_height = 843
    
    cells = [
        {
            "emoji": "📅", "title": "กิจกรรมวันนี้", "desc": "ดูกิจกรรมเปิดจองทั้งหมด",
            "colors": ((15, 23, 42), (2, 132, 199))  # Deep Slate to Sky Blue
        },
        {
            "emoji": "⭐", "title": "คะแนนสะสม", "desc": "เช็คข้อมูลชั่วโมงกิจกรรม",
            "colors": ((15, 23, 42), (13, 148, 136))  # Deep Slate to Teal
        },
        {
            "emoji": "📋", "title": "ประวัติการจอง", "desc": "ดูประวัติกิจกรรม 5 ล่าสุด",
            "colors": ((15, 23, 42), (99, 102, 241))  # Deep Slate to Indigo
        },
        {
            "emoji": "👤", "title": "ข้อมูลส่วนตัว", "desc": "ดูชั้นปี สาขา คะแนน และโปรไฟล์",
            "colors": ((15, 23, 42), (71, 85, 105))  # Deep Slate to Cool Slate
        },
        {
            "emoji": "❓", "title": "วิธีใช้งานบอท", "desc": "แสดงเมนูความช่วยเหลือทั้งหมด",
            "colors": ((15, 23, 42), (225, 29, 72))  # Deep Slate to Rose Red
        },
        {
            "emoji": "🌐", "title": "เว็บไซต์หลัก", "desc": "เข้าสู่ระบบหลักเพื่อทำรายการ",
            "colors": ((15, 23, 42), (79, 70, 229))  # Deep Slate to Royal Purple
        }
    ]
    
    # Load fonts
    font_emoji = get_font("seguiemj", 130)
    font_title = get_font("Leelawdb", 56)
    font_desc = get_font("LeelawUI", 32)
    
    for idx, cell in enumerate(cells):
        x_idx = idx % 3
        y_idx = idx // 3
        
        x_start = x_idx * 833
        y_start = y_idx * 843
        x_end = x_start + (834 if x_idx == 2 else 833)
        y_end = y_start + 843
        
        # Draw gradient background for each cell
        draw_gradient(draw_bg, x_start, y_start, x_end, y_end, cell["colors"][0], cell["colors"][1])
        
        # Transparent overlay grid lines (slate border)
        draw_overlay.rectangle([x_start, y_start, x_end, y_end], outline=(255, 255, 255, 15), width=2)
        
        # Center glassmorphic card bounds
        card_padding_x = 50
        card_padding_y = 60
        card_x_start = x_start + card_padding_x
        card_y_start = y_start + card_padding_y
        card_x_end = x_end - card_padding_x
        card_y_end = y_end - card_padding_y
        
        # Draw glass container
        draw_overlay.rounded_rectangle(
            [card_x_start, card_y_start, card_x_end, card_y_end],
            radius=35,
            fill=(255, 255, 255, 15),
            outline=(255, 255, 255, 50),
            width=2
        )
        
        center_x = (card_x_start + card_x_end) // 2
        
        # Draw subtle glowing halo behind emoji
        draw_overlay.ellipse(
            [center_x - 90, card_y_start + 175 - 90, center_x + 90, card_y_start + 175 + 90],
            fill=(255, 255, 255, 20)
        )
        
    # Combine background and overlay before drawing text for maximum legibility and crispness
    final_img = Image.alpha_composite(img.convert("RGBA"), overlay)
    draw_final = ImageDraw.Draw(final_img)
    
    # Draw text labels on the final composite image
    for idx, cell in enumerate(cells):
        x_idx = idx % 3
        y_idx = idx // 3
        
        x_start = x_idx * 833
        y_start = y_idx * 843
        x_end = x_start + (834 if x_idx == 2 else 833)
        
        card_padding_x = 50
        card_padding_y = 60
        card_x_start = x_start + card_padding_x
        card_x_end = x_end - card_padding_x
        card_y_start = y_start + card_padding_y
        
        center_x = (card_x_start + card_x_end) // 2
        
        # Render Emoji
        draw_final.text((center_x, card_y_start + 175), cell["emoji"], font=font_emoji, fill=(255, 255, 255, 255), anchor="mm")
        # Render Title (Thai)
        draw_final.text((center_x, card_y_start + 410), cell["title"], font=font_title, fill=(255, 255, 255, 255), anchor="mm")
        # Render Description
        draw_final.text((center_x, card_y_start + 530), cell["desc"], font=font_desc, fill=(148, 163, 184, 255), anchor="mm")
        
        # Elegant bottom accent line for each card matching gradient color
        draw_final.line([(center_x - 100, card_y_start + 620), (center_x + 100, card_y_start + 620)], fill=cell["colors"][1] + (255,), width=4)

    image_path = "rich_menu.png"
    final_img.convert("RGB").save(image_path, "PNG")
    print(f"[+] Image generated and saved locally as '{image_path}'")

    # 2. LINE API Calls to register Rich Menu
    print("[*] Sending request to LINE API to create Rich Menu...")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    rich_menu_data = {
        "size": {
            "width": 2500,
            "height": 1686
        },
        "selected": True,
        "name": "SciTech Activity Rich Menu",
        "chatBarText": "เมนูกิจกรรม",
        "areas": [
            {
                "bounds": {"x": 0, "y": 0, "width": 833, "height": 843},
                "action": {"type": "message", "text": "กิจกรรม"}
            },
            {
                "bounds": {"x": 833, "y": 0, "width": 833, "height": 843},
                "action": {"type": "message", "text": "คะแนน"}
            },
            {
                "bounds": {"x": 1666, "y": 0, "width": 834, "height": 843},
                "action": {"type": "message", "text": "ประวัติ"}
            },
            {
                "bounds": {"x": 0, "y": 843, "width": 833, "height": 843},
                "action": {"type": "message", "text": "ข้อมูลส่วนตัว"}
            },
            {
                "bounds": {"x": 833, "y": 843, "width": 833, "height": 843},
                "action": {"type": "message", "text": "ช่วยเหลือ"}
            },
            {
                "bounds": {"x": 1666, "y": 843, "width": 834, "height": 843},
                "action": {"type": "uri", "uri": website_url}
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
    print(f"[*] Uploading '{image_path}' to Rich Menu...")
    with open(image_path, "rb") as f:
        img_data = f.read()
        
    headers_img = {
        "Content-Type": "image/png",
        "Authorization": f"Bearer {token}"
    }
    
    # LINE uses api-data.line.me (not api.line.me) for binary content upload
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
            print("[+] Rich Menu set as default successfully! All students will now see the new premium dashboard!")
    except Exception as e:
        print(f"[x] Failed to set default Rich Menu: {e}")
        if hasattr(e, 'read'):
            print(e.read().decode('utf-8'))
        sys.exit(1)
        
    # Cleanup temp file
    try:
        os.remove(image_path)
    except OSError:
        pass
        
    print("[*] Setup completed successfully!")

if __name__ == "__main__":
    main()
