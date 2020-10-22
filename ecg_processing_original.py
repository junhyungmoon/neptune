#from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg
import pyqtgraph.exporters
import pylab as plt
import math
from pathlib import Path
import glob
import os
from biosppy import ecg

setID = '01' # device ID
for datePostfix in [11]:
    if datePostfix == 19:
        continue
    if datePostfix < 10:
        date = '19060' + str(datePostfix)
    else:
        date = '1906' + str(datePostfix)
    rootPath = "D:\\neptuNE\\ne\\" + setID + "\\" + date + "\\"#
    inFile = open(rootPath + date + "_NE_filled_merged_complete.csv", "r")
    outFile = open(rootPath + date + "_NE_filled_merged_hr.csv", "w")
    outFile2 = open(rootPath + date + "_NE_filled_merged_hr_refined.csv", "w")
    outFilePath = rootPath

    fileSize = len(inFile.readlines())
    hourLine = int(fileSize / (65 * 4 * 3600)) + 1
    tickArr = []
    hourFlag = []
    for k in range(hourLine + 1):
        # tickArr.append(k * 64 * 4 * 3600)
        # hourFlag.append(k * 64 * 4 * 3600)
        tickArr.append(k * 3600)
        hourFlag.append(k * 3600)
    inFile.seek(0, 0)

    cnt = 0
    NEflag = -1
    NEpos = []
    pktCnt = 0
    freqECG = 256
    ecgBuf = []
    while True:
        line = inFile.readline()  # 라인 by 라인으로 데이터 읽어오기
        if not line:
            break

        lineData = [x.strip() for x in line.split(',')]
        if cnt % 65 !=0: # NOT header
            ecgBuf.append(int(lineData[0]))
        else: # header
            NEflag = int(lineData[1].replace("NE=", ""))  #
            if NEflag == 1:
                NEpos.append(int(pktCnt/4))
            pktCnt += 1
        cnt += 1
    inFile.close()

    resultECG = ecg.ecg(signal=ecgBuf, sampling_rate=freqECG, show=False)
    rawhr_t = resultECG[5] # seconds
    rawhr = resultECG[6] #

    for z in range(len(rawhr)):
        outFile.write(str(rawhr_t[z]) + "," + str(rawhr[z]) + "\n")
    outFile.close()

    tmpHR = []
    sec = 10 # 시작 후 10초부터 연산하려 함(초반이 불안정할 것 같아서 임의로 설정)
    refinedhr = []
    refinedhr_t = []
    for k in range(len(rawhr)):
        if rawhr_t[k] >= sec:
            curHR = np.average(tmpHR)
            diff = int(rawhr_t[k]) - sec
            for y in range(diff):
                refinedhr.append(curHR)
                refinedhr_t.append(sec)
                sec += 1
            refinedhr.append(curHR)
            refinedhr_t.append(sec)
            sec += 1 # 1초씩 증가
            tmpHR = []
        tmpHR.append(rawhr[k])
    if tmpHR:
        refinedhr.append(np.average(tmpHR))
        refinedhr_t.append(sec)

    finalhr = [refinedhr[0], refinedhr[0], refinedhr[0], refinedhr[0], refinedhr[0], refinedhr[0], refinedhr[0], refinedhr[0], refinedhr[0], refinedhr[0]] + refinedhr
    finalhr_t = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] + refinedhr_t

    for z in range(len(finalhr)):
        outFile2.write(str(finalhr_t[z]) + "," + str(finalhr[z]) + "\n")
    outFile2.close()

    titleSize = 80
    labelSize = 80
    lineWidth = 3


    plotTypeArr = ['dot'] #'dot',
    sensorArr = ['rawHR', 'refinedHR', 'rawHR_clipped', 'refinedHR_clipped'] # 'rawECG',
    for plotType in plotTypeArr:
        for sensor in sensorArr:
            fig = plt.figure(figsize=(70, 30))
            fig.suptitle(sensor, fontsize=titleSize)
            plt.tick_params(labelsize=labelSize)
            if sensor == 'rawHR':
                dataArr = rawhr
                xArr = rawhr_t
                yMin = 40
                yMax = 120
                plt.ylim(top=yMax, bottom=yMin)
                for j in range(len(NEpos)):
                    plt.vlines(x=NEpos[j], ymin=yMin, ymax=yMax, colors='red', linewidth=lineWidth,
                               linestyles='solid', label='NE detected')
                for j in range(len(hourFlag)):
                    plt.vlines(x=hourFlag[j], ymin=yMin, ymax=yMax, colors='blue', linewidth=lineWidth,
                               linestyles='solid', label='NE detected')
            elif sensor == 'refinedHR':
                dataArr = finalhr
                xArr = finalhr_t
                yMin = 40
                yMax = 120
                plt.ylim(top=yMax, bottom=yMin)
                for j in range(len(NEpos)):
                    plt.vlines(x=NEpos[j], ymin=yMin, ymax=yMax, colors='red', linewidth=lineWidth,
                               linestyles='solid', label='NE detected')
                for j in range(len(hourFlag)):
                    plt.vlines(x=hourFlag[j], ymin=yMin, ymax=yMax, colors='blue', linewidth=lineWidth,
                               linestyles='solid', label='NE detected')
            elif sensor == 'rawHR_clipped':
                dataArr = finalhr
                xArr = finalhr_t
                yMin = 40
                yMax = 200
                plt.ylim(top=yMax, bottom=yMin)
                for j in range(len(NEpos)):
                    plt.vlines(x=NEpos[j], ymin=yMin, ymax=yMax, colors='red', linewidth=lineWidth,
                               linestyles='solid', label='NE detected')
                for j in range(len(hourFlag)):
                    plt.vlines(x=hourFlag[j], ymin=yMin, ymax=yMax, colors='blue', linewidth=lineWidth,
                               linestyles='solid', label='NE detected')
                #plt.xlim(right=NEpos[0] + 600, left=NEpos[0] - 600)
                #plt.xticks(ticks=[NEpos[0] - 600, NEpos[0] - 300, NEpos[0], NEpos[0] + 300, NEpos[0] + 600])
            elif sensor == 'refinedHR_clipped':
                dataArr = finalhr
                xArr = finalhr_t
                yMin = 40
                yMax = 200
                plt.ylim(top=yMax, bottom=yMin)
                for j in range(len(NEpos)):
                    plt.vlines(x=NEpos[j], ymin=yMin, ymax=yMax, colors='red', linewidth=lineWidth,
                               linestyles='solid', label='NE detected')
                for j in range(len(hourFlag)):
                    plt.vlines(x=hourFlag[j], ymin=yMin, ymax=yMax, colors='blue', linewidth=lineWidth,
                               linestyles='solid', label='NE detected')
                #plt.xlim(right=NEpos[0] + 600, left=NEpos[0] - 600)
                #plt.xticks(ticks=[NEpos[0] - 600, NEpos[0] - 300, NEpos[0], NEpos[0] + 300, NEpos[0] + 600])
            elif sensor == 'rawECG':
                dataArr = ecgBuf

            if plotType == 'dot':
                plt.plot(xArr, dataArr, 'ko')
            elif plotType == 'line':
                plt.plot(xArr, dataArr, color='black', linewidth=3)

            plt.savefig(outFilePath + sensor + '_' + plotType + '.png')
            plt.close(fig)
