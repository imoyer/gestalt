#!/usr/bin/python

import cv
import time
import socket
import sys
import collections

################################################################
# global position

class globalposition:
    def __init__(self):
        self.x = 0 #in
        self.y = 0
        self.z = 0

        # z range for focal stack
        self.zbottom = 0 #in
        self.ztop = 0    #in
        #step size for focal stack
        self.zfstep = 0.0003 #in

        #step size
        self.step = 0.01     #in
        
        # scale 0.01 in == 315 pixels
        self.vieww = 0.015238095 #in
        self.viewh = 0.02031746  #in

        self.scale = 315.0/0.01  #pix/in

        self.screenw = 480 #pix
        self.screenh = 640 #pix

    def reset(self):
        self.x = 0
        self.y = 0
        self.z = 0

    def incx(self, off):
        self.x = self.x + off

    def incy(self, off):
        self.y = self.y + off

    def incz(self, off):
        self.z = self.z + off

################################################################
#get calibration data
i01 = cv.LoadImage('white-calib/calib.png')
passvals = cv.Load('white-calib/passvals.xml')

imin = cv.GetReal1D(passvals,0)
imax = cv.GetReal1D(passvals,1)
pmin = cv.GetReal1D(passvals,2)

#scale = pmin
scale = 100
ofs = 0
off = (-pmin+ofs,-pmin+ofs,-pmin+ofs)
#off = (-imin, -imin, -imin)
#off = (-pmin, -pmin, -pmin)
cv.AddS(i01, off, i01)

################################################################
# setup camera
cv.NamedWindow("camera", 1)
capture = cv.CreateCameraCapture(0)

width = None #leave None for auto-detection
height = None #leave None for auto-detection

if width is None:
    width = int(cv.GetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_WIDTH))
else:
    cv.SetCaptureProperty(capture,cv.CV_CAP_PROP_FRAME_WIDTH,width)    
 
if height is None:  
    height = int(cv.GetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_HEIGHT))
else:
    cv.SetCaptureProperty(capture,cv.CV_CAP_PROP_FRAME_HEIGHT,height) 

################################################################
# read a line from a file/port
def readline(s):
    line = ""
    
    while len(line) == 0 or line[-1] != chr(0x0D):
        line += s.recv(1)
        
    return line.strip()


################################################################
#connect to emc 
def ConnectEMC():

    if(len(sys.argv)==2):
        HOST = sys.argv[1]
    else:
        HOST = 'localhost'
        PORT = 5007

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))

    #say hello
    s.sendall("hello EMC x 1.0\r\n")
    print readline(s)

    #enable control
    s.sendall("set enable EMCTOO\r\n")
    print readline(s)

    #turn off ESTOP
    s.sendall("set estop off\r\n")
    print readline(s)

    #turn on machine
    s.sendall("set machine on\r\n")
    print readline(s)

    #change to manual mode
    s.sendall("set mode manual\r\n")
    print readline(s)

    #change spindle to forward direction
    s.sendall("set spindle forward\r\n")
    print readline(s)

    s.sendall("set echo off\r\n")
    cmd=""
    for i in range(40):
        cmd = cmd + "set spindle increase\r\n"
    s.sendall(cmd)
    time.sleep(0.01)
    for i in range(40):
        readline(s)
    s.sendall("set echo on\r\n")
    print readline(s)

    return s

#################################################
# move to
def MoveMill(x,y,z):
    global gp
    global s
    
    xdiff = x - gp.x
    ydiff = y - gp.y
    zdiff = z - gp.z

    gp.x = x
    gp.y = y
    gp.z = z

    cmd = "set jog incr 0 30 %0.6f\r\nset jog incr 1 30 %0.6f\r\nset jog incr 2 30 %0.6f\r\n" % (xdiff,ydiff,zdiff)
    s.sendall(cmd)
    if(xdiff != 0):
        print readline(s)
    if(ydiff != 0):
        print readline(s)
    if(zdiff != 0):
        print readline(s)

#################################################
# move mill relative
def MoveMillRel(x,y,z):
    global gp
    global s

    gp.incx(x)
    gp.incy(y)
    gp.incz(z)

    cmd = "set jog incr 0 30 %0.6f\r\nset jog incr 1 30 %0.6f\r\nset jog incr 2 30 %0.6f\r\n" % (x,y,z)
    s.sendall(cmd)
    if(x != 0):
        print readline(s)
    if(y != 0):
        print readline(s)
    if(z != 0):
        print readline(s)    

