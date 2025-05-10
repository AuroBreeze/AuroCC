from datetime import datetime
import pytz
from api.memory_store import MemoryStore

class MsgProcess:
    def __init__(self, user_id):
        self.bj_tz = pytz.timezone('Asia/Beijing')
        self.memory_store = MemoryStore(user_id)
        pass

    def Extract_msg_center(self):
        # Extract msg center from memory store
        
        pass