from constants import *
from station import Station
from main import Simulator
from multiprocessing import Queue, Process
from queue import Empty 
import time, os
log.disabled = True

def worker(task):
    while True:
        try:
            n, total_load = tasks.get_nowait()
            ampdu_sizes = defaultdict(int)
            queue_sizes = defaultdict(int)
            service_times = []
            drop_times = []
            service_times_per_stage = defaultdict(list)
            tx_trial_success = {i: {'trial': 0, 'success': 0} for i in range(MAX_STAGE+1)} #used to calculate p per stage
            thrps = []
            for seed in [0, 10, 100, 1000, 10000]:
                random.seed(seed)
                sim = Simulator(duration=30, n_sta=n, load=total_load*1e6/n, rts=rts)
                while sim.time <= sim.duration:
                    sim.run()
                n_packs = sum([sta.n_succ_packets for sta in sim.stations])
                for sta in sim.stations:
                    for i in range(1, MAX_AMPDU_SIZE+1, 1):
                        ampdu_sizes[i] += sta.ampdu_sizes[i]
                    for i in range(MAX_QUEUE_SIZE+1):
                        queue_sizes[i] += sta.q_sizes[i]
                    service_times += sta.service_times
                    drop_times += sta.drop_times
                    for stage, times in sta.service_times_per_stage.items():
                        service_times_per_stage[stage] += times 
                    for stage in range(MAX_STAGE+1):
                        tx_trial_success[stage]['trial'] += sta.tx_trial_success_per_stage[stage]['trial']
                        tx_trial_success[stage]['success'] += sta.tx_trial_success_per_stage[stage]['success']
                thrps.append(n_packs*PAYLOAD/(sim.duration-delta)/1e6)
            avg_aggr_size = sum([size*count for size, count in ampdu_sizes.items()]) / sum(list(ampdu_sizes.values()))
            pdf_ampdu_size = [count/sum(list(ampdu_sizes.values())) for size, count in ampdu_sizes.items()]
            pdf_queue_size = [count/sum(list(queue_sizes.values())) for size, count in queue_sizes.items()]
            tau, p = (sim.cnt['success'] + sim.cnt['collision'])/(sim.cnt['success'] + sim.cnt['collision'] + sim.cnt['idle']*n), sim.cnt['collision']/(sim.cnt['success'] + sim.cnt['collision'])
            avg_thrp = sum(thrps)/len(thrps)
            avg_service_time, avg_succ_service_time, avg_drop_time = sum(service_times+drop_times)/len(service_times+drop_times)*1e3, sum(service_times)/len(service_times)*1e3, 0 if not drop_times else sum(drop_times)/len(drop_times)*1e3
            print("load=%d n=%d thrp=%.3fMbps aggr=%.3f tau=%.3e p=%.3e b_e=%.6f avg_serv_time(s)=%.3e avg_succ_serv_time(s)=%.3e avg_drop_time(s)=%.3e"%(total_load, n, avg_thrp, avg_aggr_size, tau, p, pdf_queue_size[0], avg_service_time, avg_succ_service_time, avg_drop_time), end='\t')
            print("pdf_ampdu_size %s"%pdf_ampdu_size)
            pdf_queue_size = [round(pdf_queue_size[i], 6) for i in range(MAX_QUEUE_SIZE+1)]
        except Empty:
            break

for rts in [1]:
    json_dump = defaultdict(lambda: defaultdict(dict))
    tasks = Queue()
    for total_load in range(10, 610, 10):
        for n in [10, 15, 20]:
            tasks.put([n, total_load])
    procs = [Process(target=worker, args=(tasks,)) for i in range(min(tasks.qsize(), os.cpu_count()))]
    print(tasks.qsize(), " tasks created")
    print(len(procs), " processes created")
    [p.start() for p in procs]
    [p.join() for p in procs]
