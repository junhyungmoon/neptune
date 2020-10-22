import glob
import itertools
import numpy as np
import csv

def merge_one_night_files(rootPath, subNum):
    if subNum < 10:
        fPath = rootPath + "P0" + str(subNum)
    else:
        fPath = rootPath + "P" + str(subNum)

    nePathList = sorted(glob.glob(fPath + "\\raw\\NE\\*.csv"))
    moPathList = sorted(glob.glob(fPath + "\\raw\\MO\\*.csv"))

    firstDate = -1
    firstTime = -1
    destMOFile = ''
    destNEFile = ''
    for neFilePath, moFilePath in zip(nePathList, moPathList):
        fpathWords = [x.strip() for x in neFilePath.split('\\')]
        fnameWords = [x.strip() for x in fpathWords[-1].split('_')]
        if firstDate != -1:
            diff = (int(fnameWords[3]) - firstDate)*240000 + (int(fnameWords[4]) - firstTime)
            if diff >= 160000:
                firstDate = -1
                destNEFile.close()
        if firstDate == -1: # 3: date, 4: time
            firstDate = int(fnameWords[3])
            firstTime = int(fnameWords[4])
            tmp = [fPath, '\\merged\\NE\\', fnameWords[3], '_', fnameWords[4], '.csv']
            destNEFile = open(''.join(tmp), 'a')
            tmp = [fPath, '\\merged\\MO\\', fnameWords[3], '_', fnameWords[4], '.csv']
            destMOFile = open(''.join(tmp), 'a')
        srcNEFile = open(neFilePath, 'r')
        srcMOFile = open(moFilePath, 'r')
        for row in srcNEFile:
            destNEFile.write(row)
        for row in srcMOFile:
            destMOFile.write(row)
        srcNEFile.close()
        srcMOFile.close()


def examineNEfiles(rootPath, subNum):
    if subNum < 10:
        fPath = rootPath + "P0" + str(subNum) + "\\merged\\NE\\*.csv"
    else:
        fPath = rootPath + "P" + str(subNum) + "\\merged\\NE\\*.csv"

    fPathList = sorted(glob.glob(fPath))

    for fname in fPathList:
        inFile = open(fname, "r")

        prevSeqNum = -1
        cnt = 0
        while True:
            line = inFile.readline()  # ex) SEQ=70332, NE=0, Bia=1, HR=65, NA, 2018-12-10 03:23:57.952
            if not line:
                break
            lineData = [x.strip() for x in line.split(',')]  # ex) ['SEQ=70332', 'NE=0', 'Bia=1', 'HR=65', 'NA', '2018-12-10 03:23:57.952']
            if lineData[0][0].isalpha():  # header
                SeqNum = int(lineData[0].replace("SEQ=", ""))
                if SeqNum <= prevSeqNum and cnt > 1:
                    print(fname + " has SEQ which is not in increasing order")
                    print("It occurs in line " + str(cnt) + " (SEQ: " + str(SeqNum) + ")")
                if SeqNum - prevSeqNum >= 14400 and cnt > 1: # 14400 packets correspond to 1-hour
                    print(fname + " has more than 1-hour loss")
                    print("It occurs in line " + str(cnt) + " (SEQ: " + str(SeqNum) + ")")
                if cnt % 65 != 0:
                    print(fname + " has a group of data which are not 64 instances")
                    print("It occurs in line " + str(cnt) + " (SEQ: " + str(SeqNum) + ")")
                    cnt = 0
                if not lineData[0] or not lineData[1] or not lineData[2] or not lineData[3] or not lineData[4] or not lineData[5]:
                    print(fname + " has partial data loss (several elements in the same line)")
                    print("It occurs in line " + str(cnt) + " (SEQ: " + str(SeqNum) + ")")
                prevSeqNum = SeqNum
            else:  # data
                if cnt % 65 == 0:
                    print(fname + " has a group of data which are not 64 instances")
                    print("It occurs in line " + str(cnt) + " (SEQ: " + str(SeqNum) + ")")
                if not lineData[0] or not lineData[1] or not lineData[2]:
                    print(fname + " has partial data loss (several elements in the same line)")
                    print("It occurs in line " + str(cnt) + " (SEQ: " + str(SeqNum) + ")")
            cnt += 1
        inFile.close()


def examineMOfiles(rootPath, subNum):
    if subNum < 10:
        fPath = rootPath + "P0" + str(subNum) + "\\merged\\MO\\*.csv"
    else:
        fPath = rootPath + "P" + str(subNum) + "\\merged\\MO\\*.csv"

    fPathList = sorted(glob.glob(fPath))

    for fname in fPathList:
        inFile = open(fname, "r")

        prevSeqNum = -1
        cnt = 0
        while True:
            # ex) G, 0, 54:41.166,-84.878, -27.561, -74.085 (accel or gyro / left or right / time / x / y / z)
            line = inFile.readline()
            if not line:
                break
            lineData = [x.strip() for x in line.split(',')]

            if not lineData[0] or not lineData[1] or not lineData[2] or not lineData[3] or not lineData[4] or not lineData[5]:
                print(fname + " has partial data loss (several elements in the same line)")
                print("It occurs in line " + str(cnt))

            cnt += 1
        inFile.close()