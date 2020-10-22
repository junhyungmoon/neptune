##############################################
# Developed by Junhyung Moon (Yonsei Univ.)
# Latest update: 09, Apr, 2019
##############################################

import numpy as np
from biosppy import tools, ecg
from pathlib import Path
import pylab as plt
import glob
import os
from scipy import stats

####################################################################################################################################
### Examine individual NE file whether it has SEQ which is not in increasing order or a group of data which are not 64 instances ###
####################################################################################################################################
def examineNE(inFilePath):
    firstPktNum = 0
    inFile = open(inFilePath, "r")

    prevSeqNum = -1
    cnt = 0
    while True:
        line = inFile.readline()  # ex) SEQ=70332, NE=0, Bia=1, HR=65, NA, 2018-12-10 03:23:57.952
        if not line:
            break
        lineData = [x.strip() for x in line.split(',')]  # ex) ['SEQ=70332', 'NE=0', 'Bia=1', 'HR=65', 'NA', '2018-12-10 03:23:57.952']
        if lineData[0][0].isalpha(): # header
            SeqNum = int(lineData[0].replace("SEQ=", ""))
            if SeqNum <= prevSeqNum:
                print(inFilePath + " has SEQ which is not in increasing order")
                print("It occurs in line " + str(cnt))
                break
            if cnt % 65 != 0:
                print(inFilePath + " has a group of data which are not 64 instances")
                print("It occurs in line " + str(cnt))
                break
        else: # data
            if cnt % 65 == 0:
                print(inFilePath + " has a group of data which are not 64 instances")
                print("It occurs in line " + str(cnt))
                break
        cnt += 1
    inFile.close()
    #print(inFilePath + " has no errors")


##############################################################################################
### Fill dummy data in lost packets within individual NE files while arranging SEQ numbers ###
##############################################################################################
def fillLossNE(inFilePath, outFilePathPre, outFilePathPost):
    firstPktNum = 0
    inFile = open(inFilePath, "r")
    outFile = open(outFilePathPre + outFilePathPost, "w")

    prevSeqNum = -1
    cnt = 0
    while True:
        line = inFile.readline()  # ex) SEQ=70332, NE=0, Bia=1, HR=65, NA, 2018-12-10 03:23:57.952
        if not line:
            break
        lineData = [x.strip() for x in line.split(',')]  # ex) ['SEQ=70332', 'NE=0', 'Bia=1', 'HR=65', 'NA', '2018-12-10 03:23:57.952']
        SeqNum = int(lineData[0].replace("SEQ=", ""))
        if cnt == 0:
            firstPktNum = SeqNum
        if cnt != 0: # except first packet
            # interpolate lost packets
            for k in range(SeqNum - prevSeqNum - 1): # ex) previous seq. 0 ~ current seq. 3: interpolate two packets (1,2)
                # header
                outStr = "SEQ=" + str(prevSeqNum + k + 1)
                for i in range(len(lineData) - 1):  # first one, that is SEQ, was already added to outStr
                    if i == 3:
                        outStr += (", filled")
                    else:
                        outStr += ("," + lineData[i + 1])
                outStr += "\n"
                outFile.write(outStr)
                # data
                for i in range(64):
                    outFile.write("-1000,-1000,-1000\n")
        # current packet
        outFile.write(line)  # header
        for z in range(64):  # data
            line = inFile.readline()
            outFile.write(line)
        cnt += 1
        prevSeqNum = SeqNum

    inFile.close()
    outFile.close()

    #os.rename(outFilePathPre + outFilePathPost, outFilePathPre + "_" + str(firstPktNum) + "_" + str(prevSeqNum) + outFilePathPost)


###########################################################################
### Merge individual NE files into one file while arranging SEQ numbers ###
###########################################################################
def mergeNEFiles(rootPath, inFileList):
    fileCnt = 0
    prevSeqNum = 0
    prevDate = 0
    prevTime = 0
    diff = 0
    outFile = ""
    for inFilePath in inFileList:
        my_file = Path(inFilePath)
        if my_file.is_file():  # if file exists,
            inFile = open(inFilePath, "r")
            if fileCnt == 0: # first file (first hour of total sleep)
                dirData = [x.strip() for x in inFilePath.split('\\')]
                dir5Data = [x.strip() for x in dirData[5].split('_')]
                outFilePath = rootPath + dir5Data[0] + "_NE_filled_merged.csv"
                outFile = open(outFilePath, "w")

                lineCnt = 0
                while True:
                    line = inFile.readline()
                    if not line:
                        break
                    if lineCnt % 65 == 0: #header
                        lineData = [x.strip() for x in line.split(',')]
                        prevSeqNum = int(lineData[0].replace("SEQ=", ""))
                        timeData = [x.strip() for x in lineData[-1].split(' ')]  # yyyy-mm-dd hh:mm:ss.sss
                        dateData = [x.strip() for x in timeData[0].split('-')]  # yyyy mm dd
                        secData = [x.strip() for x in timeData[1].split(':')]  # hh mm ss.sss
                        prevDate = int(dateData[0]) * 10000 + int(dateData[1]) * 100 + int(dateData[2])
                        prevTime = float(secData[0]) * 3600 + float(secData[1]) * 60 + float(secData[2])
                    lineCnt += 1
                    outFile.write(line)
            else: # NOT first file (first hour of total sleep)
                fileSize = int(len(inFile.readlines()))
                inFile.seek(0, 0)
                for k in range(fileSize):
                    line = inFile.readline()
                    if k % 65 == 0: # header
                        lineData = [x.strip() for x in line.split(',')]
                        SeqNum = int(lineData[0].replace("SEQ=", ""))
                        timeData = [x.strip() for x in lineData[-1].split(' ')]  # yyyy-mm-dd hh:mm:ss.sss
                        dateData = [x.strip() for x in timeData[0].split('-')]  # yyyy mm dd
                        secData = [x.strip() for x in timeData[1].split(':')]  # hh mm ss.sss
                        currDate = int(dateData[0]) * 10000 + int(dateData[1]) * 100 + int(dateData[2])
                        currTime = float(secData[0]) * 3600 + float(secData[1]) * 60 + float(secData[2])
                        if prevSeqNum > SeqNum + diff:  # bluetooth re-connection occurred!
                            if currDate - prevDate >= 1:  # date was passed
                                diff = prevSeqNum + int((currTime + 24 * 3600 - prevTime) / 0.25)
                            else:
                                diff = prevSeqNum + int((currTime - prevTime) / 0.25)

                        if diff == 0:
                            outFile.write(line)
                        else:
                            outStr = "SEQ=" + str(diff + SeqNum)
                            for i in range(len(lineData) - 1):  # first one, that is SEQ, was already added to outStr
                                outStr += ("," + lineData[i + 1])
                            outStr += "\n"
                            outFile.write(outStr)
                            # update info. about previous packet with info. about current one
                            prevSeqNum = SeqNum + diff
                            prevTime = currTime
                            prevDate = currDate
                    else:
                        outFile.write(line)

            inFile.close()
            fileCnt += 1
    if outFile:
        outFile.close()


###########################################################################################################################################
### Interpolate data per every second & divide individual MO files into 4 files of 'left acc', 'left gyr', 'right acc', and 'right gyr' ###
###########################################################################################################################################
def interpolateNdivideMoFiles(inFilePath, outFilePath):
    inFile = open(inFilePath, "r")
    mo_la_File = open(outFilePath + "_Mo_la_filled.csv", "w")
    mo_lg_File = open(outFilePath + "_Mo_lg_filled.csv", "w")
    mo_ra_File = open(outFilePath + "_Mo_ra_filled.csv", "w")
    mo_rg_File = open(outFilePath + "_Mo_rg_filled.csv", "w")
    lineCnt = 0
    unitTime = 0
    la_buf = []
    lg_buf = []
    ra_buf = []
    rg_buf = []
    prevTime = 0
    while True:
        line = inFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break
        lineCnt += 1
        lineData = [x.strip() for x in line.split(',')]
        if lineCnt == 1:
            firstTime = lineData[2]
            timeData = [x.strip() for x in lineData[2].split(':')]
            unitTime = float(timeData[0])*60 + float(timeData[1])
            mo_la_File.write(firstTime + "\n")
            mo_lg_File.write(firstTime + "\n")
            mo_ra_File.write(firstTime + "\n")
            mo_rg_File.write(firstTime + "\n")
            prevTime = unitTime

        timeData = [x.strip() for x in lineData[2].split(':')]
        currTime = float(timeData[0]) * 60 + float(timeData[1])
        if prevTime - currTime > 1: # hour is changed
            currTime += (60 * 60)
        if currTime - unitTime >= 1:
            if la_buf: # not empty
                mo_la_File.write(str(np.average(la_buf)) + "\n")
            else:
                mo_la_File.write(str(-10) + "\n")
            if lg_buf: # not empty
                mo_lg_File.write(str(np.average(lg_buf)) + "\n")
            else:
                mo_lg_File.write(str(-10) + "\n")
            if ra_buf: # not empty
                mo_ra_File.write(str(np.average(ra_buf)) + "\n")
            else:
                mo_ra_File.write(str(-10) + "\n")
            if rg_buf: # not empty
                mo_rg_File.write(str(np.average(rg_buf)) + "\n")
            else:
                mo_rg_File.write(str(-10) + "\n")
            la_buf = []
            lg_buf = []
            ra_buf = []
            rg_buf = []
            unitTime += 1
        if lineData[0] == "A" and lineData[1] == "0":
            la_buf.append(np.sqrt(float(lineData[3]) * float(lineData[3]) + float(lineData[4]) * float(lineData[4]) + float(lineData[5]) * float(lineData[5])))
        elif lineData[0] == "A" and lineData[1] == "1":
            ra_buf.append(np.sqrt(float(lineData[3]) * float(lineData[3]) + float(lineData[4]) * float(lineData[4]) + float(lineData[5]) * float(lineData[5])))
        elif lineData[0] == "G" and lineData[1] == "0":
            lg_buf.append(np.sqrt(float(lineData[3]) * float(lineData[3]) + float(lineData[4]) * float(lineData[4]) + float(lineData[5]) * float(lineData[5])))
        elif lineData[0] == "G" and lineData[1] == "1":
            rg_buf.append(np.sqrt(float(lineData[3]) * float(lineData[3]) + float(lineData[4]) * float(lineData[4]) + float(lineData[5]) * float(lineData[5])))
        prevTime = currTime
    mo_la_File.close()
    mo_lg_File.close()
    mo_ra_File.close()
    mo_rg_File.close()


############################################################################
### Fill zeros in lost packets within merged file of individual NE files ###
############################################################################
def mergeMoFiles(rootPath):
    for fileID in ["_Mo_lg_", "_Mo_la_", "_Mo_rg_", "_Mo_ra_"]:
        inFileList = glob.glob(rootPath + "*" + fileID + "*.csv")
        prevTime = 0
        prevDate = 0
        fileCnt = 0
        outFile = ""
        outFilePath = ""
        for inFilePath in inFileList:
            my_file = Path(inFilePath)
            if my_file.is_file():  # if file exists,
                inFile = open(inFilePath, "r")
                dirData = [x.strip() for x in inFilePath.split('\\')]
                dir5Data = [x.strip() for x in dirData[5].split('_')]

                if fileCnt == 0:  # first file (first hour of total sleep)
                    outFilePath = rootPath + dir5Data[0] + fileID + "filled_merged.csv"
                    outFile = open(outFilePath, "w")

                lineCnt = 0
                currDate = 0
                currTime = 0
                while True:
                    line = inFile.readline()  # 라인 by 라인으로 데이터 읽어오기
                    if not line:
                        break
                    if lineCnt == 0:
                        lineData = [x.strip() for x in line.split(':')]
                        currDate = int(dir5Data[0])
                        currFileNameHour = int(int(dir5Data[1])/10000)
                        currTime = float(currFileNameHour * 3600 + int(lineData[0]) * 60 + float(lineData[1]))
                        if fileCnt == 0: # first file (first hour of total sleep)
                            outFile.write(dir5Data[0] + "\t" + str(currFileNameHour) + ":" + line)
                            prevDate = currDate
                            prevTime = currTime

                        if currDate - prevDate >= 1: # date is changed
                            currTime += (24 * 3600)
                        if currTime - prevTime >= 2: # more than 1 second, that is loss
                            for k in range(int(currTime-prevTime-1)):
                                outFile.write(str(-10) + "\n")
                    else:
                        outFile.write(line)
                        if lineCnt > 1: # 파일에 쓰여진 시간 바로 다음의 첫번째 값은 그 시간이지, 그 시간에서 1초 지난 후의 값이 아님
                            currTime += 1
                    lineCnt += 1
                    prevTime = currTime
                fileCnt += 1
        if outFile:
            outFile.close()


