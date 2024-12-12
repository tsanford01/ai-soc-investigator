#!/usr/bin/python3

import requests
import base64
import json
from urllib.parse import urlunparse
requests.packages.urllib3.disable_warnings()

# Add credentials
HOST = "poc.stellarcyber.cloud"
userid = "tsanford@stellarcyber.ai"
refresh_token = "bBhx8xhRg7hDleehoVh7A0oumr-KtGdEuIS6rfDSh3Vct1OKcdC1urKYW7qo5JVi6dBXOTU2gIodIlhPb_xY5Q"

def getAccessToken(userid, refresh_token):
    auth = base64.b64encode(bytes(userid + ":" + refresh_token, "utf-8")).decode("utf-8")
    headers = {
        "Authorization": "Basic " + auth,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    url = urlunparse(("https", HOST, "/connect/api/v1/access_token", "", "", ""))
    print(f"URL: {url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    res = requests.post(url, headers=headers, verify=False)
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.text}")
    if res.status_code == 200:
        return res.json()["access_token"]
    return None

if __name__ == "__main__":
    print("\nTesting authentication...")
    jwt = getAccessToken(userid, refresh_token)
    if jwt:
        print("\nSuccess! Got access token:")
        print(jwt)
    else:
        print("\nFailed to get access token")
