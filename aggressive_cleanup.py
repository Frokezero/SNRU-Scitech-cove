import json
import re

def aggressive_cleanup():
    with open('events.json', 'r', encoding='utf-8') as f:
        events = json.load(f)
    
    cleaned = []
    for e in events:
        date = e.get('date', '').strip()
        title = e.get('title', '').strip()
        
        # 1. Merge year from title to date
        # Pattern: title starts with "69 " or "70 "
        year_match = re.match(r'^(\d{2})\s+(.*)', title)
        if year_match:
            y = year_match.group(1)
            rest = year_match.group(2)
            if y in ['68', '69', '70']:
                date = f"{date} {y}"
                title = rest
        
        # 2. Fix range dates that leaked into title
        # Example: date="28 ก.พ.", title="- 1มี.ค.69 ..."
        range_match = re.match(r'^([-]\s*\d+.*?\d{2})\s+(.*)', title)
        if range_match:
            date = f"{date} {range_match.group(1)}"
            title = range_match.group(2)
            
        # 3. Handle cases where month and year are in title
        # Example: date="1", title="พ.ค. 69 ..."
        month_year_match = re.match(r'^([ก-ฮ\.]+)\s*(\d{2})\s+(.*)', title)
        if month_year_match and len(date) <= 3:
            date = f"{date} {month_year_match.group(1)} {month_year_match.group(2)}"
            title = month_year_match.group(3)

        # 4. Final cleaning
        title = title.lstrip('-').strip()
        title = title.replace('*', '') # Remove original asterisks if any left
        
        # 5. Fix specific known issues from PDF OCR
        # "ปจฉิม" -> "ปฐม" (OCR error)
        title = title.replace("ปจฉิม", "ปฐม")
        
        e['date'] = date
        e['title'] = title
        cleaned.append(e)
        
    with open('events.json', 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=4)
    print("Aggressive cleanup completed.")

if __name__ == "__main__":
    aggressive_cleanup()