#####################
### Scan NE files ###
#####################
def scanNEFiles(rootPath):
    inFilePath = rootPath + "_NE_filled_merged_complete.csv"
    my_file = Path(inFilePath)
    if my_file.is_file():  # if file exists,
        inFile = open(inFilePath, "r")
        lineCnt = 0
        wearCnt = 0
        notWearCnt = 0
        lossPktCnt = 0
        onCnt = 0
        offCnt = 0
        firstSeqNum = 0
        lastSeqNum = 0
        receivedPktCnt = 0
        while True:
            line = inFile.readline()
            if not line:
                break
            lineData = [x.strip() for x in line.split(',')]
            if lineCnt % 65 != 0:  # NOT header
                if 0 < int(lineData[1]) <= 4000:
                    if int(lineData[1]) > 1000:
                        onCnt += 1
                        wearCnt += 1
                    else:
                        offCnt += 1
                elif int(lineData[1]) > 4000:
                    notWearCnt += 1
                    onCnt += 1
            else: # header
                if lineCnt == 0:
                    firstSeqNum = int(lineData[0].replace("SEQ=", ""))
                if lineData[4] == 'filled':
                    lossPktCnt += 1
                else:
                    receivedPktCnt += 1
                lastSeqNum = int(lineData[0].replace("SEQ=", ""))
            lineCnt += 1
        inFile.close()

        h = int(0.25 * (lastSeqNum - firstSeqNum) / 3600)
        m = int(0.25 * (lastSeqNum - firstSeqNum) / 60) - (h * 60)
        s = 0.25 * (lastSeqNum - firstSeqNum) - (h * 3600) - (m * 60)

        outStr = ""
        outStr += str(receivedPktCnt) + "\t" + str(lossPktCnt) + "\t" + str(100*receivedPktCnt/(receivedPktCnt + lossPktCnt)) + "\t" + \
            str(offCnt) + "\t" + str(onCnt) + "\t" + str(100*onCnt/(onCnt + offCnt)) + "\t" + \
            str(wearCnt) + "\t" + str(notWearCnt) + "\t" + str(100*wearCnt/(wearCnt + notWearCnt)) + "\t" + \
            str(firstSeqNum) + "\t" + str(lastSeqNum) + "\t" + \
            str(h) + ":" + str(m) + ":" + str(s) + "\t"

        return outStr



def readyFiles(inFilePath, moLaFilePath, moLgFilePath, moRaFilePath, moRgFilePath, outFilePath):
    inFile = open(inFilePath, "r")
    moLaFile = open(moLaFilePath, "r")
    moLgFile = open(moLgFilePath, "r")
    moRaFile = open(moRaFilePath, "r")
    moRgFile = open(moRgFilePath, "r")
    finalBIAFile = open(outFilePath + "_bia_final.csv", "w") # unit: 1/256 second
    finalBIAFile_ps = open(outFilePath + "_bia_final_persec.csv", "w") # unit: 1 second
    finalECGFile = open(outFilePath + "_ecg_final.csv", "w") # unit: 1/256 second
    finalMOIFile = open(outFilePath + "_moi_final.csv", "w") # unit: 1/256 second
    finalMOIFile_ps = open(outFilePath + "_moi_final_persec.csv", "w") # unit: 1 second
    finalappHRFile = open(outFilePath + "_hr_app_final.csv", "w") # unit: 1/4 second
    finalappHRFile_ps = open(outFilePath + "_hr_app_final_persec.csv", "w") # unit: 1 second
    finalecgHRFile = open(outFilePath + "_hr_ecg_final.csv", "w") # unit: 1 second
    finalmoLaFile = open(outFilePath + "_Mo_la_persec.csv", "w")
    finalmoLgFile = open(outFilePath + "_Mo_lg_persec.csv", "w")
    finalmoRaFile = open(outFilePath + "_Mo_ra_persec.csv", "w")
    finalmoRgFile = open(outFilePath + "_Mo_rg_persec.csv", "w")

    cnt = 0
    bia = []
    moi = []
    hr = []
    tmpbia = []
    tmpmoi = []
    tmphr = []
    moLa = []
    moLg = []
    moRa = []
    moRg = []
    timeFlag = []
    hourFlag = []

    beginTime = 0
    beginDate = 0
    NEFlag = 0
    while True:
        line = inFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            # print(" End Of "+inFile)
            break

        lineData = [x.strip() for x in line.split(',')]
        if cnt % 65 != 0:  # NOT header
            tmpbia.append(int(lineData[1]))
            tmpmoi.append(int(lineData[-1]))
            finalBIAFile.write(lineData[1] + "\n")
            finalECGFile.write(lineData[0] + "\n")
            finalMOIFile.write(lineData[-1] + "\n")
        else:  # headers
            lineData5 = [x.strip() for x in lineData[5].split(' ')]
            dateData = [x.strip() for x in lineData5[0].split('-')]
            timeData = [x.strip() for x in lineData5[1].split(':')]
            if cnt == 0: # first header
                beginTime = float(int(timeData[0]) * 3600 + int(timeData[1]) * 60 + float(timeData[2]))
                beginDate = int(dateData[0]) * 10000 + int(dateData[1]) * 100 + int(dateData[2])
                finalBIAFile.write(str(beginDate) + "\n" + lineData5[1] + "\n")
                finalBIAFile_ps.write(str(beginDate) + "\n" + lineData5[1] + "\n")
                finalECGFile.write(str(beginDate) + "\n" + lineData5[1] + "\n")
                finalMOIFile.write(str(beginDate) + "\n" + lineData5[1] + "\n")
                finalMOIFile_ps.write(str(beginDate) + "\n" + lineData5[1] + "\n")
                finalappHRFile.write(str(beginDate) + "\n" + lineData5[1] + "\n")
                finalappHRFile_ps.write(str(beginDate) + "\n" + lineData5[1] + "\n")
            NEFlag += int(lineData[1].replace("NE=", ""))
            finalBIAFile.write(lineData[1] + "\n")  # "NE="
            finalECGFile.write(lineData[1] + "\n")
            finalMOIFile.write(lineData[1] + "\n")
            finalappHRFile.write(lineData[1] + "\n")
            hrPkt = int(lineData[3].replace("HR=", ""))  #
            tmphr.append(hrPkt) # app HR

        if cnt % 260 == 0 and cnt != 0: # per second
            if NEFlag > 0:
                finalBIAFile_ps.write(str("NE=1") + "\n")
                finalMOIFile_ps.write(str("NE=1") + "\n")
                finalappHRFile_ps.write(str("NE=1") + "\n")
            else:
                finalBIAFile_ps.write(str("NE=0") + "\n")
                finalMOIFile_ps.write(str("NE=0") + "\n")
                finalappHRFile_ps.write(str("NE=0") + "\n")

            finalBIAFile_ps.write(str(np.average(tmpbia)) + "\n")
            finalMOIFile_ps.write(str(np.average(tmpmoi)) + "\n")
            finalappHRFile_ps.write(str(np.average(tmphr)) + "\n")

            tmpbia = []
            tmphr = []
            tmpmoi = []
            NEFlag = 0

        cnt += 1

    finalBIAFile.close()
    finalBIAFile_ps.close()
    finalECGFile.close()
    finalMOIFile.close()
    finalMOIFile_ps.close()
    finalappHRFile.close()
    finalappHRFile_ps.close()

    refFile = open(outFilePath + "_ecg_final.csv", "r")  # unit: 1 second # finalECGFile

    cnt = 0
    freqECG = 256
    ecgBuf = []
    line = refFile.readline()  # Date
    finalecgHRFile.write(line)
    line = refFile.readline()  # Time
    finalecgHRFile.write(line)
    while True:
        line = refFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break

        lineData = [x.strip() for x in line.split(',')]
        if cnt % 65 != 0:  # NOT header
            ecgBuf.append(int(lineData[0]))
        cnt += 1

    resultECG = ecg.ecg(signal=ecgBuf, sampling_rate=freqECG, show=False)
    rawhr_t = resultECG[5]  # seconds
    rawhr = resultECG[6]  #

    for k in range(len(rawhr)):
        finalecgHRFile.write(str(rawhr_t[k]) + "," + str(rawhr[k]) + "\n")

    """ 문제가 좀 있네 코드가...
    tmpHR = []
    sec = 30  # 시작 후 30초부터 연산하려 함(초반이 불안정할 것 같아서 임의로 설정)
    refinedhr = []
    refinedhr_t = []
    for k in range(len(rawhr)):
        if rawhr_t[k] >= sec:
            curHR = np.average(tmpHR)
            diff = int(rawhr_t[k]) - sec
            for y in range(diff-1):
                refinedhr.append(curHR)
                refinedhr_t.append(sec)
                sec += 1
            refinedhr.append(curHR)
            refinedhr_t.append(sec)
            sec += 1  # 1초씩 증가
            tmpHR = []
        tmpHR.append(rawhr[k])
        tmpHR.remove(tmpHR[0]) # moving average
    if tmpHR:
        refinedhr.append(np.average(tmpHR))
        refinedhr_t.append(sec)

    finalhr = []
    finalhr_t = []
    for k in range(sec): # 0 ~ 29 sec
        finalhr.append(refinedhr[0])
        finalhr_t.append(k)
    finalhr = finalhr + refinedhr
    finalhr_t = finalhr_t + refinedhr_t
    """
    refFile.close()
    finalecgHRFile.close()

    ### 2. Read movement data from MO files ###

    line = moLaFile.readline()  # 라인 by 라인으로 데이터 읽어오기
    line = moLgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
    line = moRaFile.readline()  # 라인 by 라인으로 데이터 읽어오기
    line = moRgFile.readline()  # 라인 by 라인으로 데이터 읽어오기

    lineData = [x.strip() for x in line.split('\t')]
    timeData = [x.strip() for x in lineData[1].split(':')]
    beginMOTime = float(int(timeData[0]) * 3600 + int(timeData[1]) * 60 + float(timeData[2]))
    beginMODate = int(lineData[0]) + 20000000

    if beginDate != beginMODate:  # date is changed
        beginMOTime += (24*3600)

    finalmoLaFile.write(str(beginDate) + "\n" + str(beginTime) + "\n")
    finalmoLgFile.write(str(beginDate) + "\n" + str(beginTime) + "\n")
    finalmoRaFile.write(str(beginDate) + "\n" + str(beginTime) + "\n")
    finalmoRgFile.write(str(beginDate) + "\n" + str(beginTime) + "\n")

    diff = int(beginMOTime - beginTime) # 양수이면 메타웨어가 나중에 시작, 음수이면 메타웨어가 먼저 시작
    if diff > 0:
        for z in range(diff):
            finalmoLaFile.write(str(-10) + "\n")
            finalmoLgFile.write(str(-10) + "\n")
            finalmoRaFile.write(str(-10) + "\n")
            finalmoRgFile.write(str(-10) + "\n")
    elif diff < 0:
        for z in range(-diff):
            line = moLaFile.readline()  # 라인 by 라인으로 데이터 읽어오기
            line = moLgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
            line = moRaFile.readline()  # 라인 by 라인으로 데이터 읽어오기
            line = moRgFile.readline()  # 라인 by 라인으로 데이터 읽어오기

    moCnt = 0
    while True:
        line = moLaFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break

        lineData = [x.strip() for x in line.split('\n')]
        finalmoLaFile.write(lineData[0] + "\n")

    while True:
        line = moLgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break

        lineData = [x.strip() for x in line.split('\n')]
        finalmoLgFile.write(lineData[0] + "\n")

    while True:
        line = moRaFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break

        lineData = [x.strip() for x in line.split('\n')]
        finalmoRaFile.write(lineData[0] + "\n")

    while True:
        line = moRgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break

        lineData = [x.strip() for x in line.split('\n')]
        finalmoRgFile.write(lineData[0] + "\n")

    moLaFile.close()
    moLgFile.close()
    moRaFile.close()
    moRgFile.close()

    finalmoLaFile.close()
    finalmoLgFile.close()
    finalmoRaFile.close()
    finalmoRgFile.close()

    inFile.close()





