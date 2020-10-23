import glob
import itertools
import numpy as np
import csv
import math

def merge_one_night_files(fPath):
    # Merge NE files (Mo files) into one NE file (one Mo file)
    # No manipulation of data such as interpolation, normalization, etc.

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
            if int(fnameWords[3]) - firstDate > 30: # month shift
                diff = 240000 + (int(fnameWords[4]) - firstTime)
            else:
                diff = (int(fnameWords[3]) - firstDate)*240000 + (int(fnameWords[4]) - firstTime)
            if diff >= 160000: # Empirically determine that difference of more than 16 hours indicates day shift.
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


def examineNEfiles(fPathList):
    # Check data in terms of a few criteria
    for fname in fPathList:
        inFile = open(fname, "r")

        SeqNum = -1
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
                    print(fname + " has partial data loss (loss of several elements in the same line)")
                    print("It occurs in line " + str(cnt) + " (SEQ: " + str(SeqNum) + ")")
            cnt += 1
        inFile.close()


def examineMOfiles(fPathList):
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
                print(fname + " has partial data loss (loss of several elements in the same line)")
                print("It occurs in line " + str(cnt))

            cnt += 1
        inFile.close()


def interpolateNEfiles(srcFilePath, destFilePath):
    # fill dummy data for the lost packets
    srcFile = open(srcFilePath, "r")
    destFile = open(destFilePath, "w")

    prevSeqNum = -1
    prevSec = -1
    cnt = 0
    while True:
        line = srcFile.readline()  # ex) SEQ=70332, NE=0, Bia=1, HR=65, NA, 2018-12-10 03:23:57.952
        if not line:
            break
        lineData = [x.strip() for x in line.split(',')]  # ex) ['SEQ=70332', 'NE=0', 'Bia=1', 'HR=65', 'NA', '2018-12-10 03:23:57.952']
        SeqNum = int(lineData[0].replace("SEQ=", ""))
        timeData = [x.strip() for x in lineData[-1].split(' ')] # '2018-12-10 03:23:57.952'
        hmsData = [x.strip() for x in timeData[-1].split(':')] # '03:23:57.952'
        currSec = float(hmsData[0])*3600 + float(hmsData[1])*60 + float(hmsData[2]) # seconds
        # interpolate lost packets which locate before the current packet
        if cnt != 0: # except the first packet
            loopCnt = SeqNum - prevSeqNum - 1 # ex) previous seq. 0 ~ current seq. 3: interpolate two packets (1,2)
            # check whether SeqNum is 0 or not
            if SeqNum == 0:
                if prevSec > currSec: # check whether day shifts or not
                    currSec += (24*3600)
                secDiff = currSec - prevSec
                loopCnt = math.floor(secDiff)*4 # 4 packets per 1 second
            # fill dummy data
            for k in range(loopCnt):
                # header
                tmp = [lineData[1], ',', lineData[2], '\n']
                destFile.write(''.join(tmp))
                # data
                for i in range(64):
                    destFile.write("-1,-1,-1\n")
        # current packet
        tmp = [lineData[1], ',', lineData[2], '\n']
        destFile.write(''.join(tmp))
        for z in range(64):  # data
            line = srcFile.readline()
            destFile.write(line)
        cnt += 1
        prevSeqNum = SeqNum
        prevSec = currSec

    srcFile.close()
    destFile.close()


def interpolateMOfiles(srcFilePath, destFilePath):
    srcFile = open(srcFilePath, "r")
    mo_la_File = open(destFilePath + "_L_A.csv", "w")
    mo_lg_File = open(destFilePath + "_L_G.csv", "w")
    mo_ra_File = open(destFilePath + "_R_A.csv", "w")
    mo_rg_File = open(destFilePath + "_R_G.csv", "w")
    lineCnt = 0
    unitTime = 0
    la_buf = []
    lg_buf = []
    ra_buf = []
    rg_buf = []
    prevTime = 0
    while True:
        line = srcFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break
        lineCnt += 1
        lineData = [x.strip() for x in line.split(',')]
        if lineCnt == 1:
            firstTime = lineData[2]
            timeData = [x.strip() for x in lineData[2].split(':')]
            unitTime = float(timeData[0]) * 60 + float(timeData[1])
            mo_la_File.write(firstTime + "\n")
            mo_lg_File.write(firstTime + "\n")
            mo_ra_File.write(firstTime + "\n")
            mo_rg_File.write(firstTime + "\n")
            prevTime = unitTime

        timeData = [x.strip() for x in lineData[2].split(':')]
        currTime = float(timeData[0]) * 60 + float(timeData[1])
        if prevTime - currTime > 1:  # hour is changed
            currTime += (60 * 60)
        if currTime - unitTime >= 1:
            if la_buf:  # not empty
                mo_la_File.write(str(np.average(la_buf)) + "\n")
            else:
                mo_la_File.write(str(-10) + "\n")
            if lg_buf:  # not empty
                mo_lg_File.write(str(np.average(lg_buf)) + "\n")
            else:
                mo_lg_File.write(str(-10) + "\n")
            if ra_buf:  # not empty
                mo_ra_File.write(str(np.average(ra_buf)) + "\n")
            else:
                mo_ra_File.write(str(-10) + "\n")
            if rg_buf:  # not empty
                mo_rg_File.write(str(np.average(rg_buf)) + "\n")
            else:
                mo_rg_File.write(str(-10) + "\n")
            la_buf = []
            lg_buf = []
            ra_buf = []
            rg_buf = []
            unitTime += 1
        if lineData[0] == "A" and lineData[1] == "0":
            la_buf.append(np.sqrt(
                float(lineData[3]) * float(lineData[3]) + float(lineData[4]) * float(lineData[4]) + float(
                    lineData[5]) * float(lineData[5])))
        elif lineData[0] == "A" and lineData[1] == "1":
            ra_buf.append(np.sqrt(
                float(lineData[3]) * float(lineData[3]) + float(lineData[4]) * float(lineData[4]) + float(
                    lineData[5]) * float(lineData[5])))
        elif lineData[0] == "G" and lineData[1] == "0":
            lg_buf.append(np.sqrt(
                float(lineData[3]) * float(lineData[3]) + float(lineData[4]) * float(lineData[4]) + float(
                    lineData[5]) * float(lineData[5])))
        elif lineData[0] == "G" and lineData[1] == "1":
            rg_buf.append(np.sqrt(
                float(lineData[3]) * float(lineData[3]) + float(lineData[4]) * float(lineData[4]) + float(
                    lineData[5]) * float(lineData[5])))
        prevTime = currTime

    srcFile.close()
    mo_la_File.close()
    mo_lg_File.close()
    mo_ra_File.close()
    mo_rg_File.close()