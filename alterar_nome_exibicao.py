import requests
import base64

url = 'https://manutencaocemag-4fu7.onrender.com/v1/account'

payload = {
    "cc": "55",
    "phone_number": "8596758103",
    "method": "sms",
    "cert": "CmsKJwiG5vHD1vn2AxIGZW50OndhIg5Tb2Z0d2FyZSBDRU1BR1CtzoPABhpAVuSYCstgNpa+bLOdyuwYRWZhPJeiP6dOu5TyJ9QbeMwRN/IZNAV3rM2THUZZ//qoJR8hmyNbc59SUAjyU+54DhIubRs+jJqS3VXgRIu3kKlkL5Jf7ORcxtiwiE9BTq08VR4KLTCOD+5zDCztxRo1rg==",
    "pin": "212834"
}

response = requests.post(url, json=payload)
print(response.status_code)
print(response.json())


import requests

url = "https://graph.facebook.com/v22.0/me/businesses"
headers = {"Authorization": "Bearer EAAwIFMrHx4cBOZBCakd7M5mav5ZBAJfUFZB2y8bTakplZBeKXPiFkRLQkA40ZCqstZASwTGbzywAVOZABRgV3GN2MW4klZBnqwnlU8LluSktpEV7yM2lRPJMiNt2WCOh5jyTOHhI5COFVwiafVh2TmqAVOJQJrtkPbMb00qAo3G28kRAtYSbupo3aZCCri4oinkD7kAZDZD"}
res = requests.get(url, headers=headers)
print(res.json())