########################################################
### transform data of NE & MO files into image files ###
########################################################
def visualizeAllFiles(rootPath):
    dirData = [x.strip() for x in rootPath.split('\\')]
    expDate = dirData[4]
    inFile = open(rootPath + expDate + "_NE_filled_merged_complete.csv", "r")
    moLaFile = open(rootPath + expDate + "_Mo_la_filled_merged.csv", "r")
    moLgFile = open(rootPath + expDate + "_Mo_lg_filled_merged.csv", "r")
    moRaFile = open(rootPath + expDate + "_Mo_ra_filled_merged.csv", "r")
    moRgFile = open(rootPath + expDate + "_Mo_rg_filled_merged.csv", "r")
    outFilePath = rootPath

    cnt = 0
    bia = []
    moi = []
    hr = []
    tmpbia = []
    tmpmoi = []
    tmphr = []
    moLa = []
    moLg = []
    moRa = []
    moRg = []
    timeFlag = []
    hourFlag = []

    ### 1. Read moisture, BIA, and heart rate from NE file & Store indices of vertical indicators to represent every hour and NE time ###
    fileSize = len(inFile.readlines())
    hourLine = int(fileSize / (65 * 4 * 3600)) + 1
    tickArr = []
    for k in range(hourLine + 1):
        #tickArr.append(k * 64 * 4 * 3600)
        #hourFlag.append(k * 64 * 4 * 3600)
        tickArr.append(k * 3600)
        hourFlag.append(k * 3600)

    inFile.seek(0, 0)
    beginTime = 0
    beginDate = 0
    while True:
        line = inFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            # print(" End Of "+inFile)
            break

        lineData = [x.strip() for x in line.split(',')]
        if cnt % 65 != 0:  # NOT header
            tmpbia.append(int(lineData[1]))
            tmpmoi.append(int(lineData[-1]))
            #bia.append(int(lineData[1]))
            #moi.append(int(lineData[-1]))
        else:  # header
            hrPkt = int(lineData[3].replace("HR=", ""))  #
            tmphr.append(hrPkt)
            #hr.append(hrPkt)

            lineData5 = [x.strip() for x in lineData[5].split(' ')]
            dateData = [x.strip() for x in lineData5[0].split('-')]
            timeData = [x.strip() for x in lineData5[1].split(':')]
            if cnt == 0:
                beginTime = float(int(timeData[0]) * 3600 + int(timeData[1]) * 60 + float(timeData[2]))
                beginDate = int(dateData[0]) * 10000 + int(dateData[1]) * 100 + int(dateData[2])
            else:
                NEFlag = int(lineData[1].replace("NE=", ""))  #
                if NEFlag == 1:
                    NETime = float(int(timeData[0]) * 3600 + int(timeData[1]) * 60 + float(timeData[2]))
                    NEDate = int(dateData[0]) * 10000 + int(dateData[1]) * 100 + int(dateData[2])

                    if beginDate != NEDate:  # date is changed
                        timeFlag.append(int(NETime + 24 * 3600 - beginTime))
                        #timeFlag.append(int(NETime + 24 * 3600 - beginTime) * 64 * 4)
                    else:
                        timeFlag.append(int(NETime - beginTime))
                        #timeFlag.append(int(NETime - beginTime) * 64 * 4)


        if cnt % 260 == 0 and cnt != 0:
            moi.append(np.average(tmpmoi))
            bia.append(np.average(tmpbia))
            hr.append(np.average(tmphr))
            tmpbia = []
            tmphr = []
            tmpmoi = []

        cnt += 1

    """
    windowSize = 5 # unit: second
    finalHr = []
    prevHr = 70
    tmpHr = []
    for j in range(len(hr)):
        if j == 0:
            finalHr.append(hr[j])
            prevHr = 70#hr[j]
        else:
            if abs(prevHr - hr[j]) >= 10:
                if prevHr < hr[j]:
                    finalHr.append(prevHr)
                    #prevHr += 10
                else:
                    finalHr.append(prevHr)
                    #prevHr -= 10
            else:
                finalHr.append(hr[j])
                prevHr = hr[j]
    """

    ### 2. Read movement data from MO files ###

    line = moLaFile.readline()  # 라인 by 라인으로 데이터 읽어오기
    line = moLgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
    line = moRaFile.readline()  # 라인 by 라인으로 데이터 읽어오기
    line = moRgFile.readline()  # 라인 by 라인으로 데이터 읽어오기

    lineData = [x.strip() for x in line.split('\t')]
    timeData = [x.strip() for x in lineData[1].split(':')]
    beginMOTime = float(int(timeData[0]) * 3600 + int(timeData[1]) * 60 + float(timeData[2]))
    beginMODate = int(lineData[0]) + 20000000

    if beginDate != beginMODate:  # date is changed
        beginMOTime += (24*3600)

    diff = int(beginMOTime - beginTime) # 양수이면 메타웨어가 나중에 시작, 음수이면 메타웨어가 먼저 시작
    if diff > 0:
        for z in range(diff):
            moLa.append(-10)
            moLg.append(-10)
            moRa.append(-10)
            moRg.append(-10)
    elif diff < 0:
        for z in range(-diff):
            line = moLaFile.readline()  # 라인 by 라인으로 데이터 읽어오기
            line = moLgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
            line = moRaFile.readline()  # 라인 by 라인으로 데이터 읽어오기
            line = moRgFile.readline()  # 라인 by 라인으로 데이터 읽어오기

    moCnt = 0
    while True:
        line = moLaFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break

        lineData = [x.strip() for x in line.split('\n')]
        moLa.append(float(lineData[0]))

    while True:
        line = moLgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break

        lineData = [x.strip() for x in line.split('\n')]
        moLg.append(float(lineData[0]))

    while True:
        line = moRaFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break

        lineData = [x.strip() for x in line.split('\n')]
        moRa.append(float(lineData[0]))

    while True:
        line = moRgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break

        lineData = [x.strip() for x in line.split('\n')]
        moRg.append(float(lineData[0]))

    moLaFile.close()
    moLgFile.close()
    moRaFile.close()
    moRgFile.close()

    inFile.close()

    ### 3. Transform data into graph and then store graphs as image files ###
    titleSize = 80
    labelSize = 80
    lineWidth = 5

    plotTypeArr = ['dot']#, 'line']
    sensorArr = ['moisture', 'bia', 'bia_zoom', 'bia_zoom_more', 'heartRate', 'left_acc', 'left_gyr', 'right_acc', 'right_gyr']
    for plotType in plotTypeArr:
        for sensor in sensorArr:
            fig = plt.figure(figsize=(70, 30))
            fig.suptitle(sensor, fontsize=titleSize)
            plt.tick_params(labelsize=labelSize)
            xMax = 12000
            xMin = 10800
            if sensor == 'moisture':
                yMin = 6500
                yMax = 9500
                dataArr = moi
            elif sensor == 'bia':
                yMin = -1000
                yMax = 9000
                dataArr = bia
            elif sensor == 'bia_zoom':
                yMin = 1500
                yMax = 3000
                dataArr = bia
            elif sensor == 'bia_zoom_more':
                yMin = 1600
                yMax = 1800
                dataArr = bia
            elif sensor == 'heartRate':
                yMin = 40
                yMax = 200
                dataArr = hr # finalHr
            elif sensor == 'left_acc' or sensor == 'right_acc':
                yMin = -5
                yMax = 5
                if sensor == 'left_acc':
                    dataArr = moLa
                elif sensor == 'right_acc':
                    dataArr = moRa
            elif sensor == 'left_gyr' or sensor == 'right_gyr':
                yMin = -20
                yMax = 100
                if sensor == 'left_gyr':
                    dataArr = moLg
                elif sensor == 'right_gyr':
                    dataArr = moRg

            if timeFlag:
                for k in range(len(timeFlag)):
                    plt.vlines(x=timeFlag[k], ymin=yMin, ymax=yMax, colors='red', linewidth=lineWidth,
                               linestyles='solid', label='NE detected')
            if hourFlag:
                for k in range(len(hourFlag)):
                    plt.vlines(x=hourFlag[k], ymin=yMin, ymax=yMax, colors='blue', linewidth=lineWidth,
                               linestyles='solid', label='NE detected')
            plt.ylim(top=yMax, bottom=yMin)
            #plt.xlim(right=xMax, left=xMin)
            plt.xticks(ticks=tickArr)
            #plt.xticks(ticks=[10800, 11100, 11400, 11700, 12000])
            # plt.plot(moi, color='black', linewidth=3)
            if plotType == 'dot':
                plt.plot(dataArr, 'ko')
            elif plotType == 'line':
                plt.plot(dataArr, color='black', linewidth=3)
            plt.savefig(outFilePath + sensor + '_' + plotType + '.png')
            plt.close(fig)