#################################################
# parse key presses
def parsekey(k):
    global step
    global scale
    global ofs
    global off
    global correction
    global lines
    global text
    global gp

    lowbyte = k & 0xff
    specialbit = (k & 0x8000)>0

    if(lowbyte == ord('a') and specialbit == False):
        step = step * 2
        print "step:", step
    elif(lowbyte == ord('z') and specialbit == False):
        step = step / 2
        print "step:", step
    elif(lowbyte == 81 and specialbit == True): #left
        MoveMillRel(step,0,0)
    elif(lowbyte == 83 and specialbit == True): #right
        MoveMillRel(-step,0,0)
    elif(lowbyte == 82 and specialbit == True): #up
        MoveMillRel(0,-step,0)
    elif(lowbyte == 84 and specialbit == True): #dn
        MoveMillRel(0,step,0)
    elif(lowbyte == 85 and specialbit == True): #pgup
        MoveMillRel(0,0,-step)
    elif(lowbyte == 86 and specialbit == True): #pgdn
        MoveMillRel(0,0,step)
    elif(lowbyte == 201 and specialbit == True):  #f12
        cmd = "set spindle increase\r\n"
        s.sendall(cmd)
        print readline(s)
    elif(lowbyte == 200 and specialbit == True):  #f11
        cmd = "set spindle decrease\r\n"
        s.sendall(cmd)
        print readline(s)
    elif(lowbyte == ord('=') and specialbit == False):
        scale = scale + 5
        print "scale:", scale
    elif(lowbyte == ord('-') and specialbit == False):
        scale = scale - 5
        print "scale:", scale
    elif(lowbyte == ord('+') and specialbit == False):
        ofs = ofs + 5
        print "ofs:",ofs
        off = (-pmin+ofs,-pmin+ofs,-pmin+ofs)
        cv.AddS(i01, (5, 5, 5), i01)
    elif(lowbyte == ord('_') and specialbit == False):
        ofs = ofs - 5
        print "ofs:",ofs
        off = (-pmin+ofs,-pmin+ofs,-pmin+ofs)
        cv.AddS(i01, (-5, -5, -5), i01)
    elif(lowbyte == ord('c') and specialbit == False):
        correction = not correction
        print "correction:",correction
    elif(lowbyte == ord('l') and specialbit == False):
        lines = not lines
        print "lines:",lines
    elif(lowbyte == ord('t') and specialbit == False):
        text = not text
        print "text:",text
    elif(lowbyte == ord('w') and specialbit == False):
        avgnimages(il,5,0)
        name = ("%02.3f_%02.3f_%02.3f.jpg") % (gp.x,gp.y,gp.z)
        cv.SaveImage(name,list(il)[0])
        print "wrote ", name


###############################################
# image diff

def difference(il,tol):
    if(len(list(il))<2):
        return True

    i1=list(il)[0]
    i2=list(il)[1]
    temp = cv.CreateImage((i1.width,i1.height),i1.depth,i1.nChannels)
    cv.AbsDiff(i1,i2,temp)
    #cv.ConvertScale(temp,temp,20)
    #cv.ShowImage("difference",temp)
    mean = cv.Avg(temp)
    #cv.SetImageCOI(temp,2)
    #mmlvec = cv.MinMaxLoc(temp)
    #print mean,mmlvec

    mean = (mean[0]+mean[1]+mean[2])/3
    if(mean > tol):
        return True
    return False

################################################
# avg

def avgnimages(il,n,ngood=2):
    global maxlen
    global off
    global scale
    global correction

    if(n>maxlen):
        n = maxlen
        print "Error: avgnimages: n>maxlen"

    for i in range(n-ngood): #capture n more images
        il.appendleft(cv.CreateImage((list(il)[0].width,list(il)[0].height),list(il)[0].depth,list(il)[0].nChannels))
        FormatImage(cv.QueryFrame(capture),list(il)[0],off,scale,correction)

    ideep = cv.CreateImage((list(il)[0].width,list(il)[0].height),cv.IPL_DEPTH_16U,list(il)[0].nChannels)
    cv.SetZero(ideep)
    itmp = cv.CreateImage((list(il)[0].width,list(il)[0].height),cv.IPL_DEPTH_16U,list(il)[0].nChannels)
    for i in range(n):
        cv.Convert(list(il)[i],itmp)
        cv.Add(itmp,ideep,ideep)

    cv.ConvertScale(ideep,list(il)[0],1/float(n))
    #cv.Convert(itmp,list(il)[0])

