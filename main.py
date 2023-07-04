from constants import *
from station import Station
import json

class Simulator:
    def __init__(self, duration=1, n_sta = 5, load=10e6, rts=1):
        self.stations = [Station(interval=PAYLOAD/load) for _ in range(n_sta)]
        self.duration = duration
        self.time = 0.0
        self.rts_enabled = rts
        self.stations.sort()
        self.cnt = {'success':0, 'collision':0, 'idle':0}

    def get_duration(self, stas):
        assert len(stas) == 1 
        n_aggr = stas[0].hw_queue
        n_sym = math.ceil(n_aggr*(HEADER + PAYLOAD) / RATE / SYMBOL)
        if self.rts_enabled:
            return round(RTS + SIFS + CTS + SIFS + LEG_PREAMBLE + HT_PREAMBLE + n_sym * SYMBOL + SIFS + BACK, 6) 
        else:
            return round(LEG_PREAMBLE + HT_PREAMBLE + n_sym * SYMBOL + SIFS + BACK, 6)

    def get_collision_duration(self, stas):            
        if self.rts_enabled:
            return RTS + SIFS + CTS
        else:
            max_size = max([i.hw_queue for i in stas])
            n_sym = math.ceil(max_size*(HEADER + PAYLOAD) / RATE / SYMBOL)
            return round(LEG_PREAMBLE + HT_PREAMBLE + n_sym * SYMBOL + SIFS + BACK, 6)

    def handle_tx_start(self):
        min_cw = self.stations[0].cw
        assert min_cw >= 0
        self.time = round(self.stations[0].backoff_end, 6)
        log.debug("handle_tx_start at %.6f"%self.time)
        # txing_stas = [i for i in self.stations if i.backoff_end == self.time and i.queue]
        txing_stas = [i for i in self.stations if i.backoff_end == self.time and (i.queue or i.hw_queue)]
        assert txing_stas
        if len(txing_stas) == 1:
            self.cnt['success'] += 1
        elif len(txing_stas) > 1:
            self.cnt['collision'] += len(txing_stas)
        self.cnt['idle'] += self.stations[0].cw
        duration = self.get_duration(txing_stas) if len(txing_stas) == 1 else self.get_collision_duration(txing_stas)
        log.debug("%d stas txing %d packets for %.6f"%(len(txing_stas), txing_stas[0].hw_queue, duration))
        for sta in self.stations:
            # if sta.queue:
            if sta.queue or sta.hw_queue:
                # sta.cw -= min_cw
                remaining_slots = math.ceil(round((sta.backoff_end - self.time)/SLOT, 9))
                sta.cw = remaining_slots
                # log.debug("rem_slots %s %d"%(str(sta.name), sta.cw))
            assert sta.cw >= 0
            #change status
            # if sta.cw == 0 and sta.queue:
            if sta.cw == 0 and (sta.queue or sta.hw_queue):
                sta.status = "col" if len(txing_stas) > 1 else "tx"
            else:
                sta.status = 'rx'    
            #set backoff end
            if sta.status in ['tx', 'col']:
                # assert sta.queue
                assert sta.queue or sta.hw_queue
                sta.backoff_end = round(self.time + duration, 6)
            elif sta.status == 'rx':
                if self.stations[0].status == 'tx':
                    sta.backoff_end = round(self.time + duration + DIFS + sta.cw * SLOT, 6)
                elif self.stations[0].status == 'col':
                    sta.backoff_end = round(self.time + duration + DIFS + sta.cw * SLOT, 6)
                    # sta.backoff_end = round(self.time + duration + EIFS + sta.cw * SLOT, 6)
            else:
                assert False

    def handle_tx_finish(self):
        self.time = self.stations[0].backoff_end
        log.debug("handle_tx_finish at %.6f"%self.time)
        for sta in self.stations:
            if sta.status == "tx":
                sta.get_service_time(now=self.time)
                sta.reset_stage(now=self.time, success=True)
                sta.backoff_end = round(self.time + DIFS + sta.cw * SLOT, 6)
                
            elif sta.status == "col":
                sta.increase_stage(self.time)
                sta.backoff_end = round(self.time + DIFS + sta.cw * SLOT, 6)
                
            elif sta.status == "rx":
                pass
            sta.status = "idle"
    
    def handle_arrival(self):
        self.time = self.stations[0].next_arrival 
        log.debug("handle_arrival at %.6f"%self.time)
        for sta in self.stations:
            if sta.next_arrival == self.time:
                # prev_size = sta.queue
                sta.add_packet(self.time)
                # if prev_size != sta.queue:
                #     sta.q_sizes[sta.queue] += 1
                # if sta.queue == 1 and sta.status == "idle":
                if (sta.hw_queue == 1) and sta.status == "idle":
                    sta.backoff_end = round(self.time + DIFS + sta.cw * SLOT, 6)
            else:
                break

    def run(self):
        self.stations.sort()
        for sta in self.stations:
            log.debug("\t%s"%sta)
        first_sta = self.stations[0]
        if first_sta.next_arrival <= first_sta.backoff_end\
            or (first_sta.queue == 0 and first_sta.hw_queue == 0 ):
            self.handle_arrival()
        elif first_sta.status == 'idle':
            self.handle_tx_start()
        elif first_sta.status in ["tx", "col"]:
            self.handle_tx_finish()
        else:
            assert False