def visualizeAllFilesV2(inFilePath, outFilePath, biaMin, biaMax, hrMin, hrMax, moiMin, moiMax, movMin, movMax):
    finalBIAFile_ps = open(inFilePath + "_bia_final_persec.csv", "r")  # unit: 1 second
    finalMOIFile = open(inFilePath + "_moi_final.csv", "r")  # unit: 1/256 second
    finalappHRFile_ps = open(inFilePath + "_hr_app_final_persec.csv", "r")  # unit: 1 second
    finalecgHRFile = open(inFilePath + "_hr_ecg_final.csv", "r")  # unit: 1 second
    finalmoLaFile = open(inFilePath + "_Mo_la_persec.csv", "r") # unit: 1 second
    finalmoLgFile = open(inFilePath + "_Mo_lg_persec.csv", "r")
    finalmoRaFile = open(inFilePath + "_Mo_ra_persec.csv", "r")
    finalmoRgFile = open(inFilePath + "_Mo_rg_persec.csv", "r")

    titleSize = 80
    labelSize = 80
    lineWidth = 5

    plotType = 'dot'
    fileSize = len(finalMOIFile.readlines()) - 2  # 1st line is date, and 2nd line is time
    hourLine = int(fileSize / (65 * 4 * 3600)) + 1

    ### 1. Read Moisture (Raw data) and transform it into images ###
    if moiMax > 0 and moiMax > moiMin:
        cnt = 0
        moi = []
        timeFlag = []
        hourFlag = []

        tickArr = []
        for k in range(hourLine + 1):
            tickArr.append(k * 64 * 4 * 3600)
            hourFlag.append(k * 64 * 4 * 3600)

        finalMOIFile.seek(0, 0)
        line = finalMOIFile.readline()  # Date
        line = finalMOIFile.readline()  # Time
        while True:
            line = finalMOIFile.readline()  # 라인 by 라인으로 데이터 읽어오기
            if not line:
                # print(" End Of "+inFile)
                break

            lineData = [x.strip() for x in line.split('\n')]
            if cnt % 65 != 0:  # NOT header
                moi.append(int(lineData[0]))
            else:  # header
                NEFlag = int(lineData[0].replace("NE=", ""))  #
                if NEFlag == 1:
                    timeFlag.append(cnt)
            cnt += 1

        fig = plt.figure(figsize=(70, 30))
        fig.suptitle('Moisture', fontsize=titleSize)
        plt.tick_params(labelsize=labelSize)
        yMin = moiMin
        yMax = moiMax
        dataArr = moi

        if timeFlag:
            for z in range(len(timeFlag)):
                plt.vlines(x=timeFlag[z], ymin=yMin, ymax=yMax, colors='red', linewidth=lineWidth, linestyles='solid', label='NE detected')
        if hourFlag:
            for z in range(len(hourFlag)):
                plt.vlines(x=hourFlag[z], ymin=yMin, ymax=yMax, colors='blue', linewidth=lineWidth, linestyles='solid', label='NE detected')
        plt.ylim(top=yMax, bottom=yMin)
        plt.xticks(ticks=tickArr)
        if plotType == 'dot':
            plt.plot(dataArr, 'ko')
        elif plotType == 'line':
            plt.plot(dataArr, color='black', linewidth=3)
        plt.savefig(outFilePath + 'moisture_' + plotType + '_' + str(moiMax) + '_' + str(moiMin) + '.png')
        plt.close(fig)


    ### 2. Read BIA_persec, App_HR_persec, ECG_HR ###
    # Date
    line = finalBIAFile_ps.readline()
    line = finalappHRFile_ps.readline()
    line = finalecgHRFile.readline()
    line = finalmoLaFile.readline()
    line = finalmoLgFile.readline()
    line = finalmoRaFile.readline()
    line = finalmoRgFile.readline()
    # Time
    line = finalBIAFile_ps.readline()
    line = finalappHRFile_ps.readline()
    line = finalecgHRFile.readline()
    line = finalmoLaFile.readline()
    line = finalmoLgFile.readline()
    line = finalmoRaFile.readline()
    line = finalmoRgFile.readline()

    bia = []
    apphr = []
    timeFlag_persec = []
    hourFlag_persec = []
    tickArr_persec = []
    for k in range(hourLine + 1):
        tickArr_persec.append(k * 3600)
        hourFlag_persec.append(k * 3600)

    cnt = 0
    while True:
        biaLine = finalBIAFile_ps.readline()  # 라인 by 라인으로 데이터 읽어오기
        apphrLine = finalappHRFile_ps.readline()
        if not biaLine:
            break

        biaLineData = [x.strip() for x in biaLine.split('\n')]
        apphrLineData = [x.strip() for x in apphrLine.split('\n')]

        if cnt % 2 == 0: # NE flag
            NEFlag = int(biaLineData[0].replace("NE=", ""))  #
            if NEFlag == 1:
                timeFlag_persec.append(cnt/2)
        else:
            bia.append(float(biaLineData[0]))
            apphr.append(float(apphrLineData[0]))
        cnt += 1

    ecghr = []
    ecghr_t = []
    while True:
        ecgHRLine = finalecgHRFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not ecgHRLine:
            break

        ecgHRLineData = [x.strip() for x in ecgHRLine.split(',')]
        ecghr.append(float(ecgHRLineData[1]))
        ecghr_t.append(float(ecgHRLineData[0]))

    ### Read motion data and transform it into graphs and then store graphs as image files ###
    if movMax > 0 and movMax > movMin:
        moLa = []
        moLg = []
        moRa = []
        moRg = []
        while True:
            moLaLine = finalmoLaFile.readline()
            moLgLine = finalmoLgFile.readline()
            moRaLine = finalmoRaFile.readline()
            moRgLine = finalmoRgFile.readline()
            if not moLaLine:
                break

            moLaLineData = [x.strip() for x in moLaLine.split('\n')]
            moLgLineData = [x.strip() for x in moLgLine.split('\n')]
            moRaLineData = [x.strip() for x in moRaLine.split('\n')]
            moRgLineData = [x.strip() for x in moRgLine.split('\n')]
            moLa.append(float(moLaLineData[0]))
            moLg.append(float(moLgLineData[0]))
            moRa.append(float(moRaLineData[0]))
            moRg.append(float(moRgLineData[0]))

        fig = plt.figure(figsize=(70, 30))
        fig.suptitle('Left gyroscope', fontsize=titleSize)
        plt.tick_params(labelsize=labelSize)
        yMin = movMin
        yMax = movMax
        dataArr = moLg

        if timeFlag_persec:
            for z in range(len(timeFlag_persec)):
                plt.vlines(x=timeFlag_persec[z], ymin=yMin, ymax=yMax, colors='red', linewidth=lineWidth,
                           linestyles='solid', label='NE detected')
        if hourFlag_persec:
            for z in range(len(hourFlag_persec)):
                plt.vlines(x=hourFlag_persec[z], ymin=yMin, ymax=yMax, colors='blue', linewidth=lineWidth,
                           linestyles='solid', label='NE detected')
        plt.ylim(top=yMax, bottom=yMin)
        plt.xticks(ticks=tickArr_persec)
        if plotType == 'dot':
            plt.plot(dataArr, 'ko', markersize=10)
        elif plotType == 'line':
            plt.plot(dataArr, color='black', linewidth=3)
        plt.savefig(outFilePath + 'left_gyr_' + plotType + '_' + str(movMax) + '_' + str(movMin) + '.png')
        plt.close(fig)

        fig = plt.figure(figsize=(70, 30))
        fig.suptitle('Right gyroscope', fontsize=titleSize)
        plt.tick_params(labelsize=labelSize)
        yMin = movMin
        yMax = movMax
        dataArr = moRg
        if timeFlag_persec:
            for z in range(len(timeFlag_persec)):
                plt.vlines(x=timeFlag_persec[z], ymin=yMin, ymax=yMax, colors='red', linewidth=lineWidth,
                           linestyles='solid', label='NE detected')
        if hourFlag_persec:
            for z in range(len(hourFlag_persec)):
                plt.vlines(x=hourFlag_persec[z], ymin=yMin, ymax=yMax, colors='blue', linewidth=lineWidth,
                           linestyles='solid', label='NE detected')
        plt.ylim(top=yMax, bottom=yMin)
        plt.xticks(ticks=tickArr_persec)
        if plotType == 'dot':
            plt.plot(dataArr, 'ko', markersize=10)
        elif plotType == 'line':
            plt.plot(dataArr, color='black', linewidth=3)
        plt.savefig(outFilePath + 'right_gyr_' + plotType + '_' + str(movMax) + '_' + str(movMin) + '.png')
        plt.close(fig)

    ### 3. Transform BIA and HR data into graph and then store graphs as image files ###
    if biaMax > 0 and biaMax > biaMin:
        fig = plt.figure(figsize=(70, 30))
        fig.suptitle('BIA', fontsize=titleSize)
        plt.tick_params(labelsize=labelSize)
        yMin = biaMin
        yMax = biaMax
        dataArr = bia

        if timeFlag_persec:
            for z in range(len(timeFlag_persec)):
                plt.vlines(x=timeFlag_persec[z], ymin=yMin, ymax=yMax, colors='red', linewidth=lineWidth, linestyles='solid', label='NE detected')

        if hourFlag_persec:
            for z in range(len(hourFlag_persec)):
                plt.vlines(x=hourFlag_persec[z], ymin=yMin, ymax=yMax, colors='blue', linewidth=lineWidth, linestyles='solid', label='NE detected')

        plt.ylim(top=yMax, bottom=yMin)
        #plt.xlim(left=10800, right=18000)
        plt.xticks(ticks=tickArr_persec)
        #########################################################
        """
        finalDataArr = []
        tmpArr = []
        prevBIA = -1
        for j in range(59):
            tmpArr.append(2350)
        for j in range(len(dataArr)):
            if 2500 >= dataArr[j] >= 2250:# and abs(dataArr[j] - prevBIA) < 20:
                tmpArr.append(dataArr[j])
                finalDataArr.append(np.average(tmpArr))
                prevBIA = np.average(tmpArr)
                tmpArr.remove(tmpArr[0])
            else:
                if dataArr[j] < 0:
                    finalDataArr.append(dataArr[j])
                else:
                    tmpArr.append(prevBIA)
                    finalDataArr.append(np.average(tmpArr))
                if tmpArr:
                    tmpArr.remove(tmpArr[0])
        """
        #########################################################
        if plotType == 'dot':
            plt.plot(dataArr, 'ko', markersize=10)
        elif plotType == 'line':
            plt.plot(dataArr, color='black', linewidth=3)
        plt.savefig(outFilePath + 'BIA_' + plotType + '_' + str(biaMax) + '_' + str(biaMin) + '.png')
        plt.close(fig)

    if hrMax > 0 and hrMax > hrMin:
        fig = plt.figure(figsize=(70, 30))
        fig.suptitle('HR from NETcher', fontsize=titleSize)
        plt.tick_params(labelsize=labelSize)
        yMin = hrMin
        yMax = hrMax
        dataArr = apphr


        """
        hourFlag_persec = []
        tickArr = []
        for k in range(6):  # 191006
            tickArr.append(k * 3600)
            hourFlag_persec.append(k * 3600)

        """

        if timeFlag_persec:
            for z in range(len(timeFlag_persec)):
                plt.vlines(x=timeFlag_persec[z], ymin=yMin, ymax=yMax, colors='red', linewidth=lineWidth, linestyles='solid', label='NE detected')
        if hourFlag_persec:
            for z in range(len(hourFlag_persec)):
                plt.vlines(x=hourFlag_persec[z], ymin=yMin, ymax=yMax, colors='blue', linewidth=lineWidth, linestyles='solid', label='NE detected')
        plt.ylim(top=yMax, bottom=yMin)
        plt.xticks(ticks=tickArr_persec)
        if plotType == 'dot':
            plt.plot(dataArr, 'ko', markersize=10)
        elif plotType == 'line':
            plt.plot(dataArr, color='black', linewidth=3)
        plt.savefig(outFilePath + 'app_hr_' + plotType + '_' + str(hrMax) + '_' + str(hrMin) + '.png')
        plt.close(fig)

        fig = plt.figure(figsize=(70, 30))
        fig.suptitle('HR from ECG', fontsize=titleSize)
        plt.tick_params(labelsize=labelSize)
        dataArr = ecghr

        if timeFlag_persec:
            for z in range(len(timeFlag_persec)):
                plt.vlines(x=timeFlag_persec[z], ymin=yMin, ymax=yMax, colors='red', linewidth=lineWidth, linestyles='solid', label='NE detected')
        if hourFlag_persec:
            for z in range(len(hourFlag_persec)):
                plt.vlines(x=hourFlag_persec[z], ymin=yMin, ymax=yMax, colors='blue', linewidth=lineWidth, linestyles='solid', label='NE detected')

        plt.ylim(top=yMax, bottom=yMin)
        plt.xticks(ticks=tickArr_persec)
        #########################################################
        """
        finalDataArr = []
        tmpArr = []
        prevHR = 75
        final_t = []
        for j in range(599): # 10 minute smoothing
            tmpArr.append(75) # 191006
        for j in range(len(dataArr)):
            finalDataArr.append(np.average(tmpArr))
            prevHR = np.average(tmpArr)
            tmpArr.remove(tmpArr[0])
            if 60 <= dataArr[j] <= 80:
                tmpArr.append(dataArr[j])
            else:
                tmpArr.append(prevHR)
        """
        #########################################################
        if plotType == 'dot':
            plt.plot(ecghr_t, dataArr, 'ko', markersize=10)
        elif plotType == 'line':
            plt.plot(ecghr_t, dataArr, color='black', linewidth=3)
        if timeFlag_persec:
            for z in range(len(timeFlag_persec)):
                plt.vlines(x=timeFlag_persec[z], ymin=yMin, ymax=yMax, colors='red', linewidth=lineWidth, linestyles='solid', label='NE detected')
        if hourFlag_persec:
            for z in range(len(hourFlag_persec)):
                plt.vlines(x=hourFlag_persec[z], ymin=yMin, ymax=yMax, colors='blue', linewidth=lineWidth, linestyles='solid', label='NE detected')
        plt.savefig(outFilePath + 'ecg_hr_' + plotType + '_' + str(hrMax) + '_' + str(hrMin) + '.png')
        plt.close(fig)



    finalBIAFile_ps.close()
    finalMOIFile.close()
    finalappHRFile_ps.close()
    finalecgHRFile.close()
    finalmoLaFile.close()
    finalmoLgFile.close()
    finalmoRaFile.close()
    finalmoRgFile.close()



def findNE(inFilePath):
    inFile = open(inFilePath, "r")

    while True:
        line = inFile.readline()  # ex) SEQ=70332, NE=0, Bia=1, HR=65, NA, 2018-12-10 03:23:57.952
        if not line:
            break
        lineData = [x.strip() for x in line.split(',')]  # ex) ['SEQ=70332', 'NE=0', 'Bia=1', 'HR=65', 'NA', '2018-12-10 03:23:57.952']
        if lineData[0][0].isalpha(): # header
            if int(lineData[1].replace("NE=", "")) == 1:
                return 1

    inFile.close()
    return 0



def visualizeRawMOIdata(inFilePath, outFilePath, moiMin, moiMax):
    inFile = open(inFilePath, "r")  # unit: 1/256 second

    cnt = 0
    moi = []
    timeFlag = []
    hourFlag = []

    fileSize = len(inFile.readlines()) # 1st line is date, and 2nd line is time
    hourLine = int(fileSize / (65 * 4 * 3600)) + 1
    tickArr = []
    for k in range(hourLine + 1):
        tickArr.append(k * 64 * 4 * 3600)
        hourFlag.append(k * 64 * 4 * 3600)

    inFile.seek(0, 0)
    while True:
        line = inFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            # print(" End Of "+inFile)
            break

        lineData = [x.strip() for x in line.split(',')]
        if cnt % 65 != 0:  # NOT header
            moi.append(int(lineData[2]))
        else:  # header
            NEFlag = int(lineData[1].replace("NE=", ""))  #
            if NEFlag == 1:
                timeFlag.append(cnt)
        cnt += 1

    ### 2. Transform data into graph and then store graphs as image files ###
    titleSize = 80
    labelSize = 80
    lineWidth = 5

    plotType = 'dot'
    if moiMax > 0 and moiMax > moiMin:
        fig = plt.figure(figsize=(70, 30))
        fig.suptitle('Moisture', fontsize=titleSize)
        plt.tick_params(labelsize=labelSize)
        yMin = moiMin
        yMax = moiMax
        dataArr = moi
        if timeFlag:
            for z in range(len(timeFlag)):
                plt.vlines(x=timeFlag[z], ymin=yMin, ymax=yMax, colors='red', linewidth=lineWidth, linestyles='solid', label='NE detected')
        """
        if hourFlag:
            for z in range(len(hourFlag)):
                plt.vlines(x=hourFlag[z], ymin=yMin, ymax=yMax, colors='blue', linewidth=lineWidth, linestyles='solid', label='NE detected')
        """
        plt.ylim(top=yMax, bottom=yMin)
        #plt.xticks(ticks=tickArr)
        if plotType == 'dot':
            plt.plot(dataArr, 'ko')
        elif plotType == 'line':
            plt.plot(dataArr, color='black', linewidth=3)
        plt.savefig(outFilePath + 'raw_moisture_' + plotType + '.png')
        plt.close(fig)

    inFile.close()




