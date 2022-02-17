from threading import Thread
from lib.widget import Widget

import cv2
import mediapipe as mp
from math import sqrt
from time import sleep, time
import numpy as np

cap = cv2.VideoCapture(0)
#cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands()
mp_draw = mp.solutions.drawing_utils

def calc_avgs(point_indices, landmarks):
    x_total = 0
    y_total = 0
    z_total = 0
    for index in point_indices:
        point = landmarks[index]
        x_total += point.x
        y_total += point.y
        z_total += point.z
    return x_total/len(point_indices), y_total/len(point_indices), z_total/len(point_indices)


# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# s.connect(("192.168.1.3",8080))
def clip(x, a, b, c, d, do_round=True):
    if c > d:
        a, b = b, a
        c, d = d, c
    out = (x - a) / (b-a) * (d-c) + c
    # clip out between c and d
    out = min(d, max(c, out))   
    if do_round:
        out = round(out, 2)
    return out 

def sgn(x):
    if x < 0:
        return -1
    return 1

def calc_curve(landmarks):
    vectors = []
    last_lm = None
    for lm in landmarks:
        if last_lm is not None:
            vectors.append([last_lm.x - lm.x, last_lm.y - lm.y, last_lm.z - lm.z])
            #print([vectors[-1]])
        last_lm = lm

    dot_total = 0

    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            x1, y1, z1 = vectors[i]
            x2, y2, z2 = vectors[j]
            dot = x1 * x2 + y1 * y2 + z1 * z2
            this_mag = sqrt(x1**2 + y1**2 + z1**2)
            last_mag = sqrt(x2**2 + y2**2 + z2**2)
            fixed_dot = dot/this_mag/last_mag
            dot_total += fixed_dot
    return dot_total / (len(landmarks) - 1)


class HandTracking(Widget):
    def setup(self):
        self.running = True
        Thread(target=self.main, daemon=True).start()

    def main(self):
        x_avg, y_avg, z_avg = None, None, None
        x_vel_sgn_count = 0
        x_vel_sgn = 0
        y_vel_sgn_count = 0
        y_vel_sgn = 0
        x_vel_avg, y_vel_avg = 0, 0
        factor = .5
        start = time()
        while True:
            _, img = cap.read()
            imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = hands.process(imgRGB)
            # print("[INFO] handmarks: {}".format(results.multi_hand_landmarks))

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    index = 0
                    for lm in hand_landmarks.landmark:
                        height, width, channel = img.shape
                        cx, cy = int(lm.x * width), int(lm.y * height)
                        col = min(255, max(index-5, 0) * 40)
                        cv2.circle(img, (cx, cy), 10, (col, col, col), cv2.FILLED)
                        index += 1
                    mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                #print(results.multi_hand_landmarks)
                landmarks = results.multi_hand_landmarks[0].landmark

                
                avgs = calc_avgs([0, 5, 9, 13, 17], landmarks)
                x = avgs[0]
                y = avgs[1]
                lm1 = landmarks[0]
                def calc_dist(lm1, lm2):
                    return sqrt((lm1.x - lm2.x)**2 + (lm1.y - lm2.y)**2 + (lm1.z - lm2.z)**2)
                z = calc_dist(lm1, landmarks[5]) + calc_dist(lm1, landmarks[17])
                curve = sum(calc_curve(landmarks[4*i + 5: 4*i+9]) for i in range(4)) / 4


                if x_avg is None:
                    x_avg = x
                    y_avg = y
                    z_avg = z
                else:
                    '''
                    other_factor = .3
                    x_vel = x - x_avg
                    y_vel = y - y_avg
                
                    x_vel_avg = x_vel * factor + x_vel_avg * (1- other_factor)
                    y_vel_avg = y_vel * factor + y_vel_avg * (1- other_factor)
                    if sgn(x_vel) == x_vel_sgn:
                        x_vel_sgn_count += 1
                    else:
                        x_vel_avg = 0
                        x_vel_sgn_count = 0

                    if sgn(y_vel) == y_vel_sgn:
                        y_vel_sgn_count += 1
                    else:
                        y_vel_avg = 0
                        y_vel_sgn_count = 0
                    '''

                    x_avg = x * factor + x_avg * (1 - factor)
                    y_avg = y * factor + y_avg * (1 - factor)
                    z_avg = z * factor + z_avg * (1 - factor)

                #lookahead=0
                #use_x, use_y, use_z = x_avg + x_vel_avg*lookahead, y_avg+y_vel_avg*lookahead, z_avg
                
                #print(curve)
                pos = [clip(1/z_avg, 2, 5, 0, 30), clip(x_avg, .1, .95, -30, 30), clip(y_avg, .1, .85, 10, 140)]
                curve = clip(curve, .2, 1, 100, 0)
                #pos = [clip(z_avg, .1, .05, 0, 30), clip(x_avg, .1, .95, -30, 30), clip(y_avg, 0, 1, 10, 140)]
                #print(30*(1-point.y), 60*(.5-point.x), point.z)
                #pos = ','.join(map(str, pos))
                try:
                    self.control.move(x=pos[0], y=pos[1], z=pos[2], e=curve)
                except:
                    print('OOF')
                # sleep(.025)
                #print(time() - start)
                start = time()
            img = cv2.flip(img, 1)
            cv2.imshow("Image", img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break