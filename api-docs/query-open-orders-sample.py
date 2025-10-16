# List all open orders on Spot.

import http.client
import urllib.request
import urllib.parse
import hashlib
import hmac
import base64
import json
import time

def main():
   response = request(
      method="POST",
      path="/0/private/OpenOrders",
      public_key="1sH9KQNClmVU031IDq5JYwWUp17Ge7eSrL8rpMmZ3j7VG+aST23KrfVi",
      private_key="J0Qwq4Za4bCcch+sErbHPGvGalEw7E5CsLpx1UkSTHcY3AlztK6CO2trh6IxAQwOkt2u4B7jTwA5l8raABkqUw==",
      environment="https://api.kraken.com",
   )
   print(response.read().decode())

def request(method: str = "GET", path: str = "", query: dict | None = None, body: dict | None = None, public_key: str = "", private_key: str = "", environment: str = "") -> http.client.HTTPResponse:
   url = environment + path
   query_str = ""
   if query is not None and len(query) > 0:
      query_str = urllib.parse.urlencode(query)
      url += "?" + query_str
   nonce = ""
   if len(public_key) > 0:
      if body is None:
         body = {}
      nonce = body.get("nonce")
      if nonce is None:
         nonce = get_nonce()
         body["nonce"] = nonce
   headers = {}
   body_str = ""
   if body is not None and len(body) > 0:
      body_str = json.dumps(body)
      headers["Content-Type"] = "application/json"
   if len(public_key) > 0:
      headers["API-Key"] = public_key
      headers["API-Sign"] = get_signature(private_key, query_str+body_str, nonce, path)
   req = urllib.request.Request(
      method=method,
      url=url,
      data=body_str.encode(),
      headers=headers,
   )
   return urllib.request.urlopen(req)

def get_nonce() -> str:
   return str(int(time.time() * 1000))

def get_signature(private_key: str, data: str, nonce: str, path: str) -> str:
   return sign(
      private_key=private_key,
      message=path.encode() + hashlib.sha256(
            (nonce + data)
         .encode()
      ).digest()
   )

def sign(private_key: str, message: bytes) -> str:
   return base64.b64encode(
      hmac.new(
         key=base64.b64decode(private_key),
         msg=message,
         digestmod=hashlib.sha512,
      ).digest()
   ).decode()


if __name__ == "__main__":
   main()

# Example output of query open orders
#    {
#   "error": [],
#   "result": {
#     "open": {
#       "OZAFUQ-6FB7W-GR63OS": {
#         "refid": null,
#         "userref": 0,
#         "status": "open",
#         "opentm": 1760578655.936616,
#         "starttm": 0,
#         "expiretm": 0,
#         "descr": {
#           "pair": "XXBTZUSDT",
#           "aclass": "forex",
#           "type": "buy",
#           "ordertype": "trailing-stop",
#           "price": "+15.0000%",
#           "price2": "0",
#           "leverage": "none",
#           "order": "buy 0.00006000 XXBTZUSDT @ trailing stop +15.0000%",
#           "close": ""
#         },
#         "vol": "0.00006000",
#         "vol_exec": "0.00000000",
#         "cost": "0.00000",
#         "fee": "0.00000",
#         "price": "0.00000",
#         "stopprice": "127605.90000",
#         "limitprice": "110961.70000",
#         "misc": "",
#         "oflags": "fciq",
#         "trigger": "index"
#       },
#       "ORWBHN-LMPRM-TG4RWJ": {
#         "refid": null,
#         "userref": 0,
#         "status": "open",
#         "opentm": 1760578459.280463,
#         "starttm": 0,
#         "expiretm": 0,
#         "descr": {
#           "pair": "XXBTZUSDT",
#           "aclass": "forex",
#           "type": "sell",
#           "ordertype": "trailing-stop",
#           "price": "+10.0000%",
#           "price2": "0",
#           "leverage": "none",
#           "order": "sell 0.00005000 XXBTZUSDT @ trailing stop +10.0000%",
#           "close": ""
#         },
#         "vol": "0.00005000",
#         "vol_exec": "0.00000000",
#         "cost": "0.00000",
#         "fee": "0.00000",
#         "price": "0.00000",
#         "stopprice": "99874.10000",
#         "limitprice": "110971.20000",
#         "misc": "",
#         "oflags": "fcib",
#         "trigger": "index"
#       }
#     }
#   }
# }