def conditionalVisualize(rootPath):
    dirData = [x.strip() for x in rootPath.split('\\')]
    expDate = dirData[4]
    inFile = open(rootPath + expDate + "_NE_filled_merged_complete.csv", "r")  # whole night, 256 data/1 second
    #HRFile = open(rootPath + expDate + "_NE_filled_merged_hr_refined.csv", "r")  # whole night, 1 data/1 second
    #moLgFile = open(rootPath + expDate + "_Mo_lg_filled_merged.csv", "r")  # whole night, 1 data/1 second
    #moRgFile = open(rootPath + expDate + "_Mo_rg_filled_merged.csv", "r")  # whole night, 1 data/1 second
    outFilePath = rootPath
    condMaxBia = 2000
    condMinBia = 1500
    maxTime = 18000-1200
    minTime = 14400-0

    cnt = 0
    bia = []
    tmpbia = []
    moLg = []
    moRg = []
    timeFlag = []
    hourFlag = []

    ### 1. Read moisture, BIA, and heart rate from NE file & Store indices of vertical indicators to represent every hour and NE time ###
    fileSize = len(inFile.readlines())
    hourLine = int(fileSize / (65 * 4 * 3600)) + 1
    tickArr = []
    for k in range(hourLine + 1):
        # tickArr.append(k * 64 * 4 * 3600)
        # hourFlag.append(k * 64 * 4 * 3600)
        tickArr.append(k * 3600)
        hourFlag.append(k * 3600)

    inFile.seek(0, 0)
    beginTime = 0
    beginDate = 0
    prevBIA = condMaxBia
    while True:
        line = inFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            # print(" End Of "+inFile)
            break

        lineData = [x.strip() for x in line.split(',')]
        if cnt % 65 != 0:  # NOT header
            if int(lineData[1]) > condMaxBia or int(lineData[1]) < condMinBia:
                tmpbia.append(prevBIA)
            else:
                tmpbia.append(int(lineData[1]))
                prevBIA = int(lineData[1])
        else:  # header
            lineData5 = [x.strip() for x in lineData[5].split(' ')]
            dateData = [x.strip() for x in lineData5[0].split('-')]
            timeData = [x.strip() for x in lineData5[1].split(':')]
            if cnt == 0:
                beginTime = float(int(timeData[0]) * 3600 + int(timeData[1]) * 60 + float(timeData[2]))
                beginDate = int(dateData[0]) * 10000 + int(dateData[1]) * 100 + int(dateData[2])
            else:
                NEFlag = int(lineData[1].replace("NE=", ""))  #
                if NEFlag == 1:
                    NETime = float(int(timeData[0]) * 3600 + int(timeData[1]) * 60 + float(timeData[2]))
                    NEDate = int(dateData[0]) * 10000 + int(dateData[1]) * 100 + int(dateData[2])

                    if beginDate != NEDate:  # date is changed
                        timeFlag.append(int(NETime + 24 * 3600 - beginTime))
                        # timeFlag.append(int(NETime + 24 * 3600 - beginTime) * 64 * 4)
                    else:
                        timeFlag.append(int(NETime - beginTime))
                        # timeFlag.append(int(NETime - beginTime) * 64 * 4)

        if cnt % 260 == 0 and cnt != 0:
            bia.append(np.average(tmpbia))
            tmpbia = []

        cnt += 1

    slopeBIA = []
    xArrSlope = []
    cnt = 0
    for i in range(len(bia)):
        if minTime <= i <= maxTime:
            slopeBIA.append(bia[i])
            xArrSlope.append(cnt)
            cnt += 1
    s, intercept, r_value, p_value, std_err = stats.linregress(xArrSlope, slopeBIA)
    print(slopeBIA[0])
    print(np.max(slopeBIA))
    print(slopeBIA[-1])
    print(np.min(slopeBIA))
    print(s)

    ### 2. Read HR data
    """
    hr = []
    prevHR = 100
    while True:
        line = HRFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            # print(" End Of "+inFile)
            break

        lineData = [x.strip() for x in line.split(',')]  # second, HR value
        if float(lineData[1]) > 160 or float(lineData[1]) < 40:
            hr.append(prevHR)
        else:
            hr.append(float(lineData[1]))
            prevHR = float(lineData[1])

    ### 3. Read movement data from MO files ###

    line = moLgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
    line = moRgFile.readline()  # 라인 by 라인으로 데이터 읽어오기

    lineData = [x.strip() for x in line.split('\t')]
    timeData = [x.strip() for x in lineData[1].split(':')]
    beginMOTime = float(int(timeData[0]) * 3600 + int(timeData[1]) * 60 + float(timeData[2]))
    beginMODate = int(lineData[0]) + 20000000

    if beginDate != beginMODate:  # date is changed
        beginMOTime += (24 * 3600)

    diff = int(beginMOTime - beginTime)  # 양수이면 메타웨어가 나중에 시작, 음수이면 메타웨어가 먼저 시작
    if diff > 0:
        for z in range(diff):
            moLg.append(-10)
            moRg.append(-10)
    elif diff < 0:
        for z in range(-diff):
            line = moLgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
            line = moRgFile.readline()  # 라인 by 라인으로 데이터 읽어오기

    while True:
        line = moLgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break

        lineData = [x.strip() for x in line.split('\n')]
        moLg.append(float(lineData[0]))

    while True:
        line = moRgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break

        lineData = [x.strip() for x in line.split('\n')]
        moRg.append(float(lineData[0]))

    moLgFile.close()
    moRgFile.close()
    inFile.close()
    HRFile.close()
    """
    ### 5. Transform data into graph and then store graphs as image files ###
    titleSize = 80
    labelSize = 80
    lineWidth = 5

    plotTypeArr = ['dot']  # , 'line']
    sensorArr = ['interpolate_bia'] # , 'interpolate_hr', 'interpolate_left_gyr', 'interpolate_right_gyr'
    for plotType in plotTypeArr:
        for sensor in sensorArr:
            fig = plt.figure(figsize=(70, 30))
            fig.suptitle(sensor, fontsize=titleSize)
            plt.tick_params(labelsize=labelSize)
            if sensor == 'interpolate_bia':
                yMin = condMinBia
                yMax = condMaxBia
                dataArr = bia
            elif sensor == 'interpolate_hr':
                yMin = 40
                yMax = 160
                #dataArr = hr  # finalHr
            elif sensor == 'interpolate_left_gyr' or sensor == 'interpolate_right_gyr':
                yMin = -20
                yMax = 100
                if sensor == 'interpolate_left_gyr':
                    dataArr = moLg
                elif sensor == 'interpolate_right_gyr':
                    dataArr = moRg

            if timeFlag:
                for k in range(len(timeFlag)):
                    plt.vlines(x=timeFlag[k], ymin=yMin, ymax=yMax, colors='red', linewidth=lineWidth,
                               linestyles='solid', label='NE detected')
            if hourFlag:
                for k in range(len(hourFlag)):
                    plt.vlines(x=hourFlag[k], ymin=yMin, ymax=yMax, colors='blue', linewidth=lineWidth,
                               linestyles='solid', label='every hour')
            plt.ylim(top=yMax, bottom=yMin)
            # plt.xlim(right=xMax, left=xMin)
            plt.xticks(ticks=tickArr)
            # plt.xticks(ticks=[10800, 11100, 11400, 11700, 12000])
            # plt.plot(moi, color='black', linewidth=3)
            if plotType == 'dot':
                plt.plot(dataArr, 'ko')
            elif plotType == 'line':
                plt.plot(dataArr, color='black', linewidth=3)
            plt.savefig(outFilePath + sensor + '_' + plotType + '.png')
            plt.close(fig)


def plotBIADerivatives(rootPath):
    dirData = [x.strip() for x in rootPath.split('\\')]
    expDate = dirData[4]
    inFile = open(rootPath + expDate + "_NE_filled_merged_complete.csv", "r")  # whole night, 256 data/1 second
    outFilePath = rootPath
    condMaxBia = 2200
    condMinBia = 1800
    maxTime = 3600+600
    minTime = 3600-600

    cnt = 0
    bia = []
    tmpbia = []
    moLg = []
    moRg = []
    timeFlag = []
    hourFlag = []

    ### 1. Read moisture, BIA, and heart rate from NE file & Store indices of vertical indicators to represent every hour and NE time ###
    fileSize = len(inFile.readlines())
    hourLine = int(fileSize / (65 * 4 * 3600)) + 1
    tickArr = []
    for k in range(hourLine + 1):
        # tickArr.append(k * 64 * 4 * 3600)
        # hourFlag.append(k * 64 * 4 * 3600)
        tickArr.append(k * 3600)
        hourFlag.append(k * 3600)

    inFile.seek(0, 0)
    beginTime = 0
    beginDate = 0
    prevBIA = condMaxBia
    while True:
        line = inFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            # print(" End Of "+inFile)
            break

        lineData = [x.strip() for x in line.split(',')]
        if cnt % 65 != 0:  # NOT header
            if int(lineData[1]) > condMaxBia or int(lineData[1]) < condMinBia:
                tmpbia.append(prevBIA)
            else:
                tmpbia.append(int(lineData[1]))
                prevBIA = int(lineData[1])
        else:  # header
            lineData5 = [x.strip() for x in lineData[5].split(' ')]
            dateData = [x.strip() for x in lineData5[0].split('-')]
            timeData = [x.strip() for x in lineData5[1].split(':')]
            if cnt == 0:
                beginTime = float(int(timeData[0]) * 3600 + int(timeData[1]) * 60 + float(timeData[2]))
                beginDate = int(dateData[0]) * 10000 + int(dateData[1]) * 100 + int(dateData[2])
            else:
                NEFlag = int(lineData[1].replace("NE=", ""))  #
                if NEFlag == 1:
                    NETime = float(int(timeData[0]) * 3600 + int(timeData[1]) * 60 + float(timeData[2]))
                    NEDate = int(dateData[0]) * 10000 + int(dateData[1]) * 100 + int(dateData[2])

                    if beginDate != NEDate:  # date is changed
                        timeFlag.append(int(NETime + 24 * 3600 - beginTime))
                        # timeFlag.append(int(NETime + 24 * 3600 - beginTime) * 64 * 4)
                    else:
                        timeFlag.append(int(NETime - beginTime))
                        # timeFlag.append(int(NETime - beginTime) * 64 * 4)

        if cnt % 260 == 0 and cnt != 0:
            bia.append(np.average(tmpbia))
            tmpbia = []

        cnt += 1

    xArrSlope = []
    for z in range(30):
        xArrSlope.append(z)

    slopeBIA = []
    slopeBIA30sec = []
    for z in range(30):
        slopeBIA.append()
    for i in range(30, len(bia)):
        slopeBIA30sec.append(bia[i])
        if i % 30 == 29:
            s, intercept, r_value, p_value, std_err = stats.linregress(xArrSlope, slopeBIA30sec)
            slopeBIA.append(s)
            slopeBIA30sec.remove(slopeBIA30sec[0])

    inFile.close()

    ### 5. Transform data into graph and then store graphs as image files ###
    titleSize = 80
    labelSize = 80
    lineWidth = 5

    plotTypeArr = ['dot']  # , 'line']
    sensorArr = ['derivative_bia']
    for plotType in plotTypeArr:
        for sensor in sensorArr:
            fig = plt.figure(figsize=(70, 30))
            fig.suptitle(sensor, fontsize=titleSize)
            plt.tick_params(labelsize=labelSize)
            if sensor == 'derivative_bia':
                yMin = condMinBia
                yMax = condMaxBia
                dataArr = bia

            if timeFlag:
                for k in range(len(timeFlag)):
                    plt.vlines(x=timeFlag[k], ymin=yMin, ymax=yMax, colors='red', linewidth=lineWidth,
                               linestyles='solid', label='NE detected')
            if hourFlag:
                for k in range(len(hourFlag)):
                    plt.vlines(x=hourFlag[k], ymin=yMin, ymax=yMax, colors='blue', linewidth=lineWidth,
                               linestyles='solid', label='every hour')
            plt.ylim(top=yMax, bottom=yMin)
            # plt.xlim(right=xMax, left=xMin)
            plt.xticks(ticks=tickArr)
            # plt.xticks(ticks=[10800, 11100, 11400, 11700, 12000])
            # plt.plot(moi, color='black', linewidth=3)
            if plotType == 'dot':
                plt.plot(dataArr, 'ko')
            elif plotType == 'line':
                plt.plot(dataArr, color='black', linewidth=3)
            plt.savefig(outFilePath + sensor + '_' + plotType + '.png')
            plt.close(fig)


