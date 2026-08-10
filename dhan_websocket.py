import json
import websocket
import threading
import time
import logging

class DhanWebSocket:
    def __init__(self, client_id, access_token):
        self.client_id = client_id
        self.access_token = access_token
        self.ws_url = f"wss://api-feed.dhan.co?version=2&token={access_token}&clientId={client_id}&authType=2"
        self.is_connected = False
        self.latest_tick = {}
        self.should_run = True

    def on_message(self, ws, message):
        try:
            self.latest_tick = json.loads(message)
        except Exception as e:
            logging.error(f"WS Parse Error: {str(e)}")

    def on_error(self, ws, error):
        logging.error(f"WS Error: {str(error)}")

    def on_close(self, ws, close_status_code, close_msg):
        self.is_connected = False
        if self.should_run:
            time.sleep(5)
            self.start()

    def on_open(self, ws):
        self.is_connected = True

    def start(self):
        websocket.enableTrace(False)
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        wst = threading.Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()
