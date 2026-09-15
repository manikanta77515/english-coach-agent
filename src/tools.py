# src/tools.py
import json

def get_telugu_translation(english_word: str) -> str:
    """
    Get the Telugu translation of an English word.
    
    Args:
        english_word: The English word to translate.
        
    Returns:
        The Telugu translation as a JSON string.
    """
    dictionary = {
        "opportunity": "అవకాశం (Avakasam)",
        "confidence": "ఆత్మవిశ్వాసం (Atmaviswasam)",
        "success": "విజయం (Vijayam)",
        "practice": "సాధన (Sadhana)",
        "grammar": "వ్యాకరణం (Vyakarana)"
    }
    translation = dictionary.get(english_word.lower(), "Translation not found in our database.")
    return json.dumps({"word": english_word, "translation": translation})

def save_user_mistake(mistake: str, correction: str) -> str:
    """
    Saves a grammar or vocabulary mistake made by the user to a local file so the coach can track their progress.
    
    Args:
        mistake: The incorrect English sentence or word.
        correction: The correct English version.
        
    Returns:
        A success message confirming it was saved.
    """
    # This writes to a physical file on your hard drive!
    with open("mistake_log.txt", "a", encoding="utf-8") as f:
        f.write(f"Mistake: {mistake} | Correction: {correction}\n")
    
    return "Success: The mistake has been permanently saved to mistake_log.txt."


# src/tools.py
import json
import os # Make sure this is at the top of the file!

# ... (keep your existing get_telugu_translation and save_user_mistake functions here) ...

def review_past_mistakes() -> str:
    """
    Reads the user's past grammar and vocabulary mistakes from the local mistake log.
    Use this tool when the user asks to review their mistakes or wants a practice exercise based on past errors.
    
    Returns:
        A string containing all past mistakes, or a message saying no mistakes are found.
    """
    file_path = "mistake_log.txt"
    
    # Check if the file exists first so our program doesn't crash
    if not os.path.exists(file_path):
        return "No mistakes have been logged yet. The user has a clean record!"
    
    # Open and read the file
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if not content.strip():
        return "The mistake log is empty."
        
    return f"Here are the user's past mistakes:\n{content}"