def predictNE(rootPath):
    dirData = [x.strip() for x in rootPath.split('\\')]
    expDate = dirData[4]
    inFile = open(rootPath + expDate + "_NE_filled_merged_complete.csv", "r")
    HRFile = open(rootPath + expDate + "_hr_ecg_final.csv", "r")
    moLgFile = open(rootPath + expDate + "_Mo_lg_filled_merged.csv", "r")
    moRgFile = open(rootPath + expDate + "_Mo_rg_filled_merged.csv", "r")
    outFilePath = rootPath

    cnt = 0
    bia = []
    wholeBia = []
    tmpbia = []
    moLg = []
    moRg = []
    timeFlag = []
    hourFlag = []

    ### 1. Read moisture, BIA, and heart rate from NE file & Store indices of vertical indicators to represent every hour and NE time ###
    fileSize = len(inFile.readlines())
    hourLine = int(fileSize / (65 * 4 * 3600)) + 1
    tickArr = []
    for k in range(hourLine + 1):
        # tickArr.append(k * 64 * 4 * 3600)
        # hourFlag.append(k * 64 * 4 * 3600)
        tickArr.append(k * 3600)
        hourFlag.append(k * 3600)

    inFile.seek(0, 0)
    beginTime = 0
    beginDate = 0
    while True:
        line = inFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            # print(" End Of "+inFile)
            break

        lineData = [x.strip() for x in line.split(',')]
        if cnt % 65 != 0:  # NOT header
            wholeBia.append(float(lineData[1]))
        else: # header
            lineData5 = [x.strip() for x in lineData[5].split(' ')]
            dateData = [x.strip() for x in lineData5[0].split('-')]
            timeData = [x.strip() for x in lineData5[1].split(':')]
            if cnt == 0:
                beginTime = float(int(timeData[0]) * 3600 + int(timeData[1]) * 60 + float(timeData[2]))
                beginDate = int(dateData[0]) * 10000 + int(dateData[1]) * 100 + int(dateData[2])
            else:
                NEFlag = int(lineData[1].replace("NE=", ""))  #
                if NEFlag == 1:
                    NETime = float(int(timeData[0]) * 3600 + int(timeData[1]) * 60 + float(timeData[2]))
                    NEDate = int(dateData[0]) * 10000 + int(dateData[1]) * 100 + int(dateData[2])

                    if beginDate != NEDate:  # date is changed
                        timeFlag.append(int(NETime + 24 * 3600 - beginTime))
                        # timeFlag.append(int(NETime + 24 * 3600 - beginTime) * 64 * 4)
                    else:
                        timeFlag.append(int(NETime - beginTime))
                        # timeFlag.append(int(NETime - beginTime) * 64 * 4)

        cnt += 1

    # Aggregation
    aggregateSize = 64 * 4  # unit: BIA value
    tmpBia = []
    prevBIA = 2350
    aggregateBia = []  # unit: aggregateSize
    for z in range(len(wholeBia)):
        if z != 0 and z % aggregateSize == 0:
            if tmpBia:
                aggregateBia.append(np.average(tmpBia))
                prevBIA = np.average(tmpBia)
            else:
                aggregateBia.append(prevBIA)
            tmpBia = []
        if 2280 <= wholeBia[z] <= 2360:
            tmpBia.append(wholeBia[z])
        else:
            tmpBia.append(prevBIA)

    # Aggregation (위에서 초당 BIA 데이터로 변환 완료)
    prevBIA = aggregateBia[0]
    interpolateBia = []  # unit: aggregateSize
    interpolateBia.append(prevBIA)
    for z in range(1, len(aggregateBia)):
        diff = aggregateBia[z] - aggregateBia[z - 1]
        if - 10 < diff < 10:
            interpolateBia.append(interpolateBia[z - 1] + diff)
            prevBIA = interpolateBia[z - 1] + diff
        else:
            interpolateBia.append(prevBIA)

    # Aggregation (위에서 상엽이 방법 적용 완료)
    tmpBia = []
    prevBIA = interpolateBia[0]
    interpolateBia2 = []  # unit: aggregateSize
    interpolateBia2.append(prevBIA)
    interpolateSize = 10  # seconds
    for z in range(0, 3600 * 5):  # len(interpolateBia)
        if z > interpolateSize:
            if tmpBia:
                interpolateBia2.append(np.average(tmpBia))
                prevBIA = np.average(tmpBia)
            else:
                interpolateBia2.append(prevBIA)
            tmpBia.remove(tmpBia[0])
        if 1800 <= interpolateBia[z] <= 2400:
            tmpBia.append(interpolateBia[z])
        else:
            tmpBia.append(prevBIA)


    ### 2. Read HR data
    hr = []
    line = HRFile.readline()  # 라인 by 라인으로 데이터 읽어오기
    line = HRFile.readline()  # 라인 by 라인으로 데이터 읽어오기
    minute = 0
    minuteHR = 0
    cnt = 0
    while True:
        line = HRFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            # print(" End Of "+inFile)
            break

        lineData = [x.strip() for x in line.split(',')] # second, HR value
        hr.append(float(lineData[1]))


    ### 3. Read movement data from MO files ###

    line = moLgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
    line = moRgFile.readline()  # 라인 by 라인으로 데이터 읽어오기

    lineData = [x.strip() for x in line.split('\t')]
    timeData = [x.strip() for x in lineData[1].split(':')]
    beginMOTime = float(int(timeData[0]) * 3600 + int(timeData[1]) * 60 + float(timeData[2]))
    beginMODate = int(lineData[0]) + 20000000

    if beginDate != beginMODate:  # date is changed
        beginMOTime += (24 * 3600)

    diff = int(beginMOTime - beginTime)  # 양수이면 메타웨어가 나중에 시작, 음수이면 메타웨어가 먼저 시작
    if diff > 0:
        for z in range(diff):
            moLg.append(-10)
            moRg.append(-10)
    elif diff < 0:
        for z in range(-diff):
            line = moLgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
            line = moRgFile.readline()  # 라인 by 라인으로 데이터 읽어오기

    while True:
        line = moLgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break

        lineData = [x.strip() for x in line.split('\n')]
        moLg.append(float(lineData[0]))

    while True:
        line = moRgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break

        lineData = [x.strip() for x in line.split('\n')]
        moRg.append(float(lineData[0]))

    moLgFile.close()
    moRgFile.close()
    inFile.close()
    HRFile.close()

    ### 4. Rule-based NE prediction
    loopLen = np.min([len(interpolateBia2), len(hr), len(moLg), len(moRg)])
    #print(str(beginTime) + "\t" + str(beginMOTime) + "\t" + str(len(bia)) + "\t" + str(len(hr)) + "\t" + str(len(moLg)) + "\t" + str(len(moRg)))
    predictLine = []
    biaAlarmFlag = 0
    hrAlarmFlag = 0
    leftAlarmFlag = []
    rightAlarmFlag = []
    hrWindow = []
    hr_x = []

    for j in range(0, 1800):
        hr_x.append(j)

    for t in range(3600, loopLen): # unit: second, skip 1st hour
        if t >= 1800 + 3600: # 심박수 3분
            s, intercept, r_value, p_value, std_err = stats.linregress(hr_x, hrWindow)
            if s > 0:
                hrAlarmFlag = 1
            else:
                hrAlarmFlag = 0
            hrWindow.remove(hrWindow[0])

        if t >= 600 + 3600:  # 움직임 10분
            if biaAlarmFlag > 100 and (np.average(leftAlarmFlag) > 0 or np.average(rightAlarmFlag) > 0) and hrAlarmFlag == 1:
                predictLine.append(t)

            leftAlarmFlag.remove(leftAlarmFlag[0])
            rightAlarmFlag.remove(rightAlarmFlag[0])
            hrAlarmFlag = 0

        if 1800 <= interpolateBia2[t] <= 2400: # 임피던스 영역대
            biaAlarmFlag += 1
        if moLg[t] > 5:
            leftAlarmFlag.append(1)
        else:
            leftAlarmFlag.append(0)
        if moRg[t] > 5:
            rightAlarmFlag.append(1)
        else:
            rightAlarmFlag.append(0)
        hrWindow.append(hr[t])





    ### 5. Transform data into graph and then store graphs as image files ###
    titleSize = 80
    labelSize = 80
    lineWidth = 5

    plotTypeArr = ['dot']  # , 'line']
    sensorArr = ['predictNE_bia']#, 'predictNE_hr', 'predictNE_left_gyr', 'predictNE_right_gyr']
    for plotType in plotTypeArr:
        for sensor in sensorArr:
            fig = plt.figure(figsize=(70, 30))
            fig.suptitle(sensor, fontsize=titleSize)
            plt.tick_params(labelsize=labelSize)
            if sensor == 'predictNE_bia':
                yMin = np.min(interpolateBia2)
                yMax = np.max(interpolateBia2)
                dataArr = interpolateBia2
            elif sensor == 'predictNE_hr':
                yMin = 60
                yMax = 90
                dataArr = hr  # finalHr
            elif sensor == 'predictNE_left_gyr' or sensor == 'predictNE_right_gyr':
                yMin = -20
                yMax = 100
                if sensor == 'predictNE_left_gyr':
                    dataArr = moLg
                elif sensor == 'predictNE_right_gyr':
                    dataArr = moRg

            if timeFlag:
                for k in range(1,2):#len(timeFlag)):
                    plt.vlines(x=timeFlag[k], ymin=yMin, ymax=yMax, colors='red', linewidth=lineWidth,
                               linestyles='solid', label='NE detected')

            if hourFlag:
                for k in range(0,6):#len(hourFlag)):
                    plt.vlines(x=hourFlag[k], ymin=yMin, ymax=yMax, colors='blue', linewidth=lineWidth,
                               linestyles='solid', label='every hour')
            if predictLine:
                for k in range(len(predictLine)):
                    plt.vlines(x=predictLine[k], ymin=yMin, ymax=yMax, colors='green', linewidth=lineWidth,
                               linestyles='solid', label='NE predicted')
            plt.ylim(top=yMax, bottom=yMin)
            # plt.xlim(right=xMax, left=xMin)
            plt.xticks(ticks=tickArr)
            # plt.xticks(ticks=[10800, 11100, 11400, 11700, 12000])
            # plt.plot(moi, color='black', linewidth=3)
            if plotType == 'dot':
                if sensor == 'predictNE_bia':
                    plt.plot(dataArr, 'ko', markersize=10)
                else:
                    plt.plot(dataArr, 'ko', markersize=10)
            elif plotType == 'line':
                plt.plot(dataArr, color='black', linewidth=3)
            plt.savefig(outFilePath + sensor + '_' + plotType + '.png')
            plt.close(fig)


def interpolateGraphs(rootPath):
    dirData = [x.strip() for x in rootPath.split('\\')]
    expDate = dirData[4]
    inFile = open(rootPath + expDate + "_NE_filled_merged_complete.csv", "r") # whole night, 256 data/1 second
    HRFile = open(rootPath + expDate + "_NE_filled_merged_hr_refined.csv", "r") # whole night, 1 data/1 second
    moLgFile = open(rootPath + expDate + "_Mo_lg_filled_merged.csv", "r") # whole night, 1 data/1 second
    moRgFile = open(rootPath + expDate + "_Mo_rg_filled_merged.csv", "r") # whole night, 1 data/1 second
    outFilePath = rootPath

    cnt = 0
    bia = []
    tmpbia = []
    moLg = []
    moRg = []
    timeFlag = []
    hourFlag = []

    ### 1. Read moisture, BIA, and heart rate from NE file & Store indices of vertical indicators to represent every hour and NE time ###
    fileSize = len(inFile.readlines())
    hourLine = int(fileSize / (65 * 4 * 3600)) + 1
    tickArr = []
    for k in range(hourLine + 1):
        # tickArr.append(k * 64 * 4 * 3600)
        # hourFlag.append(k * 64 * 4 * 3600)
        tickArr.append(k * 3600)
        hourFlag.append(k * 3600)

    inFile.seek(0, 0)
    beginTime = 0
    beginDate = 0
    prevBIA = 3000
    while True:
        line = inFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            # print(" End Of "+inFile)
            break

        lineData = [x.strip() for x in line.split(',')]
        if cnt % 65 != 0:  # NOT header
            if int(lineData[1]) > 3000 or int(lineData[1]) < 1500:
                tmpbia.append(prevBIA)
            else:
                tmpbia.append(int(lineData[1]))
                prevBIA = int(lineData[1])
        else: # header
            lineData5 = [x.strip() for x in lineData[5].split(' ')]
            dateData = [x.strip() for x in lineData5[0].split('-')]
            timeData = [x.strip() for x in lineData5[1].split(':')]
            if cnt == 0:
                beginTime = float(int(timeData[0]) * 3600 + int(timeData[1]) * 60 + float(timeData[2]))
                beginDate = int(dateData[0]) * 10000 + int(dateData[1]) * 100 + int(dateData[2])
            else:
                NEFlag = int(lineData[1].replace("NE=", ""))  #
                if NEFlag == 1:
                    NETime = float(int(timeData[0]) * 3600 + int(timeData[1]) * 60 + float(timeData[2]))
                    NEDate = int(dateData[0]) * 10000 + int(dateData[1]) * 100 + int(dateData[2])

                    if beginDate != NEDate:  # date is changed
                        timeFlag.append(int(NETime + 24 * 3600 - beginTime))
                        # timeFlag.append(int(NETime + 24 * 3600 - beginTime) * 64 * 4)
                    else:
                        timeFlag.append(int(NETime - beginTime))
                        # timeFlag.append(int(NETime - beginTime) * 64 * 4)

        if cnt % 260 == 0 and cnt != 0:
            bia.append(np.average(tmpbia))
            tmpbia = []

        cnt += 1



    ### 2. Read HR data
    hr = []
    prevHR = 100
    while True:
        line = HRFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            # print(" End Of "+inFile)
            break

        lineData = [x.strip() for x in line.split(',')] # second, HR value
        if float(lineData[1]) > 160 or float(lineData[1]) < 40:
            hr.append(prevHR)
        else:
            hr.append(float(lineData[1]))
            prevHR = float(lineData[1])


    ### 3. Read movement data from MO files ###

    line = moLgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
    line = moRgFile.readline()  # 라인 by 라인으로 데이터 읽어오기

    lineData = [x.strip() for x in line.split('\t')]
    timeData = [x.strip() for x in lineData[1].split(':')]
    beginMOTime = float(int(timeData[0]) * 3600 + int(timeData[1]) * 60 + float(timeData[2]))
    beginMODate = int(lineData[0]) + 20000000

    if beginDate != beginMODate:  # date is changed
        beginMOTime += (24 * 3600)

    diff = int(beginMOTime - beginTime)  # 양수이면 메타웨어가 나중에 시작, 음수이면 메타웨어가 먼저 시작
    if diff > 0:
        for z in range(diff):
            moLg.append(-10)
            moRg.append(-10)
    elif diff < 0:
        for z in range(-diff):
            line = moLgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
            line = moRgFile.readline()  # 라인 by 라인으로 데이터 읽어오기

    while True:
        line = moLgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break

        lineData = [x.strip() for x in line.split('\n')]
        moLg.append(float(lineData[0]))

    while True:
        line = moRgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break

        lineData = [x.strip() for x in line.split('\n')]
        moRg.append(float(lineData[0]))

    moLgFile.close()
    moRgFile.close()
    inFile.close()
    HRFile.close()

    ### 5. Transform data into graph and then store graphs as image files ###
    titleSize = 80
    labelSize = 80
    lineWidth = 5

    plotTypeArr = ['dot']  # , 'line']
    sensorArr = ['interpolate_bia', 'interpolate_hr', 'interpolate_left_gyr', 'interpolate_right_gyr']
    for plotType in plotTypeArr:
        for sensor in sensorArr:
            fig = plt.figure(figsize=(70, 30))
            fig.suptitle(sensor, fontsize=titleSize)
            plt.tick_params(labelsize=labelSize)
            if sensor == 'interpolate_bia':
                yMin = 1500
                yMax = 3000
                dataArr = bia
            elif sensor == 'interpolate_hr':
                yMin = 40
                yMax = 160
                dataArr = hr  # finalHr
            elif sensor == 'interpolate_left_gyr' or sensor == 'interpolate_right_gyr':
                yMin = -20
                yMax = 100
                if sensor == 'interpolate_left_gyr':
                    dataArr = moLg
                elif sensor == 'interpolate_right_gyr':
                    dataArr = moRg

            if timeFlag:
                for k in range(len(timeFlag)):
                    plt.vlines(x=timeFlag[k], ymin=yMin, ymax=yMax, colors='red', linewidth=lineWidth,
                               linestyles='solid', label='NE detected')
            if hourFlag:
                for k in range(len(hourFlag)):
                    plt.vlines(x=hourFlag[k], ymin=yMin, ymax=yMax, colors='blue', linewidth=lineWidth,
                               linestyles='solid', label='every hour')
            plt.ylim(top=yMax, bottom=yMin)
            # plt.xlim(right=xMax, left=xMin)
            plt.xticks(ticks=tickArr)
            # plt.xticks(ticks=[10800, 11100, 11400, 11700, 12000])
            # plt.plot(moi, color='black', linewidth=3)
            if plotType == 'dot':
                plt.plot(dataArr, 'ko', markersize=10)
            elif plotType == 'line':
                plt.plot(dataArr, color='black', linewidth=3)
            plt.savefig(outFilePath + sensor + '_' + plotType + '.png')
            plt.close(fig)


