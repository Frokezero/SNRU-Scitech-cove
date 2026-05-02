import json

def replace_68_with_69():
    with open('events.json', 'r', encoding='utf-8') as f:
        events = json.load(f)
    
    for e in events:
        # Replace in date
        if '68' in e['date']:
            e['date'] = e['date'].replace('68', '69')
        
        # Replace in title
        if '68' in e['title']:
            e['title'] = e['title'].replace('68', '69')
            
    with open('events.json', 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=4)
    print("Successfully replaced all '68' with '69' in events.json")

if __name__ == "__main__":
    replace_68_with_69()
