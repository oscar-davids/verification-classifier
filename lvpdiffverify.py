import os
import time
import psutil
import platform
import subprocess
import argparse
import logging
import glob
from verifier import Verifier

from collections import OrderedDict
from distutils import spawn
import xml.etree.ElementTree

def cpustatus():
    d = OrderedDict()
    d["time"] = time.time()
    util = psutil.cpu_percent()
    d["util"] = util
    pid = os.getpid()
    py = psutil.Process(pid)
    memoryUse = py.memory_info()[0] / 2. ** 30 * 1024  # MiB
    d["mem_used"] = memoryUse
    d["mem_used_per"] = py.memory_percent()
    # mem = psutil.virtual_memory()
    # d["mem_used_per"] =  memoryUse / mem.total * 100.0
    # from psutil import virtual_memory
    # mem = virtual_memory()
    # mem.total  # total physical memory available
    return d

def extract(elem, tag, drop_s):
    text = elem.find(tag).text
    if drop_s not in text: raise Exception(text)
    text = text.replace(drop_s, "")
    try:
        return int(text)
    except ValueError:
        return float(text)

def gpustatus():
    if platform.system() == "Windows":
        # If the platform is Windows and nvidia-smi
        # could not be found from the environment path,
        # try to find it from system drive with default installation path
        nvidia_smi = spawn.find_executable('nvidia-smi')
        if nvidia_smi is None:
            nvidia_smi = "%s\\Program Files\\NVIDIA Corporation\\NVSMI\\nvidia-smi.exe" % os.environ['systemdrive']
    else:
        nvidia_smi = "nvidia-smi"

    d = OrderedDict()
    d["time"] = time.time()

    cmd_out = subprocess.check_output([nvidia_smi, "-q", "-x"])

    gpu = xml.etree.ElementTree.fromstring(cmd_out).find("gpu")
    util = gpu.find("utilization")
    d["util"] = extract(util, "gpu_util", "%")

    d["mem_used"] = extract(gpu.find("fb_memory_usage"), "used", "MiB")
    totalmem = extract(gpu.find("fb_memory_usage"), "total", "MiB")
    d["mem_used_per"] = d["mem_used"] * 100 / totalmem

    return d

#python lvpdiffverify.py --v1path=master video path --v2path=slave video path --mode=cpu --loopcpunt=10
if __name__=="__main__":

    parser = argparse.ArgumentParser()
    # Required arguments.
    parser.add_argument("--v1path", default="", help="master video path for test.")
    parser.add_argument("--v2path", default="", help="slave video path for test.")
    parser.add_argument("--mode", default="cpu", help="calculation mode(skip, cpu, cuda) for test.")
    parser.add_argument("--loopcpunt",type=int, default=10, help="The loop count for test.")
    args = parser.parse_args()

    v1path = args.v1path
    v2path = args.v2path
    calcmode = args.mode
    loopcount = args.loopcpunt

    totaltime = 0
    totalgusage = 0.0
    totalgram = 0.0
    totalgper = 0.0
    totalcusage = 0.0
    totalcram = 0.0
    totalcper = 0.0

    correctcount = 0

    debug = False
    verifier = Verifier(10, 'http://storage.googleapis.com/verification-models/verification-metamodel-2020-07-06.tar.xz', False, False, debug)
    

    for i in range(loopcount):


        result_org = verifier.verify(v1path, [{'uri': v2path}])
        #print(result_org[0]['tamper'])

        start_time = time.time()
        result_lvpdiff = verifier.verifylvpfilter(v1path, [{'uri': v2path}], calcmode)
        #print(result_lvpdiff[0]['tamper'])
        totaltime += (time.time() - start_time)

        print(result_org[0]['tamper'] == result_lvpdiff[0]['tamper'])

        if result_org[0]['tamper'] == result_lvpdiff[0]['tamper']:
            correctcount = correctcount + 1

        gds = gpustatus()
        cds = cpustatus()
        totalgusage += gds["util"]
        totalgram += gds["mem_used"]
        totalgper += gds["mem_used_per"]

        totalcusage += cds["util"]
        totalcram += cds["mem_used"]
        totalcper += cds["mem_used_per"]

    executiontime = totaltime / loopcount

    totalgusage /= loopcount
    totalgram /= loopcount
    totalgper /= loopcount

    totalcusage /= loopcount
    totalcram /= loopcount
    totalcper /= loopcount

    correctper = correctcount * 100 / loopcount

    print("===================================")
    laststr = "Executiontime:{0:.2f}s GPU:{1:.2f}% CPU:{2:.2f}% GPU RAM:{3:.2f} MiB {4:.2f}% CPU RAM:{5:.2f} MiB {6:.2f}%".format(
        executiontime, totalgusage, totalcusage, totalgram, totalgper, totalcram, totalcper)
    print(laststr)
    print("===================================")
    print("accuracy percent = {0:.2f} %".format(correctper))
    print("===================================")