def parseNearNE(rootPath, alarmOrder):
    dirData = [x.strip() for x in rootPath.split('\\')]
    expDate = dirData[4]
    inFile = open(rootPath + expDate + "_NE_filled_merged_complete.csv", "r")
    HRFile = open(rootPath + expDate + "_NE_filled_merged_hr_refined.csv", "r")
    moLgFile = open(rootPath + expDate + "_Mo_lg_filled_merged.csv", "r")
    moRgFile = open(rootPath + expDate + "_Mo_rg_filled_merged.csv", "r")
    outFilePath = rootPath

    cnt = 0
    bia = []
    tmpbia = []
    moLg = []
    moRg = []
    timeFlag = []
    hourFlag = []

    ### 1. Read moisture, BIA, and heart rate from NE file & Store indices of vertical indicators to represent every hour and NE time ###
    fileSize = len(inFile.readlines())
    """
    hourLine = int(fileSize / (65 * 4 * 3600)) + 1
    tickArr = []
    for k in range(hourLine + 1):
        tickArr.append(k * 3600)
        hourFlag.append(k * 3600)
    """
    inFile.seek(0, 0)
    beginTime = 0
    beginDate = 0
    while True:
        line = inFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            # print(" End Of "+inFile)
            break

        lineData = [x.strip() for x in line.split(',')]
        if cnt % 65 != 0:  # NOT header
            tmpbia.append(int(lineData[1]))
        else: # header
            lineData5 = [x.strip() for x in lineData[5].split(' ')]
            dateData = [x.strip() for x in lineData5[0].split('-')]
            timeData = [x.strip() for x in lineData5[1].split(':')]
            if cnt == 0:
                beginTime = float(int(timeData[0]) * 3600 + int(timeData[1]) * 60 + float(timeData[2]))
                beginDate = int(dateData[0]) * 10000 + int(dateData[1]) * 100 + int(dateData[2])
            else:
                NEFlag = int(lineData[1].replace("NE=", ""))  #
                if NEFlag == 1:
                    NETime = float(int(timeData[0]) * 3600 + int(timeData[1]) * 60 + float(timeData[2]))
                    NEDate = int(dateData[0]) * 10000 + int(dateData[1]) * 100 + int(dateData[2])

                    if beginDate != NEDate:  # date is changed
                        timeFlag.append(int(NETime + 24 * 3600 - beginTime))
                    else:
                        timeFlag.append(int(NETime - beginTime))

        if cnt % 260 == 0 and cnt != 0:
            bia.append(np.average(tmpbia))
            tmpbia = []

        cnt += 1

    ### 2. Read HR data
    hr = []
    while True:
        line = HRFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            # print(" End Of "+inFile)
            break

        lineData = [x.strip() for x in line.split(',')] # second, HR value
        hr.append(float(lineData[1]))


    ### 3. Read movement data from MO files ###

    line = moLgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
    line = moRgFile.readline()  # 라인 by 라인으로 데이터 읽어오기

    lineData = [x.strip() for x in line.split('\t')]
    timeData = [x.strip() for x in lineData[1].split(':')]
    beginMOTime = float(int(timeData[0]) * 3600 + int(timeData[1]) * 60 + float(timeData[2]))
    beginMODate = int(lineData[0]) + 20000000

    if beginDate != beginMODate:  # date is changed
        beginMOTime += (24 * 3600)

    diff = int(beginMOTime - beginTime)  # 양수이면 메타웨어가 나중에 시작, 음수이면 메타웨어가 먼저 시작
    if diff > 0:
        for z in range(diff):
            moLg.append(-10)
            moRg.append(-10)
    elif diff < 0:
        for z in range(-diff):
            line = moLgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
            line = moRgFile.readline()  # 라인 by 라인으로 데이터 읽어오기

    while True:
        line = moLgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break

        lineData = [x.strip() for x in line.split('\n')]
        moLg.append(float(lineData[0]))

    while True:
        line = moRgFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break

        lineData = [x.strip() for x in line.split('\n')]
        moRg.append(float(lineData[0]))

    moLgFile.close()
    moRgFile.close()
    inFile.close()
    HRFile.close()

    loopLen = np.min([len(bia), len(hr), len(moLg), len(moRg)])
    for parseRangeLimit in [60, 300, 600, 1800, 3600, 7200]:
        summaryHR = []
        summaryBIA = []
        summaryLeft = []
        summaryRight = []

        if timeFlag[alarmOrder] - parseRangeLimit < 0:
            lowerBound = 0
        else:
            lowerBound = timeFlag[alarmOrder] - parseRangeLimit

        if timeFlag[alarmOrder] + parseRangeLimit > loopLen:
            upperBound = loopLen
        else:
            upperBound = timeFlag[alarmOrder] + parseRangeLimit

        xArr = []
        xArrbeforeNE = []
        xArrafterNE = []
        statsBIAbeforeNE = []
        statsBIAafterNE = []
        statsHRbeforeNE = []
        statsHRafterNE = []
        statsLeftbeforeNE = []
        statsLeftafterNE = []
        statsRightbeforeNE = []
        statsRightafterNE = []
        for i in range(lowerBound, upperBound):
            summaryBIA.append(bia[i])
            if 1500 < bia[i] < 1900:
                if i < timeFlag[alarmOrder]:
                    statsBIAbeforeNE.append(bia[i])
                elif i > timeFlag[alarmOrder]:
                    statsBIAafterNE.append(bia[i])

            summaryHR.append(hr[i])
            if i < timeFlag[alarmOrder]:
                statsHRbeforeNE.append(hr[i])
                xArrbeforeNE.append(i)
            elif i > timeFlag[alarmOrder]:
                statsHRafterNE.append(hr[i])
                xArrafterNE.append(i)

            summaryLeft.append(moLg[i])
            if moLg[i] > 0:
                if i < timeFlag[alarmOrder]:
                    statsLeftbeforeNE.append(moLg[i])
                elif i > timeFlag[alarmOrder]:
                    statsLeftafterNE.append(moLg[i])

            summaryRight.append(moRg[i])
            if moRg[i] > 0:
                if i < timeFlag[alarmOrder]:
                    statsRightbeforeNE.append(moRg[i])
                elif i > timeFlag[alarmOrder]:
                    statsRightafterNE.append(moRg[i])
            xArr.append(i)

        ### 1. aggregated stats

        if not statsBIAbeforeNE:
            statsBIAbeforeNE = [-1000]
        if not statsBIAafterNE:
            statsBIAafterNE = [-1000]
        if not statsHRbeforeNE:
            statsHRbeforeNE = [-1000]
        if not statsHRafterNE:
            statsHRafterNE = [-1000]
        if not statsLeftbeforeNE:
            statsLeftbeforeNE = [-1000]
        if not statsLeftafterNE:
            statsLeftafterNE = [-1000]
        if not statsRightbeforeNE:
            statsRightbeforeNE = [-1000]
        if not statsRightafterNE:
            statsRightafterNE = [-1000]        

        #print(str(np.min(statsBIAbeforeNE)) + "\t" + str(np.average(statsBIAbeforeNE)) + "\t" + str(np.max(statsBIAbeforeNE)) + "\t" + str(np.min(statsBIAafterNE)) + "\t" + str(np.average(statsBIAafterNE)) + "\t" + str(np.max(statsBIAafterNE)))
        #print(str(np.min(statsBIAbeforeNE)) + "\t" + str(np.average(statsBIAbeforeNE)) + "\t" + str(np.max(statsBIAbeforeNE)))
        #print(str(np.min(statsHRbeforeNE)) + "\t" + str(np.average(statsHRbeforeNE)) + "\t" + str(np.max(statsHRbeforeNE)) + "\t" + str(np.min(statsHRafterNE)) + "\t" + str(np.average(statsHRafterNE)) + "\t" + str(np.max(statsHRafterNE)))
        #print(str(np.min(statsLeftbeforeNE)) + "\t" + str(np.average(statsLeftbeforeNE)) + "\t" + str(np.max(statsLeftbeforeNE)) + "\t" + str(np.min(statsLeftafterNE)) + "\t" + str(np.average(statsLeftafterNE)) + "\t" + str(np.max(statsLeftafterNE)))
        #print(str(np.min(statsLeftbeforeNE)) + "\t" + str(np.average(statsLeftbeforeNE)) + "\t" + str(np.max(statsLeftbeforeNE)))
        #print(str(np.min(statsRightbeforeNE)) + "\t" + str(np.average(statsRightbeforeNE)) + "\t" + str(np.max(statsRightbeforeNE)) + "\t" + str(np.min(statsRightafterNE)) + "\t" + str(np.average(statsRightafterNE)) + "\t" + str(np.max(statsRightafterNE)))

        ### 2. individual stats

        outStr = ""
        cnt1600 = 0
        cnt1700 = 0
        cnt1800 = 0
        for p in range(len(statsBIAbeforeNE)):
            if 1600 <= statsBIAbeforeNE[p] < 1700:
                cnt1600 += 1
            elif 1700 <= statsBIAbeforeNE[p] < 1800:
                cnt1700 += 1
            elif 1800 <= statsBIAbeforeNE[p] < 1900:
                cnt1800 += 1
        #outStr += (str(cnt1600) + "\t" + str(cnt1700) + "\t" + str(cnt1800) + "\t")

        cnt1600 = 0
        cnt1700 = 0
        cnt1800 = 0
        for p in range(len(statsBIAafterNE)):
            if 1600 <= statsBIAafterNE[p] < 1700:
                cnt1600 += 1
            elif 1700 <= statsBIAafterNE[p] < 1800:
                cnt1700 += 1
            elif 1800 <= statsBIAafterNE[p] < 1900:
                cnt1800 += 1
        #outStr += (str(cnt1600) + "\t" + str(cnt1700) + "\t" + str(cnt1800) + "\n")

        hrSlopebeforeNE, intercept, r_value, p_value, std_err = stats.linregress(xArrbeforeNE, statsHRbeforeNE)
        #outStr += (str(hrSlopebeforeNE) + "\t\t\t")
        hrSlopeafterNE, intercept, r_value, p_value, std_err = stats.linregress(xArrafterNE, statsHRafterNE)
        #outStr += (str(hrSlopeafterNE) + "\n")

        cnt1 = 0
        cnt10 = 0
        cnt100 = 0
        for p in range(len(statsLeftbeforeNE)):
            if 1 <= statsLeftbeforeNE[p] < 10:
                cnt1 += 1
            elif 10 <= statsLeftbeforeNE[p] < 50:
                cnt10 += 1
            elif 50 <= statsLeftbeforeNE[p]:
                cnt100 += 1
        outStr += (str(cnt1) + "\t" + str(cnt10) + "\t" + str(cnt100) + "\t")
        print(outStr)
        cnt1 = 0
        cnt10 = 0
        cnt100 = 0
        for p in range(len(statsLeftafterNE)):
            if 1 <= statsLeftafterNE[p] < 10:
                cnt1 += 1
            elif 10 <= statsLeftafterNE[p] < 100:
                cnt10 += 1
            elif 100 <= statsLeftafterNE[p]:
                cnt100 += 1
        outStr += (str(cnt1) + "\t" + str(cnt10) + "\t" + str(cnt100) + "\n")

        cnt1 = 0
        cnt5 = 0
        cnt20 = 0
        for p in range(len(statsRightbeforeNE)):
            if 1 <= statsRightbeforeNE[p] < 5:
                cnt1 += 1
            elif 5 <= statsRightbeforeNE[p] < 20:
                cnt5 += 1
            elif 20 <= statsRightbeforeNE[p]:
                cnt20 += 1
        outStr += (str(cnt1) + "\t" + str(cnt5) + "\t" + str(cnt20) + "\t")
        cnt1 = 0
        cnt5 = 0
        cnt20 = 0
        for p in range(len(statsRightafterNE)):
            if 1 <= statsRightafterNE[p] < 5:
                cnt1 += 1
            elif 5 <= statsRightafterNE[p] < 20:
                cnt5 += 1
            elif 20 <= statsRightafterNE[p]:
                cnt20 += 1
        outStr += (str(cnt1) + "\t" + str(cnt5) + "\t" + str(cnt20))
        #print(outStr)

        tickArr = [lowerBound, timeFlag[alarmOrder], upperBound]
        ### 5. Transform data into graph and then store graphs as image files ###
        """
        titleSize = 80
        labelSize = 80
        lineWidth = 5
        
        plotTypeArr = ['dot']  # , 'line']
        sensorArr = ['bia', 'hr', 'left_gyr', 'right_gyr']
        for plotType in plotTypeArr:
            for sensor in sensorArr:
                fig = plt.figure(figsize=(70, 30))
                fig.suptitle(sensor, fontsize=titleSize)
                plt.tick_params(labelsize=labelSize)
                if sensor == 'bia':
                    sensor = 'bia_' + str(parseRangeLimit)
                    yMin = 1500
                    yMax = 2000
                    dataArr = summaryBIA
                elif sensor == 'hr':
                    sensor = 'hr_' + str(parseRangeLimit)
                    yMin = 40
                    yMax = 200
                    dataArr = summaryHR
                elif sensor == 'left_gyr' or sensor == 'right_gyr':
                    yMin = -20
                    yMax = 100
                    if sensor == 'left_gyr':
                        sensor = 'left_gyr_' + str(parseRangeLimit)
                        dataArr = summaryLeft
                    elif sensor == 'right_gyr':
                        sensor = 'right_gyr_' + str(parseRangeLimit)
                        dataArr = summaryRight

                if timeFlag:
                    plt.vlines(x=timeFlag[alarmOrder], ymin=yMin, ymax=yMax, colors='red', linewidth=lineWidth, linestyles='solid', label='NE detected')
                
                #if hourFlag:
                    #for k in range(len(hourFlag)):
                        #plt.vlines(x=hourFlag[k], ymin=yMin, ymax=yMax, colors='blue', linewidth=lineWidth,
                                   #linestyles='solid', label='every hour')
                
                plt.ylim(top=yMax, bottom=yMin)
                plt.xlim(right=upperBound, left=lowerBound)
                plt.xticks(ticks=tickArr)
                # plt.xticks(ticks=[10800, 11100, 11400, 11700, 12000])
                # plt.plot(moi, color='black', linewidth=3)
                if plotType == 'dot':
                    plt.plot(xArr, dataArr, 'ko')
                elif plotType == 'line':
                    plt.plot(dataArr, color='black', linewidth=3)
                plt.savefig(outFilePath + sensor + '_' + plotType + '.png')
                plt.close(fig)
        """


