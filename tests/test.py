
import requests

# Deine Angaben
base_url = 'http://192.168.177.152:8123/api/' # Ich habe /states/ entfernt, um nur die API-Root zu testen (leichter)
access_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIxNWY0NDdiZmQ3YmE0YjUyYThkZmE4ZjQ0ZDVhZGJiOCIsImlhdCI6MTY5OTgyNzgwMywiZXhwIjoyMDE1MTg3ODAzfQ.4h69Q9XR4VNv71NcJmBezEmZNpi5WNEsSAhqgfD40Ow'  # Füge dein Access Token hier ein    }


# Der Header muss das Format "Bearer <Token>" haben
headers = {
    "Authorization": f"Bearer {access_token}",
    "content-type": "application/json",
}

try:
    # Wir testen einfach den API-Root-Status ("/") oder "/states/"
    response = requests.get(base_url, headers=headers, timeout=5)

    if response.status_code == 200:
        print("✅ Erfolg: Der Token ist GÜLTIG.")
        print(f"API Antwort: {response.text}") # Sollte {"message": "API running."} sein bei root
    elif response.status_code == 401:
        print("❌ Fehler: Der Token ist UNGÜLTIG oder abgelaufen (Unauthorized).")
    else:
        print(f"⚠️ Anderer Status-Code: {response.status_code}")

except requests.exceptions.ConnectionError:
    print("❌ Fehler: Konnte Home Assistant nicht erreichen (falsche IP oder Server offline).")
except Exception as e:
    print(f"Ein Fehler ist aufgetreten: {e}")