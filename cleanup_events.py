import json
import re

def cleanup_imported_events():
    with open('events.json', 'r', encoding='utf-8') as f:
        events = json.load(f)
    
    for e in events:
        # 1. Fix cases where date leaked into title
        # Pattern: title starts with "- [number] [month] [year]"
        match = re.match(r'^-\s*(\d+)\s+([ก-ฮ\.]+)\s+(\d{2})', e['title'])
        if match:
            e['date'] = f"{e['date']} {match.group(0)}"
            e['title'] = e['title'].replace(match.group(0), '').strip().lstrip('-').strip()
            
        # 2. Fix cases where date is just a number but title has the rest
        # Example: date="1", title="พ.ค.69 ..."
        match_title_date = re.match(r'^([ก-ฮ\.]+)\s*(\d{2})', e['title'])
        if match_title_date and len(e['date']) <= 5:
            e['date'] = f"{e['date']} {match_title_date.group(0)}"
            e['title'] = e['title'].replace(match_title_date.group(0), '').strip()

        # 3. Fix item 581/590 specifically
        if "70" in e['title'] and e['date'] in ["21", "ก.พ."]:
             # e.g. "21" and "- 30 ม.ค. 70 ..."
             # or "ก.พ." and "70 ..."
             combined = f"{e['date']} {e['title']}"
             date_match = re.search(r'(\d+.*70|ก\.พ\..*70)', combined)
             if date_match:
                 e['date'] = date_match.group(0)
                 e['title'] = combined.replace(e['date'], '').strip().lstrip('-').strip()

        # 4. Final title cleanup
        e['title'] = e['title'].lstrip('-').strip()
        
    with open('events.json', 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=4)
    print("Cleanup of events.json completed.")

if __name__ == "__main__":
    cleanup_imported_events()
