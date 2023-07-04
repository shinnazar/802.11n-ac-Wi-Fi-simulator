from constants import *

class Station:
    id = 0
    def __init__(self, interval=float('inf'), rts = True):
        self.name = "sta " + str(Station.id)
        self.cw = random.randint(0, CW_MIN-1)
        self.status = "idle"
        self.stage = 0
        self.n_succ_packets = 0
        self.queue = 0
        self.arrival_interval = interval
        self.rts = rts
        self.next_arrival = float('inf') if interval == float('inf') else round(random.expovariate(lambd=1.0/interval), 6)
        self.backoff_end = round(DIFS + self.cw * SLOT, 6)
        self.hw_queue = 0
        self.ampdu_sizes = {i:0 for i in range(MAX_AMPDU_SIZE+1)} #to collect all a-mpdu sizes
        self.q_sizes = {i:0 for i in range(MAX_QUEUE_SIZE+1)} #defaultdict(int) #to collect all queue sizes after successful/discarded frame
        self.service_start = -1
        self.service_times = []
        self.drop_times = []
        self.service_times_per_stage = defaultdict(list)
        Station.id += 1
        self.anomalous_slot = 0
        self.tx_trial_success_per_stage = {i: {'trial': 0, 'success': 0} for i in range(MAX_STAGE+1)} #used to calculate p per stage
    
    def get_service_time(self, now):
        service_time = now - self.service_start
        if not self.anomalous_slot:
            log.debug("%s service_time %.3fms"%(self.name, service_time*1000))
            self.service_times.append(service_time)
            self.service_times_per_stage[self.stage].append(service_time)
        else:
            log.debug("%s service_time_anomalous_slot %.3fms"%(self.name, service_time*1000))
        assert self.service_start >= 0 and service_time > 0

    def reset_stage(self, now, success=True):
        if success:
            self.tx_trial_success_per_stage[self.stage]['success'] += 1
        for i in range(self.stage+1):
            self.tx_trial_success_per_stage[i]['trial'] += 1    
        self.anomalous_slot = 0
        self.stage = 0
        self.cw = random.randint(0, CW_MIN-1)
        ampdu_size = self.hw_queue if success else 0
        queue_size = self.queue
        self.hw_queue = 0
        if now >= delta:
            self.n_succ_packets += ampdu_size if success else 0
            self.ampdu_sizes[ampdu_size] += 1
            self.q_sizes[queue_size] += 1
        if self.queue:   
            self.set_hw_queue(now)
    
    def set_hw_queue(self, now):
        if self.hw_queue == 0:
            self.hw_queue = min(MAX_AMPDU_SIZE, self.queue)
            self.queue -= self.hw_queue
            self.service_start = now
        elif self.hw_queue < MAX_AMPDU_SIZE and self.queue:
            new_hw_queue = min(MAX_AMPDU_SIZE, self.queue + self.hw_queue)
            self.queue -= new_hw_queue - self.hw_queue
            self.hw_queue = new_hw_queue
        if self.next_arrival == float('inf') and self.queue < MAX_QUEUE_SIZE:
            self.next_arrival = self.get_next_arrival(self.backoff_end)
    
    def get_drop_time(self, now):
        drop_time = now - self.service_start
        log.debug("%s drop_time %.3fms"%(self.name, drop_time*1000))
        self.drop_times.append(drop_time)
        assert self.service_start >= 0 and drop_time > 0

    def increase_stage(self, now):
        if self.stage >= MAX_STAGE:
            self.get_drop_time(now)
            self.reset_stage(now = now, success = False)
        else:
            self.stage += 1
            self.cw = random.randint(0, min(2**self.stage * CW_MIN, CW_MAX)-1)
        if self.queue > 0 and self.hw_queue < MAX_AMPDU_SIZE:
            self.set_hw_queue(now)
    
    def get_next_arrival(self, current_time):
        return round(current_time + random.expovariate(lambd=1.0/self.arrival_interval), 6)

    def add_packet(self, now):
        if self.queue < MAX_QUEUE_SIZE:
            self.queue += 1
            if self.hw_queue < MAX_AMPDU_SIZE and self.status not in ['col', 'tx']:
                self.set_hw_queue(now)            
            if self.queue < MAX_QUEUE_SIZE:
                self.next_arrival = self.get_next_arrival(now)
            else:
                self.next_arrival = float('inf')

    def get_duration(self):
        n_sym = math.ceil((HEADER + PAYLOAD) / RATE / SYMBOL)
        return round(LEG_PREAMBLE + HT_PREAMBLE + n_sym * SYMBOL + SIFS + BACK + DIFS, 6)

    def __lt__(self, other):
        self_event, other_event = min(self.backoff_end, self.next_arrival), min(other.backoff_end, other.next_arrival)
        if (self.queue or self.hw_queue) and (other.queue or other.hw_queue):
            if self_event != other_event:
                return self_event <= other_event
            elif self_event in [self.next_arrival, other.next_arrival]:
                return self.next_arrival <= other.next_arrival
            return self_event <= other_event
        elif not (self.queue or self.hw_queue) and not (other.queue or other.hw_queue):
            return self.next_arrival <= other.next_arrival
        elif not (self.queue or self.hw_queue) and (other.queue or other.hw_queue):
            return self.next_arrival <= other_event 
        elif (self.queue or self.hw_queue) and not (other.queue or other.hw_queue):
            return self_event <= other.next_arrival
        else:
            assert False

    def __str__(self):
        return "%-9sstat=%-5sstage=%d cw=%-4d b_end=%-9.6f q_size=%-3d hw_q_size=%-3d n_arr=%-9.6f n_succ_packets=%d"%(self.name, self.status, self.stage, self.cw, self.backoff_end, self.queue, self.hw_queue, self.next_arrival, self.n_succ_packets)\
            + " %s"%({i:[self.tx_trial_success_per_stage[i]['trial'], self.tx_trial_success_per_stage[i]['success']] for i in range(MAX_STAGE+1)})

def range_prod(lo,hi):
    if lo+1 < hi:
        mid = (hi+lo)//2
        return range_prod(lo,mid) * range_prod(mid+1,hi)
    if lo == hi:
        return lo
    return lo*hi

def treefactorial(n):
    if n < 2:
        return 1
    return range_prod(1,n)
