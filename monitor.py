import os
import time
import psutil
import logging as log
from psutil._common import bytes2human
from datetime import datetime

# ps -e -o pid,user,cpu,size,rss,cmd --sort -size,-rss | grep chroma 
# ps -e -o pid,user,cpu,size,rss,cmd --sort -size,-rss | grep bot.py 


# Включаем логирование, чтобы не пропустить важные сообщения
log.basicConfig(level=log.INFO, filename='mem_log.txt',
                        filemode="w")


def bytes_to_gb(bytes_value):
    return bytes_value / (1024 ** 3)


def get_process_info():
    pid = os.getpid()
    p = psutil.Process(pid)
    with p.oneshot():
        mem_info = p.memory_info()
        # disk_io = p.io_counters()
    return {
        "memory_usage": bytes_to_gb(mem_info.rss),
    }


def pprint_ntuple(nt):
    for name in nt._fields:
        value = getattr(nt, name)
        if name != 'percent':
            value = bytes2human(value)
        log.info('%-10s : %7s' % (name.capitalize(), value))


def step():

    time_current = datetime.now()
    log.info('TIME\n----')
    log.info(time_current)
    log.info('MEMORY\n------')
    pprint_ntuple(psutil.virtual_memory())
    log.info('\nSWAP\n----')
    pprint_ntuple(psutil.swap_memory())


for i in range(1000):
    step()
    time.sleep(10)
