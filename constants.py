import math
import random
import logging
from collections import defaultdict 
log = logging.getLogger("my_logger")
handler = logging.StreamHandler()
log.addHandler(handler)
log.setLevel(logging.DEBUG)
log.disabled = True

SIFS = 16e-6            #s
SLOT = 9e-6             #s
DIFS = SIFS + 2*SLOT    #s
EIFS = DIFS - SLOT
BACK = 32e-6            #s
PAYLOAD = 800*8         #bits
HEADER = 66*8           #bits
RATE = 150e6            #bps
CW_MIN = 16
CW_MAX = 1024
MAX_STAGE = 6
RTS = 34e-6             #s
CTS = 44e-6             #s
LEG_PREAMBLE = 20e-6    #s
HT_PREAMBLE = 16e-6    #s
SYMBOL = 4e-6           #s
MAX_QUEUE_SIZE = 150    #packets
MAX_AMPDU_SIZE = 64     #packets
delta = 1             #used for accuracy