def generateCSV(rootPath, windowSize, minBIA, maxBIA, NEseq):
    dirData = [x.strip() for x in rootPath.split('\\')]
    expDate = dirData[4]
    inFile = open(rootPath + expDate + "_NE_filled_merged_complete.csv", "r")
    HRFile = open(rootPath + expDate + "_hr_ecg_final.csv", "r")
    moLgFile = open(rootPath + expDate + "_Mo_lg_persec.csv", "r")
    moRgFile = open(rootPath + expDate + "_Mo_rg_persec.csv", "r")
    moLaFile = open(rootPath + expDate + "_Mo_la_persec.csv", "r")
    moRaFile = open(rootPath + expDate + "_Mo_ra_persec.csv", "r")
    featureFile = open(rootPath + expDate + "_feature_data_win"+str(windowSize)+".arff", "w")

    # buffer for 5-minute data
    bufBIA = []
    bufHR = []
    bufMoLa = []
    bufMoLg = []
    bufMoRa = []
    bufMoRg = []

    # buffer for total features for total period
    finalBIAfeat = []
    finalHRfeat = []
    finalMoLafeat = []
    finalMoLgfeat = []
    finalMoRafeat = []
    finalMoRgfeat = []

    # NE_filled_merged_complete.csv (마지막에 버퍼에 쌓인 것은 계산 안됨 - while loop 이후에 한번 더 처리하면 되는데, 맨 마지막 부분이라 그냥 날림)
    prevSEQ = 0
    prevBIA = maxBIA
    while True:
        # header
        line = inFile.readline()
        if not line:
            break
        lineData = [x.strip() for x in line.split(',')]
        currentSEQ = int(lineData[0].replace("SEQ=", ""))
        neFlag = int(lineData[1].replace("NE=", ""))

        if currentSEQ - prevSEQ == (windowSize*4):
            x = []
            for j in range(0, len(bufBIA)):
                x.append(j)
            s, intercept, r_value, p_value, std_err = stats.linregress(x, bufBIA)
            finalBIAfeat.append([np.min(bufBIA), np.percentile(bufBIA, 25), np.median(bufBIA), np.percentile(bufBIA, 75), np.max(bufBIA), np.mean(bufBIA), np.std(bufBIA), s]) # min per25 med per75 max mean std slope
            prevSEQ = currentSEQ
            bufBIA = []

        # data
        for i in range(64):
            line = inFile.readline()
            lineData = [x.strip() for x in line.split(',')]
            if minBIA < int(lineData[1]) < maxBIA:
                bufBIA.append(int(lineData[1]))
                prevBIA = int(lineData[1])
            else:
                bufBIA.append(prevBIA)

    # hr_ecg_final_persec.csv (마지막에 버퍼에 쌓인 것은 계산 안됨 - while loop 이후에 한번 더 처리하면 되는데, 맨 마지막 부분이라 그냥 날림)
    hrline = HRFile.readline() # date
    hrline = HRFile.readline() # time
    prevTime = 0
    while True:
        hrline = HRFile.readline()
        if not hrline:
            break
        hrData = [x.strip() for x in hrline.split(',')]
        currentTime = float(hrData[0])
        if currentTime - prevTime > windowSize:

            x = []
            for j in range(0, len(bufHR)):
                x.append(j)
            s, intercept, r_value, p_value, std_err = stats.linregress(x, bufHR)

            if np.isnan(s):
                s = 0

            for k in range(int((currentTime - prevTime)/windowSize)):
                if k == 0:
                    finalHRfeat.append([np.min(bufHR), np.percentile(bufHR, 25), np.median(bufHR), np.percentile(bufHR, 75), np.max(bufHR), np.mean(bufHR), np.std(bufHR), s]) # min per25 med per75 max mean std slope
                else:
                    finalHRfeat.append([np.min(bufHR), np.percentile(bufHR, 25), np.median(bufHR), np.percentile(bufHR, 75), np.max(bufHR), np.mean(bufHR), np.std(bufHR), 0])  # min per25 med per75 max mean std slope

            prevTime = (prevTime + int((currentTime - prevTime)/windowSize)*windowSize)
            bufHR = []

        bufHR.append(float(hrData[1]))

    # Mo_ra_persec.csv, Mo_rg_persec.csv, Mo_la_persec.csv, Mo_lg_persec.csv
    moLgFile.readline() # data
    moLgFile.readline() # time
    moLaFile.readline()
    moLaFile.readline()
    moRgFile.readline()
    moRgFile.readline()
    moRaFile.readline()
    moRaFile.readline()

    prevLg = 0
    prevLa = 0
    prevRg = 0
    prevRa = 0
    cnt = 0
    while True:
        moLgLine = moLgFile.readline()
        moLaLine = moLaFile.readline()
        moRgLine = moRgFile.readline()
        moRaLine = moRaFile.readline()
        if not moLgLine:
            break
        moLgData = [x.strip() for x in moLgLine.split('\n')]
        moLaData = [x.strip() for x in moLaLine.split('\n')]
        moRgData = [x.strip() for x in moRgLine.split('\n')]
        moRaData = [x.strip() for x in moRaLine.split('\n')]

        if cnt != 0 and cnt % windowSize == (windowSize - 1):
            if bufMoLg != []: # not empty
                x = []
                for j in range(0, len(bufMoLg)):
                    x.append(j)
                sLg, intercept, r_value, p_value, std_err = stats.linregress(x, bufMoLg)
                x = []
                for j in range(0, len(bufMoLa)):
                    x.append(j)
                sLa, intercept, r_value, p_value, std_err = stats.linregress(x, bufMoLa)
                x = []
                for j in range(0, len(bufMoRg)):
                    x.append(j)
                sRg, intercept, r_value, p_value, std_err = stats.linregress(x, bufMoRg)
                x = []
                for j in range(0, len(bufMoRa)):
                    x.append(j)
                sRa, intercept, r_value, p_value, std_err = stats.linregress(x, bufMoRa)

                finalMoLgfeat.append([np.min(bufMoLg), np.percentile(bufMoLg, 25), np.median(bufMoLg), np.percentile(bufMoLg, 75), np.max(bufMoLg), np.mean(bufMoLg), np.std(bufMoLg)])
                finalMoLafeat.append([np.min(bufMoLa), np.percentile(bufMoLa, 25), np.median(bufMoLa), np.percentile(bufMoLa, 75), np.max(bufMoLa), np.mean(bufMoLa), np.std(bufMoLa)])
                finalMoRgfeat.append([np.min(bufMoRg), np.percentile(bufMoRg, 25), np.median(bufMoRg), np.percentile(bufMoRg, 75), np.max(bufMoRg), np.mean(bufMoRg), np.std(bufMoRg)])
                finalMoRafeat.append([np.min(bufMoRa), np.percentile(bufMoRa, 25), np.median(bufMoRa), np.percentile(bufMoRa, 75), np.max(bufMoRa), np.mean(bufMoRa), np.std(bufMoRa)])
            else: # empty
                finalMoLgfeat.append([0,0,0,0,0,0,0])
                finalMoLafeat.append([0,0,0,0,0,0,0])
                finalMoRgfeat.append([0,0,0,0,0,0,0])
                finalMoRafeat.append([0,0,0,0,0,0,0])

            bufMoLg = []
            bufMoLa = []
            bufMoRg = []
            bufMoRa = []

        if float(moLgData[0]) != -10:
            bufMoLg.append(float(moLgData[0]))
        if float(moLaData[0]) != -10:
            bufMoLa.append(float(moLaData[0]))
        if float(moRgData[0]) != -10:
            bufMoRg.append(float(moRgData[0]))
        if float(moRaData[0]) != -10:
            bufMoRa.append(float(moRaData[0]))
        cnt += 1

    moLgFile.close()
    moRgFile.close()
    moLaFile.close()
    moRaFile.close()
    inFile.close()
    HRFile.close()

    for z in range(np.min([len(finalBIAfeat), len(finalHRfeat), len(finalMoLgfeat), len(finalMoLafeat), len(finalMoRgfeat), len(finalMoRafeat)])):
        for a in range(len(finalBIAfeat[z])):
            featureFile.write(str(finalBIAfeat[z][a])+",")
        for b in range(len(finalHRfeat[z])):
            featureFile.write(str(finalHRfeat[z][b])+",")
        for c in range(len(finalMoLgfeat[z])):
            featureFile.write(str(finalMoLgfeat[z][c])+",")
        for d in range(len(finalMoLafeat[z])):
            featureFile.write(str(finalMoLafeat[z][d])+",")
        for e in range(len(finalMoRgfeat[z])):
            featureFile.write(str(finalMoRgfeat[z][e])+",")
        for f in range(len(finalMoRafeat[z])):
            featureFile.write(str(finalMoRafeat[z][f])+",")

        # label
        featureFile.write(str(int(NEseq/4) - z*windowSize) + "\n")

    featureFile.close()


def refineBIA(inFilePath, outFilePath):
    finalBIAFile = open(inFilePath + "_NE_filled_merged_complete.csv", "r")

    cnt = 0
    slopeArr = [0.0] # unit: 1/4 second
    bia = []
    pktBia = []
    while True:
        line = finalBIAFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break
        if cnt != 0 and cnt % 65 == 0: # header
            x = []
            for j in range(0, len(bia)):
                x.append(j)
            s, intercept, r_value, p_value, std_err = stats.linregress(x, bia)
            slopeArr.append(s)

            pktBia.append(np.average(bia))
            bia = []
        elif cnt % 65 != 0: # data
            lineData = [x.strip() for x in line.split(',')]
            bia.append(float(lineData[1]))
        cnt += 1

    finalBIAFile.seek(0, 0)
    timeFlag = []
    cnt = 0
    while True:
        line = finalBIAFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break
        if cnt % 65 == 0: # header
            lineData = [x.strip() for x in line.split(',')]
            NEflag = int(lineData[1].replace("NE=", ""))
            if NEflag == 1:
                timeFlag.append(cnt/(65))
        cnt += 1


    xAxis = []
    for t in range(len(pktBia)):
        xAxis.append(t)
    gradArr = np.gradient(pktBia, xAxis)


    histArr = [0, 0, 0, 0, 0, 0, 0, 0, 0] # 0, -0.01~0.01, -0.1~0.1 , -0.5~0.5, -1~1, -10~10, -100~100, -1000~1000, rest of them
    for z in range(len(slopeArr)):
        if abs(slopeArr[z]) == 0:
            histArr[0] += 1
        elif abs(slopeArr[z]) <= 0.01:
            histArr[1] += 1
        elif 0.01 < abs(slopeArr[z]) <= 0.1:
            histArr[2] += 1
        elif 0.1 < abs(slopeArr[z]) <= 0.5:
            histArr[3] += 1
        elif 0.5 < abs(slopeArr[z]) <= 1:
            histArr[4] += 1
        elif 1 < abs(slopeArr[z]) <= 10:
            histArr[5] += 1
        elif 10 < abs(slopeArr[z]) <= 100:
            histArr[6] += 1
        elif 100 < abs(slopeArr[z]) <= 1000:
            histArr[7] += 1
        else:
            histArr[8] += 1

    outStr = ""
    for z in range(len(histArr)):
        outStr += (str(histArr[z]) + "\t")
        #print(histArr[z])
    print(outStr)

    titleSize = 80
    labelSize = 80
    lineWidth = 5

    fig = plt.figure(figsize=(70, 30))
    fig.suptitle('Moisture', fontsize=titleSize)
    plt.tick_params(labelsize=labelSize)
    yMin = -100
    yMax = 100
    plt.vlines(x=timeFlag, ymin=yMin, ymax=yMax, colors='red', linewidth=lineWidth, linestyles='solid',
               label='motion detected')
    plt.ylim(top=yMax, bottom=yMin)
    #plt.xticks(ticks=tickArr)
    plt.plot(gradArr, 'ko')
    plt.savefig(outFilePath + 'BIA_slope_per_packet.png')
    plt.close(fig)
