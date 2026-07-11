import re
from datetime import datetime, timedelta

# List of weekday mappings
WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6
}

def parse_leave_request_text(text: str) -> dict:
    """
    NLP-lite Request Parser using regex and rule-based keyword extraction.
    Parses requests like: 'I need leave tomorrow for period 3 and 4 due to medical checkup'
    """
    text_lower = text.lower()
    
    # 1. Parse Dates (today, tomorrow, next [weekday], or DD-MM-YYYY)
    today = datetime.now().date()
    start_date = today
    end_date = today
    
    # Check for relative keywords
    if "tomorrow" in text_lower:
        start_date = today + timedelta(days=1)
        end_date = start_date
    elif "day after tomorrow" in text_lower:
        start_date = today + timedelta(days=2)
        end_date = start_date
    elif "today" in text_lower:
        start_date = today
        end_date = today
    else:
        # Check for weekday names
        weekday_found = False
        for day_name, day_idx in WEEKDAYS.items():
            if day_name in text_lower:
                # Find the next occurrence of this weekday
                days_ahead = day_idx - today.weekday()
                if days_ahead <= 0:  # Target day is earlier in the week, or is today
                    days_ahead += 7
                start_date = today + timedelta(days=days_ahead)
                end_date = start_date
                weekday_found = True
                break
                
        if not weekday_found:
            # Check for standard date pattern (e.g. YYYY-MM-DD or DD-MM-YYYY or DD/MM/YYYY)
            date_matches = re.findall(r'(\d{1,4}[-/]\d{1,2}[-/]\d{1,4})', text_lower)
            if date_matches:
                raw_date = date_matches[0]
                # Replace slashes with dashes
                raw_date = raw_date.replace("/", "-")
                parts = raw_date.split("-")
                try:
                    if len(parts[0]) == 4: # YYYY-MM-DD
                        start_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
                    else: # DD-MM-YYYY
                        start_date = datetime.strptime(raw_date, "%d-%m-%b" if len(parts[2]) == 3 else "%d-%m-%Y").date()
                    end_date = start_date
                except Exception:
                    # Fallback to tomorrow if parsing fails
                    start_date = today + timedelta(days=1)
                    end_date = start_date

    # 2. Parse Periods (e.g. "period 3", "periods 3 and 4", "p2", "p3,4")
    periods = []
    
    # Check for full day triggers
    full_day_triggers = ["full day", "all day", "complete day", "entire day", "whole day"]
    is_full_day = any(trigger in text_lower for trigger in full_day_triggers)
    
    if not is_full_day:
        # Match 'period(s) X', 'pX', 'period(s) X and Y', 'period(s) X, Y, Z'
        # e.g., "period 3", "periods 2, 3 and 4", "p3", "p 4"
        period_matches = re.findall(r'(?:period|periods|p)\s*(\d+(?:\s*(?:,|and|&)\s*\d+)*)', text_lower)
        if period_matches:
            # Join and extract all digits
            digits = re.findall(r'\d+', period_matches[0])
            periods = sorted(list(set(int(d) for d in digits)))
            # Keep within valid periods (1-6)
            periods = [p for p in periods if 1 <= p <= 6]
            
        # If no explicit periods and not full day, assume full day
        if not periods:
            is_full_day = True

    # 3. Parse substitute cover / swap requests (e.g. "can John cover", "swap with Jane")
    cover_faculty = None
    cover_matches = re.findall(r'(?:cover|swap|substitute)\s+(?:by|with|for)?\s*([a-zA-Z]+)', text_lower)
    # Ignore common stop words that might match
    stop_words = ["me", "my", "tomorrow", "today", "the", "a", "an", "on", "for"]
    if cover_matches:
        cand = cover_matches[0].strip()
        if cand not in stop_words:
            cover_faculty = cand.capitalize()

    # 4. Extract reason (guess anything after "due to", "because of", "for")
    reason = "Personal Leave"
    reason_matches = re.findall(r'(?:due to|because of|reason:)\s+([^.\n]+)', text_lower)
    if reason_matches:
        reason = reason_matches[0].strip().capitalize()
        
    return {
        "start_date": start_date,
        "end_date": end_date,
        "periods": None if is_full_day else periods,
        "reason": reason,
        "suggested_cover_faculty": cover_faculty
    }
