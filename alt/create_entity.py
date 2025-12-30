import requests
import requests

def create_entity(url, access_token, entity_id, friendly_name, state):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    payload = {
        'state': state,
        'attributes': {
            'friendly_name': friendly_name
        }
    }

    response = requests.post(f'{url}states/{entity_id}', json=payload, headers=headers)

    if response.status_code == 201:
        print(f'Erfolgreich erstellte Entität: {entity_id}')
    else:
        print(f'Fehler beim Erstellen der Entität {entity_id}. Statuscode: {response.status_code}')
        print(f'Fehlermeldung: {response.text}')



# Beispielaufruf mit deinem gegebenen URL und Access Token
base_url = 'http://192.168.177.185:8123/api/states/'
access_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIxNWY0NDdiZmQ3YmE0YjUyYThkZmE4ZjQ0ZDVhZGJiOCIsImlhdCI6MTY5OTgyNzgwMywiZXhwIjoyMDE1MTg3ODAzfQ.4h69Q9XR4VNv71NcJmBezEmZNpi5WNEsSAhqgfD40Ow'  # Füge dein Access Token hier ein    }


create_entity(base_url, access_token, 'test_entity', 'Test Entität', 'on')
