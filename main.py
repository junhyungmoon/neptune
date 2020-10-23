from codes.functions import merge_one_night_files, examineNEfiles, examineMOfiles, interpolateNEfiles, interpolateMOfiles
import glob
import numpy as np

rootPath = "E:\\mjh\\study\\neptune\\ne_data\\"
subNum = 5
if subNum < 10:
    fPath = rootPath + "P0" + str(subNum)
else:
    fPath = rootPath + "P" + str(subNum)

#merge_one_night_files(fPath)

fPathList = sorted(glob.glob(fPath + "\\merged\\NE\\*.csv"))
#examineNEfiles(fPathList)

fPathList = sorted(glob.glob(fPath + "\\merged\\MO\\*.csv"))
#examineMOfiles(fPathList)

# CAUTION: 6 and 7 are dependent according to hierarchy of directories (ex. PC in lab. vs. PC in home)
srcPathList = sorted(glob.glob(fPath + "\\merged\\NE\\*.csv"))
for srcFilePath in srcPathList:
    tmp = [x.strip() for x in srcFilePath.split('\\')]
    destFilePath = '\\'.join(np.concatenate((np.array(tmp[:6] + ['interpolated']),np.array(tmp[7:]))))
    #interpolateNEfiles(srcFilePath, destFilePath)

# CAUTION: 6 and 7 are dependent according to hierarchy of directories (ex. PC in lab. vs. PC in home)
srcPathList = sorted(glob.glob(fPath + "\\merged\\MO\\*.csv"))
for srcFilePath in srcPathList:
    tmp = [x.strip() for x in srcFilePath.split('\\')]
    date_time = [x.strip() for x in tmp[-1].split('.')][0]
    destFilePath = '\\'.join(np.array(tmp[:6] + ['interpolated\\MO', date_time]))
    interpolateMOfiles(srcFilePath, destFilePath)