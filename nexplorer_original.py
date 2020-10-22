##############################################
# Developed by Junhyung Moon (Yonsei Univ.)
# Latest update: 21, Feb, 2019
##############################################

# -*- coding: utf-8 -*-
# All of the plots may be panned/scaled by dragging with the left/right mouse buttons.
# Right click on any plot to show a context menu.

#from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg
import pyqtgraph.exporters
import pylab as plt
import math
from pathlib import Path
import glob
import os
from scipy import stats

from functions import mergeNEFiles, mergeMoFiles, fillLossNE, interpolateNdivideMoFiles, scanNEFiles, visualizeAllFiles, predictNE, interpolateGraphs, parseNearNE, conditionalVisualize, plotBIADerivatives, examineNE, readyFiles, visualizeAllFilesV2, visualizeRawMOIdata, findNE, generateCSV, refineBIA


###############################
# 0. Define global information
###############################

examineFlag = 0
preprocessFlag = 0
mergeFlag = 0
scanFlag = 0
refineFlag = 0
plotFlag = 1
condPlotFlag = 0
derivPlotFlag = 0
predictFlag = 0
parseNEFlag = 0
interpolateFlag = 0
generateCSVFlag = 0 # for machine learning
refineBIAFlag = 0

#print(np.gradient([2,4,5], [1,2,3]))
#arrZ = np.gradient([2,4,6], [1,2,3])
#print(arrZ)
#arrZ.tolist()
#print(arrZ[1])

