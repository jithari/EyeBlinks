

#..........................................#

##############################
#Team - Titans
#Module - EyeBlinkModue - blink_detector.py
#Author - Jithari_Jayarathne

##############################

from scipy.spatial import distance as dist
from imutils.video import FileVideoStream
from scipy.signal import argrelextrema
from imutils.video import VideoStream
from imutils import face_utils
import numpy as np
import argparse
import imutils
import time
import dlib
import cv2
import os
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import load_model
import datetime as dt

def eye_aspect_ratio(eye):

    # compute the euclidean distances between the two sets of
    # vertical eye landmarks (x, y)-coordinates
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])
    # compute the euclidean distance between the horizontal
    # eye landmark (x, y)-coordinates
    C = dist.euclidean(eye[0], eye[3])

    if C < 0.1:  # practical finetuning due to possible numerical issue as a result of optical flow
        ear = 0.3
    else:
        # compute the eye aspect ratio
        ear = (A + B) / (2.0 * C)
    if ear > 0.45:
        ear = 0.45
    # return the eye aspect ratio
    return ear


def start_check(blink_index_list, ear):
    start = np.array([], dtype=np.int64)
    Bool = True
    for i in blink_index_list:
        Bool = True
        j = i - 1
        while Bool and j > 0:
            if ear[j] <= ear[j - 1]:
                j -= 1
            else:
                start = np.append(start, j)
                Bool = False
                # this condition is to make sure that we can save the end value even if it is that last value , since in the while condition
        # we're going to stop before the last value to avoid the index out of bounds error
        if j == 0:
            start = np.append(start, j)
    return start


def end_check(blink_index_list, ear):
    end = np.array([], dtype=np.int64)
    Bool = True
    for i in blink_index_list:
        Bool = True
        j = i + 1

        while Bool and j < len(ear) - 1:
            if ear[j] <= ear[j + 1]:

                j += 1
            else:
                end = np.append(end, j)
                Bool = False
                # this condition is to make sure that we can save the end value even if it is that last value , since in the while condition
        # we're going to stop before the last value to avoid the index out of bounds error
        if j == len(ear) - 1:
            end = np.append(end, j)

    return end

EYE_AR_THRESH = 0.3
EYE_AR_CONSEC_FRAMES = 3
train_blink_Final_1 = np.array([]).reshape(0,4)
labels_blink_Final_1 =  np.array([]).reshape(0,1)
# initialize the frame counters and the total number of blinks
COUNTER = 0
TOTAL = 0
EAR = []
i = 0
Final_Result = 0
COUNT = 0

datFile =  "./shape_predictor_68_face_landmarks.dat"
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(datFile)

(lStart, lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
(rStart, rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]

time.sleep(1.0)
t = dt.datetime.now()

vs = cv2.VideoCapture("5.mp4")  #path to video
#vs = cv2.VideoCapture(0)
while True:
    delta = dt.datetime.now() - t
    if delta.seconds >= 120:
        print("2 Minutes has passed...")
        print(Final_Result / COUNT * 10)
        print("2 Minutes has passed...")
        # Update 't' variable to new time
        t = dt.datetime.now()

    ret, frame = vs.read()

    if ret == False:
        break
    frame = imutils.resize(frame, width=450)
    #cv2_imshow(frame)

    # frame = cv2.resize(frame, dim, interpolation = cv2.INTER_AREA)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # detect faces in the grayscale frame
    rects = detector(gray, 0)
    for rect in rects:
        COUNTER += 1
        shape = predictor(gray, rect)
        shape = face_utils.shape_to_np(shape)
        leftEye = shape[lStart:lEnd]
        rightEye = shape[rStart:rEnd]
        leftEAR = eye_aspect_ratio(leftEye)
        rightEAR = eye_aspect_ratio(rightEye)
        EAR.append((leftEAR + rightEAR) / 2.0)
        leftEyeHull = cv2.convexHull(leftEye)
        rightEyeHull = cv2.convexHull(rightEye)
        cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
        cv2.drawContours(frame, [rightEyeHull], -1, (0, 255, 0), 1)
        cv2.putText(frame, "EAR: {:.2f}".format((leftEAR + rightEAR) / 2.0), (300, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    if COUNTER == 500:
        ear = np.array(EAR)
        ear.reshape(ear.shape[0])
        index_peak = argrelextrema(ear, np.less)
        index_peak_blink = np.array([])

        for i in index_peak[0]:
            if EAR[i] < 0.3:
                index_peak_blink = np.append(index_peak_blink, i)
        index_peak_blink = index_peak_blink.astype(np.int64)
        start = start_check(index_peak_blink, ear)
        # end of blinks
        end = end_check(index_peak_blink, ear)
        # duration of blinks
        Duration = end - start + 1

        Am = ear[end] - 2 * ear[index_peak_blink] + ear[start]
        # amplitude of blinks
        Ampl = Am / (end - start)
        # velocity of blinks
        Eye_Open_Speed = (ear[end] - ear[index_peak_blink]) / (end - index_peak_blink)
        Frames_nmbr = np.arange(1, len(ear) + 1)
        # frequency of blinks
        Freq = 100 * (np.arange(1, len(index_peak_blink) + 1) / Frames_nmbr[end])
        feature_blink = np.column_stack((Duration, Ampl, Eye_Open_Speed, Freq))
        model = load_model('./model.h5')
        result_array = model.predict(feature_blink)
        drowsy_array = []
        low_vigilant = []
        for i in range(len(result_array)):

            #print("np.argmax(result_array[i])=")
            #print( result_array[i])
            #print( "--------")
            #print(np.argmax(result_array[i]))

            max = np.argmax(result_array[i])
            if max == 10:
                drowsy_array.append(max)
            elif max == 5:
                low_vigilant.append(max)

        if len(drowsy_array) > 100:
            Final_Result = Final_Result + 10
            COUNT = COUNT + 1
            print("drowsy")
            print(Final_Result/COUNT*10)
            cv2.putText(frame, "drowsy", (300, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        elif len(low_vigilant) > 100:
            Final_Result = Final_Result + 5
            COUNT = COUNT + 1
            print("low vigilant")
            print(Final_Result / COUNT*10)
            cv2.putText(frame, "low vigilant", (300, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            Final_Result = Final_Result + 0
            COUNT = COUNT + 1
            print("alert")
            print(Final_Result / COUNT*10)
            cv2.putText(frame, "alert", (300, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        COUNTER = 0
        EAR = []

    #cv2.imshow(frame)
    key = cv2.waitKey(1) & 0xFF
    if key != 0xFF:
     break
vs.release()

cv2.destroyAllWindows()