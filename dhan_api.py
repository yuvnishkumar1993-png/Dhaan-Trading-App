def verify_dhan_credentials(client_id, access_token):
    # /fund के बजाय /holdings का उपयोग करें जो Dhan API में पूरी तरह वैध है
    url = "https://api.dhan.co/v2/holdings"
    headers = {
        "access-token": access_token, 
        "client-id": client_id, 
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return True, "Success"
        elif response.status_code == 401:
            return False, "Token Expired or Invalid"
        elif response.status_code == 404:
            return False, "API Endpoint Not Found (404)"
        return False, f"API Error {response.status_code}"
    except Exception as e:
        return False, f"Connection Failed: {str(e)}"
