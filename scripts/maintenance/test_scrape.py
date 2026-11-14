import urllib.request

req = urllib.request.Request(
    'https://www.turnpikeanalyst.com/services/', 
    headers={'User-Agent': 'Mozilla/5.0'}
)
try:
    with urllib.request.urlopen(req) as response:
        print("Status Code:", response.getcode())
        print(response.read().decode('utf-8')[:500])
except Exception as e:
    print(f"Failed: {e}")
