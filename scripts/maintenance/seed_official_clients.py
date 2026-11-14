import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"

def seed_clients():
    # 1. Create Industry
    industry_data = {
        "name": "Turnpike Global Partners",
        "icon": "Globe"
    }
    res = requests.post(f"{BASE_URL}/content/client-industries", json=industry_data)
    if res.status_code not in (200, 201):
        print("Failed to create industry:", res.text)
        # Maybe it already exists, fetch it
        res = requests.get(f"{BASE_URL}/content/client-industries")
        industries = res.json()
        industry = next((i for i in industries if i["name"] == "Turnpike Global Partners"), None)
        if not industry:
            return
    
    # 2. Add clients to this industry
    clients = [
        {"name": "Agilent", "img": "https://icon.horse/icon/agilent.com"},
        {"name": "Infor", "img": "https://icon.horse/icon/infor.com"},
        {"name": "Telekom", "img": "https://icon.horse/icon/telekom.com"},
        {"name": "ABB", "img": "https://icon.horse/icon/abb.com"},
        {"name": "Kaiser", "img": "https://icon.horse/icon/kaiserpermanente.org"},
        {"name": "American National", "img": "https://icon.horse/icon/americannational.com"},
        {"name": "KeyBank", "img": "https://icon.horse/icon/key.com"},
        {"name": "Citi", "img": "https://icon.horse/icon/citi.com"},
        {"name": "BD", "img": "https://icon.horse/icon/bd.com"},
        {"name": "3M", "img": "https://icon.horse/icon/3m.com"},
        {"name": "Plexus", "img": "https://icon.horse/icon/plexus.com"},
        {"name": "American Airlines", "img": "https://icon.horse/icon/aa.com"},
        {"name": "United Airlines", "img": "https://icon.horse/icon/united.com"},
    ]
    
    payload = {
        "category": "Turnpike Global Partners",
        "cols": 4,
        "clients": clients
    }
    
    # Try fetching first to see if it exists
    res = requests.get(f"{BASE_URL}/content/clients")
    all_cats = res.json()
    cat = next((c for c in all_cats if c["category"] == "Turnpike Global Partners"), None)
    
    if cat:
        # Update
        res = requests.put(f"{BASE_URL}/content/clients/{cat['_id']}", json=payload)
        print("Updated clients:", res.status_code)
    else:
        res = requests.post(f"{BASE_URL}/content/clients", json=payload)
        print("Created clients:", res.status_code)

if __name__ == "__main__":
    seed_clients()