setID = '09' # device ID
month = '04'
year = '20'
for datePostfix in [10]:#range(1,25):#[5,6,8,9,10,11,12,13,14,15]:#[2,4,6,8,9,11,17,18]: #
    if datePostfix < 10:
        date = year + month + '0' + str(datePostfix)
    else:
        date = year + month + str(datePostfix)
    rootPath = "D:\\neptuNE\\ne\\" + setID + "\\" + date + "\\"#
    rawNEFileList = glob.glob(rootPath + "*_NE_*_*.csv")
    rawMOFileList = glob.glob(rootPath + "*_MO_*_*.csv")

    ################################################################################################################################
    # Examine individual NE file whether it has SEQ which is not in increasing order or a group of data which are not 64 instances #
    ################################################################################################################################
    if examineFlag == 1:
        for inFilePath in rawNEFileList:
            my_file = Path(inFilePath)
            if my_file.is_file():  # if file exists,
                examineNE(inFilePath)

    ##########################################################################################################################################################
    # Fill loss in individual NE files                                                                                                                       #
    # Aggregate data into every second in individual MO files, and then divide each result file into 4 files of left-acc, left-gyr, right-acc, and right-gyr #
    ##########################################################################################################################################################
    if preprocessFlag == 1:
        for inFilePath in rawNEFileList:
            my_file = Path(inFilePath)
            if my_file.is_file():  # if file exists,
                dirData = [x.strip() for x in inFilePath.split('\\')]
                dir5Data = [x.strip() for x in dirData[5].split('_')]
                outFilePathPre = rootPath + dir5Data[3] + "_" + dir5Data[4]
                outFilePathPost = "_NE_filled.csv"
                fillLossNE(inFilePath, outFilePathPre, outFilePathPost)

        for inFilePath in rawMOFileList:
            my_file = Path(inFilePath)
            if my_file.is_file():  # if file exists,
                dirData = [x.strip() for x in inFilePath.split('\\')]
                dir5Data = [x.strip() for x in dirData[5].split('_')]
                outFilePath = rootPath + dir5Data[3] + "_" + dir5Data[4]
                interpolateNdivideMoFiles(inFilePath, outFilePath)

    ###################################
    # Merge individual files into one #
    ###################################
    filledNEFileList = glob.glob(rootPath + "*_NE_filled.csv")
    if mergeFlag == 1:
        mergeNEFiles(rootPath, filledNEFileList) # NEWear
        inFilePath = rootPath + date + "_NE_filled_merged.csv"
        my_file = Path(inFilePath)
        if my_file.is_file():  # if file exists,
            inFile = open(inFilePath, "r")
            dirData = [x.strip() for x in inFilePath.split('\\')]
            dir5Data = [x.strip() for x in dirData[5].split('_')]
            outFilePathPre = rootPath + dir5Data[0]
            outFilePathPost = "_NE_filled_merged_complete.csv"
            # fill loss between NE files if exists
            fillLossNE(inFilePath, outFilePathPre, outFilePathPost)

        mergeMoFiles(rootPath) # MetaWear

    ##########################################
    # Scan files to derive statistical info. #
    ##########################################
    if scanFlag == 1:
        resultStr = scanNEFiles(rootPath + date)

        size = 0
        inFileList = glob.glob(rootPath + "Patient_*.csv")
        for inFilePath in inFileList:
            my_file = Path(inFilePath)
            if my_file.is_file():
                size += os.path.getsize(inFilePath)
        MB = size / 1024 / 1024

        resultStr += (str(MB))
        print(resultStr)

    #####################################################################
    # Prepare files to be parsed, plotted, interpolated, analyzed, etc. #
    #####################################################################
    if refineFlag == 1:
        inFilePath = rootPath + date + "_NE_filled_merged_complete.csv"
        moLaFilePath = rootPath + date + "_Mo_la_filled_merged.csv"
        moLgFilePath = rootPath + date + "_Mo_lg_filled_merged.csv"
        moRaFilePath = rootPath + date + "_Mo_ra_filled_merged.csv"
        moRgFilePath = rootPath + date + "_Mo_rg_filled_merged.csv"
        readyFiles(inFilePath, moLaFilePath, moLgFilePath, moRaFilePath, moRgFilePath, rootPath + date)

    ### 4. Save plot images ###
    if plotFlag == 1:
        inFilePath = rootPath + date
        imagePath = rootPath
        biaMin = 0
        biaMax = 9000
        hrMin = 40
        hrMax = 200
        moiMin = 0
        moiMax = 12000
        movMin = -20
        movMax = 100
        visualizeAllFilesV2(inFilePath, imagePath, biaMin, biaMax, hrMin, hrMax, moiMin, moiMax, movMin, movMax)

        biaMin = 1500
        biaMax = 2000
        hrMin = -1
        hrMax = -1
        moiMin = -1
        moiMax = -1
        movMin = -1
        movMax = -1
        visualizeAllFilesV2(inFilePath, imagePath, biaMin, biaMax, hrMin, hrMax, moiMin, moiMax, movMin, movMax)

        biaMin = 1880
        biaMax = 2000
        visualizeAllFilesV2(inFilePath, imagePath, biaMin, biaMax, hrMin, hrMax, moiMin, moiMax, movMin, movMax)

        biaMin = 1700
        biaMax = 1900
        visualizeAllFilesV2(inFilePath, imagePath, biaMin, biaMax, hrMin, hrMax, moiMin, moiMax, movMin, movMax)

        biaMin = 1900
        biaMax = 2600
        visualizeAllFilesV2(inFilePath, imagePath, biaMin, biaMax, hrMin, hrMax, moiMin, moiMax, movMin, movMax)

        biaMin = 1700
        biaMax = 2800
        visualizeAllFilesV2(inFilePath, imagePath, biaMin, biaMax, hrMin, hrMax, moiMin, moiMax, movMin, movMax)

        biaMin = 1500
        biaMax = 3000
        visualizeAllFilesV2(inFilePath, imagePath, biaMin, biaMax, hrMin, hrMax, moiMin, moiMax, movMin, movMax)

        biaMin = 2250
        biaMax = 2400
        visualizeAllFilesV2(inFilePath, imagePath, biaMin, biaMax, hrMin, hrMax, moiMin, moiMax, movMin, movMax)

        biaMin = -1
        biaMax = -1
        hrMin = 40
        hrMax = 160
        moiMin = -1
        moiMax = -1
        movMin = -1
        movMax = -1
        visualizeAllFilesV2(inFilePath, imagePath, biaMin, biaMax, hrMin, hrMax, moiMin, moiMax, movMin, movMax)

        hrMin = 60
        hrMax = 80
        visualizeAllFilesV2(inFilePath, imagePath, biaMin, biaMax, hrMin, hrMax, moiMin, moiMax, movMin, movMax)

        biaMin = -1
        biaMax = -1
        hrMin = -1
        hrMax = -1
        moiMin = -1
        moiMax = -1
        movMin = 0
        movMax = 100
        visualizeAllFilesV2(inFilePath, imagePath, biaMin, biaMax, hrMin, hrMax, moiMin, moiMax, movMin, movMax)

        hrMin = 60
        hrMax = 100
        visualizeAllFilesV2(inFilePath, imagePath, biaMin, biaMax, hrMin, hrMax, moiMin, moiMax, movMin, movMax)

        hrMin = 60
        hrMax = 140
        visualizeAllFilesV2(inFilePath, imagePath, biaMin, biaMax, hrMin, hrMax, moiMin, moiMax, movMin, movMax)

        hrMin = 65
        hrMax = 75
        visualizeAllFilesV2(inFilePath, imagePath, biaMin, biaMax, hrMin, hrMax, moiMin, moiMax, movMin, movMax)

        for inFilePath in rawNEFileList:
            my_file = Path(inFilePath)
            if my_file.is_file():  # if file exists,
                if findNE(inFilePath) == 1:
                    moiMin = 0
                    moiMax = 9000
                    visualizeRawMOIdata(inFilePath, imagePath, moiMin, moiMax)

    ### 5. Rule-based NE prediction
    if predictFlag == 1:
        predictNE(rootPath)

    ### 6.
    if interpolateFlag == 1:
        interpolateGraphs(rootPath)

    ###
    if parseNEFlag == 1:
        if datePostfix == 4:
            alarmOrder = 2
        else:
            alarmOrder = 0
        parseNearNE(rootPath, alarmOrder)

    ###
    if condPlotFlag == 1:
        conditionalVisualize(rootPath)

    ###
    if derivPlotFlag == 1:
        plotBIADerivatives(rootPath)

    ###
    if generateCSVFlag == 1:
        minBIA = 2000
        maxBIA = 2500
        windowSize = 60 # sec
        NEseq = 101558
        generateCSV(rootPath + "MLdata\\", windowSize, minBIA, maxBIA, NEseq)

    ###
    if refineBIAFlag == 1:
        imagePath = rootPath + "refined\\"
        refineBIA(rootPath + date, imagePath)