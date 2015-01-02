import cv2.cv as cv
import sys
import time
import random

if __name__ == '__main__':
	# setup camera
	capture = cv.CaptureFromCAM(1)
	while True:
		print "yes here"
		img = cv.QueryFrame(capture)
		time.sleep(1)
		try:
			cv.SaveImage("hi"+str(random.random())[2:]+".jpeg", img)
		except:
			print "whatever"
		cv.ShowImage("camera", img)
		if cv.WaitKey(10) == 27:
			break