################################################
# correct image
def FormatImage(img, oimg, off, scale, correction):
    global i01

    #print img.height,img.width
    #print oimg.height,oimg.width
    cv.Transpose(img,oimg)
    cv.Flip(oimg,None,0)

    if(correction):
        cv.AddS(oimg, off, oimg)
        cv.Div(oimg, i01, oimg, scale)

################################################
# line drawing function
def DrawLines(img):
    global step
    global gp

    xtop = 1
    xbot = img.width
    ytop = 1
    ybot = img.height

    midx = gp.vieww/2
    midy = gp.viewh/2

    linex1 = int(gp.scale*(midx-step/2))
    linex2 = int(gp.scale*(midx+step/2))

    liney1 = int(gp.scale*(midy-step/2))
    liney2 = int(gp.scale*(midy+step/2))

    cv.Line(img,(linex1,ytop),(linex1,ybot),(255,128,64,1),1)
    cv.Line(img,(linex2,ytop),(linex2,ybot),(255,128,64,1),1)
    cv.Line(img,(xtop,liney1),(xbot,liney1),(255,128,64,1),1)
    cv.Line(img,(xtop,liney2),(xbot,liney2),(255,128,64,1),1)

################################################
# draw text
def DrawText(img, font):
    global gp
    
    color = (64,128,255,1)

    message = "step = %f" % gp.step
    cv.PutText(img,message,(10,600),font,color)
    message = "x = %02.4f" % gp.x
    cv.PutText(img,message,(10,610),font,color)
    message = "y = %02.4f" % gp.y
    cv.PutText(img,message,(10,620),font,color)
    message = "z = %02.4f" % gp.z
    cv.PutText(img,message,(10,630),font,color)


################################################
# make focal stack
def FocalStack():
    global gp
    global il

    travel = gp.ztop - gp.zbottom
    steps = int(travel/gp.zfstep)


    print "saving focal stack"

    for p in range(steps):
        q = (p*gp.zfstep+gp.zbottom)
        MoveMill(gp.x,gp.y,gp.q)
        #differences
        avgnimages(il,5,5)
        name = ("%02.3f_%02.3f_%02.3f.jpg") % (gp.x,gp.y,gp.z)
        cv.SaveImage(name,list(il)[0])
        print "wrote ", name

################################################
# setup image queue
il = collections.deque(maxlen=5)
maxlen = 5

################################################
# temporary variables
#oimg = cv.CreateImage((i01.height,i01.width),8,3)

################################################
#init status rendering
font = cv.InitFont(cv.CV_FONT_HERSHEY_PLAIN,1,1)

correction = True
lines = True
text = True
gp = globalposition()

s = ConnectEMC()

while True:
    #FIX inefficient
    #il.appendleft(cv.CreateImage((i01.width,i01.height),i01.depth,i01.nChannels))
    #img = list(il)[0]
    #cv.Copy(cv.QueryFrame(capture),img)

    il.appendleft(cv.CreateImage((i01.width,i01.height),i01.depth,i01.nChannels))
    oimg = list(il)[0]
    iimg = cv.QueryFrame(capture)
    FormatImage(iimg,oimg,off,scale,correction)

    #s.sendall("get pos_offset X\r\nget pos_offset Y\r\nget pos_offset Z\r\nget pos_offset R\r\n")

    #x = readline(s)
    #y = readline(s)
    #z = readline(s)
    #r = readline(s)

    #cv.PutText(oimg,x,(10,590),font,color)
    #cv.PutText(oimg,y,(10,600),font,color)
    #cv.PutText(oimg,z,(10,610),font,color)
    #cv.PutText(oimg,r,(10,620),font,color)

    if(lines):
        DrawLines(oimg)
        
    if(text):
        DrawText(oimg, font)

    #difference(il,15)

    cv.ShowImage("camera", oimg)
    k = cv.WaitKey(10)
    if (k & 0xff == ord('q')):
        break
    if(k>0):
        parsekey(k)

s.close()
