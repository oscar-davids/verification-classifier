import os
import argparse
import datetime
import csv
import numpy as np
import random
from verifier import Verifier

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--srcdir", default="", help="source video file directory")
    parser.add_argument("--renddir", default="", help="rendition video file directory")
    parser.add_argument("--infile", default="in.csv", help="csv file to calculate diff features.")
    parser.add_argument("--negative", default=0, type=int, help="csv file to calculate diff features.")
    args = parser.parse_args()

    infile = args.infile
    srcdir = args.srcdir
    renddir = args.renddir
    negative = args.negative

    outcsv = "difffeature" + datetime.datetime.now().strftime("%m%d%H") + ".csv"
    fileout = open(outcsv, 'w', newline='')
    wr = csv.writer(fileout)
    wr.writerow(['filepath', 'width', 'height', 'fps', 'bitrate',
                 'profile', 'devmode', 'framecount', 'indices', 'outpath', 'position', 'length', 'features', 'target'])
    max_samples = 10
    debug = False
    logcount = 0
    
    #verifier = Verifier(10, 'verification-metamodel-2020-07-06.tar.xz', False, False, debug)
    verifier = Verifier(10, 'http://storage.googleapis.com/verification-models/verification-metamodel-2020-07-06.tar.xz', False, False, debug)

    brheader = False
    with open(infile) as csvfile:
        rd = csv.reader(csvfile, delimiter=',')
        for row in rd:
            print( str(logcount) + "-----" + "start")
            logcount = logcount + 1
            wrow = []
            difffeatures = ""
            if brheader == False:
                brheader = True
            else:
                srcfile = srcdir + "/" + row[0]
                rendfile = renddir + "/" + row[9].replace('"','')
                indicies = row[8]
                wrow = row

                if negative != 0:
                    if logcount%2 == 0:
                        #create randomize features
                        list_rx = [random.uniform(0, 1000000) for i in range(6)]
                        difffeatures = '"'
                        for i in range(5):
                            difffeatures += (str(list_rx[i]) + ",")
                        difffeatures += str(list_rx[5])
                        difffeatures += '"'
                    else:
                        # create zero features
                        difffeatures = '"' + '0.0,0.0,0.0,0.0,0.0,0.0' + '"'

                    wrow.append(difffeatures)
                    wrow.append(1)
                else:
                    file_stats = os.stat(srcfile)
                    result = verifier.getfeature(srcfile, [{'uri': rendfile}], indicies)

                    difffeatures = np.array2string(result[0]['difffeature'], precision=10, separator=',',
                                    suppress_small=False)
                    difffeatures = difffeatures.replace('[','')
                    difffeatures = difffeatures.replace(']', '')
                    difffeatures = difffeatures.replace('\n', '')
                    difffeatures = '"' + difffeatures + '"'


                    wrow.append(difffeatures)
                    wrow.append(result[0]['tamper'])

                wr.writerow(wrow)

    fileout.close()
    print('Success calculation diff features!')