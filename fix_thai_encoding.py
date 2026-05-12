import json
import os

def clean_thai_text(text):
    if not isinstance(text, str):
        return text
    
    # Mapping of common corrupted Thai Unicode characters (from legacy PDF encoding)
    corrections = {
        "\uf701": "ิ", "\uf702": "ี", "\uf703": "ึ", "\uf704": "ื",
        "\uf705": "ั", "\uf706": "ํ", "\uf70a": "่", "\uf70b": "้",
        "\uf70c": "๊", "\uf70d": "๋", "\uf710": "็", "\uf711": "่",
        "\uf712": "้", "\uf713": "๊", "\uf714": "๋", "\uf715": "์",
        "\uf716": "ํ", "\uf717": "ู", "\uf718": "ู", "\uf719": "ุ",
        "\uf71a": "ู", "\uf70e": "์", "\uf71c": "ิ", "\uf71d": "ี",
        "\uf71e": "ึ", "\uf71f": "ื"
    }
    
    for corrupted, correct in corrections.items():
        text = text.replace(corrupted, correct)
    
    # Fix specific corrupted words/patterns found in events.json
    specific_fixes = {
        "ป็จฉิม": "ปัจฉิม",
        "เฝําระวัง": "เฝ้าระวัง",
        "ปํองกัน": "ป้องกัน",
        "ฟื๋นคืนชีพ": "ฟื้นคืนชีพ",
        "ปนเปื๋อน": "ปนเปื้อน",
        "ผู้นานักศึกษา": "ผู้นำนักศึกษา",
        "ปจ": "ปั",
        "ปจฉิม": "ปัจฉิม",
        "ฟื๋น": "ฟื้น",
        "เปื๋อน": "เปื้อน"
    }
    
    for corrupted, correct in specific_fixes.items():
        text = text.replace(corrupted, correct)
    
    return text

def fix_events_json():
    path = 'events.json'
    if not os.path.exists(path):
        print("events.json not found")
        return
        
    with open(path, 'r', encoding='utf-8') as f:
        events = json.load(f)
        
    for event in events:
        event['title'] = clean_thai_text(event['title'])
        event['date'] = clean_thai_text(event['date'])
        
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=4)
    
    print("Successfully cleaned Thai characters in events.json")

if __name__ == "__main__":
    fix_events_json()
