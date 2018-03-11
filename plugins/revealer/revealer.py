'''
Revealer
secret back-up solution

features:
    - Analog multi-factor backup solution
    - Safety - One time pad security
    - Redundancy - Trustless printing & distribution
    - Multiple wallets seeds can be encrypted for the same revealer*
    - Encrypt any secret you want for your revealer
    - Based on crypto by legendary cryptographers Naor and Shamir  

Tiago Romagnani Silveira, 2017


'''
from __future__ import division
import os 
import sys
import random
import qrcode
from electrum_gui.qt.qrwindow import MONOSPACE_FONT
from electrum.plugins import BasePlugin, hook
from PyQt5.QtCore import *
from PyQt5.QtGui import *
#from PyQt5.QtX11Extras import QX11Info 
from PyQt5.QtPrintSupport import QPrinter
from hashlib import sha256
from electrum import mnemonic    
from PIL.ImageQt import ImageQt

class RevealerPlugin(BasePlugin):

    def __init__(self, parent, config, name):
        BasePlugin.__init__(self, parent, config, name)
        self.calibration_h = self.config.get('calibration_h')
        self.calibration_v = self.config.get('calibration_v')
        self.size = (152,96) #(230,124) (ceramic glass)
        self.base_dir = config.electrum_path()+'/revealer/'
        if not os.path.exists(self.base_dir):
            os.mkdir(self.base_dir)

    def update_wallet_name (self, name):
        self.base_name = self.base_dir + str(name)

    def seed_img(self, is_seed = True):
      
        if not self.cseed and self.txt == False:
            return
        
        if is_seed:
            txt = self.cseed
        else:
            txt = self.txt

        img = QImage(self.size[0],self.size[1], QImage.Format_Mono)
        bitmap = QBitmap.fromImage(img, Qt.MonoOnly)
        bitmap.fill(Qt.white)
        painter = QPainter()
        painter.begin(bitmap)

        QFontDatabase.addApplicationFont(os.path.abspath('plugins/revealer/SourceSansPro-Black.otf'))
        font = QFont('Source Sans Pro', 12, QFont.Black)
        font.setLetterSpacing(QFont.PercentageSpacing, 97) 
        painter.setFont(font)
        seed_array = txt.split(' ')
        
        ''' 
        #in case one needs only 4 letters for longer seeds or bigger letters
        
        for i, sw in enumerate(seed_array):
            if len(sw)>4:
                seed_array[i] = sw[:4]
        
        '''

        #limit lines to 3 words and 17 char        
        for n in range(6):
            nwords = 3
            temp_seed = seed_array[:nwords]
            if len(' '.join(map(str, temp_seed))) > 17:
               nwords = 2
               temp_seed = seed_array[:nwords]
            painter.drawText(QRect(0, 1+((font.pointSize()+3)*n) , self.size[0], self.size[1]), Qt.AlignHCenter, ' '.join(map(str, temp_seed)))
            del seed_array[:nwords]

        painter.end()
        img = bitmap.toImage()
        
        try:
            self.rawnoise
            
        except:
            self.make_rawnoise()
            
        self.make_cypherseed(img, self.rawnoise, False, is_seed)
        return img        
    
    def make_rawnoise(self):
        #check for custom noise file
        if os.path.isfile(self.base_name+'_rawnoise.tif'): 
            self.rawnoise = QImage(self.base_name+'_rawnoise.tif')
        else:
            w = self.size[0]
            h = self.size[1]
            rawnoise = QImage(w, h, QImage.Format_Mono)
            
            try:
                self.noise_seed
            except:
                self.noise_seed = random.SystemRandom().getrandbits(128)
            else:
                self.noise_seed = int(self.noise_seed, 16)

            self.hex_noise = format(self.noise_seed, '02x')
            self.hex_noise = ' '.join(self.hex_noise[i:i+4] for i in range(0,len(self.hex_noise),4))                     
            random.seed(self.noise_seed)
            
            for x in range(w):
                for y in range(h):
                    rawnoise.setPixel(x,y,random.randint(0, 1))

            #rawnoise.save(self.base_name+'rawnoise.tif') 
            self.rawnoise = rawnoise 
            self.make_revealer()
        return 
   
    def make_revealer(self):
        revealer = self.pixelcode_2x2(self.rawnoise)
        revealer.invertPixels()
        revealer = QBitmap.fromImage(revealer).scaled(self.size[0]*6.68, self.size[1]*6.68)
        revealer = self.overlay_marks(revealer)
        revealer = self.draw_code(revealer, self.hex_noise)
        #revealer = QImage(revealer).mirrored(True, False)
        revealer = revealer.scaled(revealer.width()*2, revealer.height()*2)
        revealer.save(self.base_name+'_revealer.png')
        self.revealer = revealer
        #self.demo()
        return

    def make_cypherseed(self, img, rawnoise, calibration=False, is_seed = True):
        img = img.convertToFormat(QImage.Format_Mono)
        p = QPainter()
        p.begin(img)
        p.setCompositionMode(26) #xor
        p.drawImage(0, 0, rawnoise)
        p.end()
        cypherseed = self.pixelcode_2x2(img)
        cypherseed = QBitmap.fromImage(cypherseed).scaled(self.size[0]*6.68, self.size[1]*6.68)
        cypherseed = self.overlay_marks(cypherseed, True, calibration)
        cypherseed = cypherseed.scaled(cypherseed.width()*2, cypherseed.height()*2)
        if not is_seed:
            self.filename = '_custom_text'
        else:
            self.filename = '_cypherseed'
            
        if not calibration:
            self.toPdf(QImage(cypherseed))
            cypherseed.save(self.base_name+self.filename+'.png')
            QDesktopServices.openUrl (QUrl.fromLocalFile(os.path.abspath(self.base_name+self.filename+'.pdf')))
            
        return cypherseed

    def demo(self):

        img = QImage(self.size[0],self.size[1], QImage.Format_Mono)
        bitmap = QBitmap.fromImage(img, Qt.MonoOnly)
        bitmap.fill(Qt.white)
        painter = QPainter()
        painter.begin(bitmap)
        font = QFont('Din Trek', 9)#
        painter.setFont(font)
        txt = 'REVEALER  REVEALER  REVEALER  REVEALER  REVEALER  REVEALER \n'*5
        painter.drawText(QRect(0, 0 , self.size[0], self.size[1]), Qt.AlignHCenter, txt)
        painter.end()
        img = bitmap.toImage()
        img = self.make_cypherseed(img, self.rawnoise, True)
        self.calibration_pdf(img)
        QDesktopServices.openUrl (QUrl.fromLocalFile(os.path.abspath(self.base_dir+'calibration.pdf')))
        return img        
    
    def toPdf(self, image, n=0):
        printer = QPrinter()
        printer.setPaperSize(QSizeF(210, 297), QPrinter.Millimeter);
        printer.setResolution(600)
        printer.setPageMargins(0,0,0,0, QPrinter.Millimeter)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(self.base_name+self.filename+'.pdf')
        printer.setPageMargins(0,0,0,0,6)
        painter = QPainter()
        painter.begin(printer)

        w = int(4958/13)
        h = int(7017/13)
        
        size_h = 2022+int(self.calibration_h) 
        size_v = 1274+int(self.calibration_v)

        image =  image.scaled(size_h, size_v)

        for n in range(3):
            painter.fillRect(0, (n*(7017/3)), 4958, 33, Qt.black )
            painter.fillRect(0, (n*(7017/3))+3, 4958, 27, Qt.white )
            painter.drawImage(553,(n*(7017/3))+533, image)
            wpath = QPainterPath()
            wpath.addRoundedRect(QRectF(548,(n*(7017/3))+528, size_h+5, size_v+5), 19, 19)
            painter.setPen(QPen(Qt.black, 10))
            painter.drawPath(wpath)
        
       
        
        '''
        master public key
        qr_mpk = qrcode.make(self.mpk[0])#
        painter.drawImage(3453,933, ImageQt(qr_mpk))

        painter.setFont(QFont('Din Trek', 18, QFont.Black))
        pen = QPen(Qt.black, 127)
        painter.setPen(pen)

        painter.fillRect(0, 133+(n*(7017/4)), w, 173, Qt.black )
        painter.fillRect(0, 133+(n*(7017/4))+3, w-3, 167, Qt.white )
        painter.drawText(177, 266 + (n*(7017/4)), 'R')
        '''
                                    

        painter.end()
    
    def calibration_pdf(self, image):
        printer = QPrinter()
        printer.setPaperSize(QSizeF(210, 297), QPrinter.Millimeter);
        printer.setResolution(600)
        printer.setPageMargins(0,0,0,0, QPrinter.Millimeter)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(self.base_dir+'calibration.pdf')
        painter = QPainter()
        painter.begin(printer)
        image =  image.scaled(self.size[0]*6.68,self.size[1]*6.68)
        #tuning
        font = QFont('Source Sans Pro', 27, QFont.Black)
        painter.setFont(font)
        
        cal_value = 0
        for p in range (1,2):
            for x in range (2):
                for n in range(5):
                    cal_value+=1
                    painter.drawImage(254+(x*2296),130+(n*1326),image.scaled(2022+cal_value,1274+cal_value))
                    painter.drawText(354+(x*2296),270+(n*1326), str(cal_value))
                    
            printer.newPage()
        painter.end()

    def overlay_marks(self, img, is_cseed=False, calibration_sheet=False):
        base_img = QImage(img.width(), img.height(), QImage.Format_ARGB32 )
        base_img.fill(Qt.white)
        img = QImage(img)
        
        painter = QPainter()
        painter.begin(base_img)
        self.abstand_h = 17#higher values smaller distances
        self.abstand_v = 24
        line_distance_v = (img.width()/self.abstand_v)/2
        line_distance_h = (img.width()/self.abstand_h)/2
        painter.drawImage(img.width()/self.abstand_v,img.height()/self.abstand_h,img.scaled(img.width()-(2*(img.width()/self.abstand_v)), img.height()-(2*(img.height()/self.abstand_h))))#

        pen = QPen(Qt.black, 1)
        painter.setPen(pen)
        
        exp_base = 1.5
        #vertical lines
        for x in range (7,21):
            yexp = (img.height()/self.abstand_h)-4 + exp_base**x # 
            painter.drawLine(0, yexp, (img.width()/self.abstand_v), yexp)
            painter.drawLine(img.width(), img.height()-yexp, img.width()-(img.width()/self.abstand_v), img.height()-yexp)

        pen = QPen(Qt.black, 1)
        painter.setPen(pen)
      
        #horizontal lines
        for y in range (7,21):
            xexp = (img.width()/self.abstand_v)-4 + exp_base**y# 
            painter.drawLine(xexp, img.height()/self.abstand_h, xexp, 0)
            painter.drawLine(img.width()-xexp, img.height()-(img.height()/self.abstand_h), img.width()-xexp, img.height())


        #frame around image        
        pen = QPen(Qt.black, 5)
        painter.setPen(pen)
        #horz
        painter.drawLine(0, img.height()/self.abstand_h, img.width(), img.height()/self.abstand_h)
        painter.drawLine(0, img.height()-(img.height()/self.abstand_h), img.width(), img.height()-(img.height()/self.abstand_h))
        #vert
        painter.drawLine(img.width()/self.abstand_v, 0,  img.width()/self.abstand_v, img.height())
        painter.drawLine(img.width()-(img.width()/self.abstand_v), 0,  img.width()-(img.width()/self.abstand_v), img.height())
        
       
        
        #     
        pen = QPen(Qt.white, 3)
        painter.setPen(pen)
        
        #horz
        painter.drawLine(0, img.height()/self.abstand_h, img.width(), img.height()/self.abstand_h)
        painter.drawLine(0, img.height()-(img.height()/self.abstand_h), img.width(), img.height()-(img.height()/self.abstand_h))
        
        #vert
        painter.drawLine(img.width()/self.abstand_v, 0,  img.width()/self.abstand_v, img.height())
        painter.drawLine(img.width()-(img.width()/self.abstand_v), 0,  img.width()-(img.width()/self.abstand_v), img.height())


        #border around img
        Rpath = QPainterPath()
        Rpath.addRect(QRectF((img.width()/self.abstand_v)+2, (img.height()/self.abstand_h)+2, img.width()-((img.width()/self.abstand_v)*2)-5, (img.height()-((img.height()/self.abstand_h))*2)-5))
        
        pen = QPen(Qt.white, 2)
        painter.setPen(pen)
        painter.drawPath(Rpath);

        Bpath = QPainterPath()
        Bpath.addRect(QRectF((img.width()/self.abstand_v)+3, (img.height()/self.abstand_h)+3, img.width()-((img.width()/self.abstand_v)*2)-7, (img.height()-((img.height()/self.abstand_h))*2)-7))
        
        pen = QPen(Qt.black, 1)
        painter.setPen(pen)
        painter.drawPath(Bpath);

        if not calibration_sheet:
            if is_cseed:
                painter.drawImage(img.width()-133,img.height()-121, QImage(':icons/electrumb.png').scaledToWidth(self.abstand_v*3.3, Qt.SmoothTransformation))
    
            else: # revealer
    
                painter.setPen(QPen(Qt.white, 7))
                painter.drawLine(0, (img.height()/self.abstand_h)/2, img.width(), (img.height()/self.abstand_h)/2)
                painter.drawLine((img.width()/self.abstand_v)/2, 0,  (img.width()/self.abstand_v)/2, img.height())
                painter.drawLine(0, img.height()-((img.height()/self.abstand_h)/2), img.width(), img.height()-((img.height()/self.abstand_h)/2))
                painter.drawLine(img.width()-((img.width()/self.abstand_v)/2), 0,  img.width()-((img.width()/self.abstand_v)/2), img.height())
                
                painter.drawImage(((img.width()/self.abstand_v))+13, ((img.height()/self.abstand_h))+13, QImage(':icons/revealer.png').scaledToWidth(1.5*(img.width()/self.abstand_v)), Qt.SmoothTransformation)

        #black lines in the middle of border        
        
        painter.setPen(QPen(Qt.black, 1))
        painter.drawLine(0, (img.height()/self.abstand_h)/2, img.width(), (img.height()/self.abstand_h)/2)
        painter.drawLine((img.width()/self.abstand_v)/2, 0,  (img.width()/self.abstand_v)/2, img.height())
        painter.drawLine(0, img.height()-((img.height()/self.abstand_h)/2), img.width(), img.height()-((img.height()/self.abstand_h)/2))
        painter.drawLine(img.width()-((img.width()/self.abstand_v)/2), 0,  img.width()-((img.width()/self.abstand_v)/2), img.height())
            
        painter.end()
        return base_img
    
    def draw_code(self, img, code='NO CODE'):	
        painter = QPainter()
        painter.begin(img)
        #print code
        
        painter.setPen(QPen(Qt.white, 30))
        painter.drawLine(img.width()-61, img.height()-41, img.width()+102-(7*img.width()/8), img.height ()-41)
        
        QFontDatabase.addApplicationFont(os.path.abspath('plugins/revealer/SourceSansPBlack.otf'))
        font = QFont('Source Sans Pro', 30, QFont.Black)
        painter.setFont(font)
        painter.setPen(QColor(0,0,0,255))
        painter.drawText(QRect(0, img.height()-67, img.width()-56, img.height()-67), Qt.AlignRight, code)
        
        #draw qr code 
        #target = QRectF(img.width()-98, img.height()-98, 88, 88);
        #source = QRectF(0.0, 0.0, self.qr_noise.width(), self.qr_noise.height());
        #painter.drawImage(target, self.qr_noise, source);
        painter.end()
        return img

    def pixelcode_2x2(self, img):
        result = QImage(img.width()*2, img.height()*2, QImage.Format_ARGB32 )
        white = qRgba(255,255,255,0)
        black = qRgba(0,0,0,255)

        for x in range(img.width()):
            for y in range(img.height()):
                c = img.pixel(QPoint(x,y))
                colors = QColor(c).getRgbF()
                if colors[0]:
                    
                    result.setPixel(x*2+1,y*2+1, black)
                    result.setPixel(x*2,y*2+1, white)
                    result.setPixel(x*2+1,y*2, white)
                    result.setPixel(x*2, y*2, black)
                    
                else:
                    
                    result.setPixel(x*2+1,y*2+1, white)
                    result.setPixel(x*2,y*2+1, black)
                    result.setPixel(x*2+1,y*2, black)
                    result.setPixel(x*2, y*2, white)
                 
        return result
    
    
'''
previous numpy implementations for reference, also from the other schemes..  

def pixelcode_2x2(img, share, c_matrix=None):
    
      
    maxX, maxY = img.shape
    result = np.zeros((2*maxX, 2*maxY), dtype=bool)

    d = np.zeros((3,2,2,2), dtype=bool)
    #3 types of 4x4 matrixes, repeating creates white, using the second variation black
    d[0][0] = np.matrix('1 1 ; 0 0')
    d[0][1] = np.matrix('0 0 ; 1 1')
    
    d[1][0] = np.matrix('0 1 ; 0 1')
    d[1][1] = np.matrix('1 0 ; 1 0')
    
    d[2][0] = np.matrix('0 1 ; 1 0')
    d[2][1] = np.matrix('1 0 ; 0 1')
    print d

    maxX, maxY = img.shape
    result = d[0][0]
    row=np.zeros((2, (maxY*2)+2))
    if c_matrix == None:
        c_matrix = np.zeros((maxX,maxY))
        
    for x in range(maxX):
        for y in range(maxY):
            if share ==0:
                dn = np.random.randint(0,3)
                c_matrix[x,y] = dn
            else:
                dn = c_matrix[x,y] 
            zo= share
            #for the plain diagonal mode dn=2 , vertical dn = 1,  horinzontal dn = 0, unset = random variations
            #dn = 2 
            if img[x,y]:
                result = np.bmat([result, d[dn][zo]])
            else:
                result = np.bmat([result, d[dn][not zo]])
                
      #  print (result.shape, row.shape)
        row = np.bmat('row; result')  
        result = d[0][0]    
    
    if share == 0:
        return row, c_matrix
    else:
        return row


def print_mat(m):
    for row in m:
        print row


def pixelcode_3x3(img):

    # 3 x 3 solution
    
    m0 = np.matrix('0 0 1 1; 0 1 0 1; 0 1 1 0')
    m1 = np.matrix('1 1 0 0; 1 0 1 0; 1 0 0 1')

    #adds a wite pixel and pixelcodes each row, then stacks them up.
    maxX, maxY = img.shape
    result = m0
    row=np.zeros((3, (maxY*4)+4))
    for x in range(maxX):
        for y in range(maxY):
            if img[x,y]:
                #for id in range (3):
                result = np.bmat([result, np.random.permutation(m0)])
            else:
                result = np.bmat([result, np.random.permutation(m1)])
        print (result.shape, row.shape)
        row = np.bmat('row; result')  
        result = m0    
    return row
    
    

def pixelcode_2x4(img, iteration):
    white = np.zeros((4,3, 3))
    white[1] = np.matrix('0 1 1; 1 1 1; 0 0 0')
    white[2] = np.matrix('0 1 0; 1 1 0; 0 1 1')
    white[3] = np.matrix('0 0 1; 1 1 0; 1 0 1')
    white[0] = np.matrix('0 0 0; 1 1 1; 1 1 0')

    black = np.zeros((4, 3, 3))
    black[1] = np.matrix('0 1 1; 0 1 1; 0 1 0')
    black[2] = np.matrix('0 1 0; 1 1 1; 0 0 1')
    black[3] = np.matrix('0 1 0; 1 1 0; 1 1 0')
    black[0] = np.matrix('1 0 0; 1 1 1; 0 1 0')
    
    maxX, maxY = img.shape
    result = black[0]
    row=np.zeros((3, (maxY*3)+3))
    b = np.random.random_integers(0,3)
    w = np.random.random_integers(0,3)
    preto = np.random.permutation(black[iteration])
    branco = np.random.permutation(white[3 -iteration])
    for x in range(maxX):
        for y in range(maxY):
            if img[x,y]:    
                result = np.bmat([result, preto])
            else:
                result = np.bmat([result, branco])
        #print (result.shape, row.shape)
        row = np.bmat('row; result')  
        result = black[0]
    print b    
    return row


def pixelcode_bias(img, bias1, bias2, share, c_matrix=None):
    scipy.misc.imsave(str(share)+"original.tif", img)
    #bias image must be the size of the original image.

    
"""
    #this version fails because permutations cannot be random (?)
    white = np.zeros((3,2, 2))
    white[0] = np.matrix('0 0; 1 1')
    white[1] = np.matrix('1 0; 1 0')
    white[2] = np.matrix('1 0; 1 1') #bias black share

    black = np.zeros((4, 2, 2))
    black[0] = np.matrix('0 0; 1 1')
    black[1] = np.matrix('1 1; 0 0')
    black[2] = np.matrix('1 1; 1 0') #bias black share
    black[3] = np.matrix('0 1; 1 1') #bias black share



    if share==0:
        white_white = white[0]
        white_black = white[2]
        black_white = black[1]
        black_black = black[3]
    else:
        white_white = white[1]
        white_black = white[2]
        black_white = black[0]
        black_black = black[2]

    white_black = np.random.permutation(white[2])
    black_white = np.random.permutation(black[np.random.random_integers(0,1)])
    black_black = np.random.permutation(black[np.random.random_integers(2,3)])
    
    if share==0:
        white_white = np.random.permutation(white[0])
        white_black = np.random.permutation(white[2])
        black_white = np.random.permutation(black[1])
        black_black = np.random.permutation(black[3])
    else:
        white_white = np.random.permutation(white[1])
        white_black = np.random.permutation(white[2])
        black_white = np.random.permutation(black[0])
        black_black = np.random.permutation(black[2])

   """

    d = np.zeros((6,2,2,2), dtype=bool)
    #6 types of 4x4 matrixes, repeating creates white, using the second variation black

    ##WHITE RESULT
    #two white bias shares
    d[0][0] = np.matrix('0 0; 1 1')
    d[0][1] = np.matrix('1 0; 1 0')
    #black and white bias shares
    d[1][0] = np.matrix('0 0; 1 1')
    d[1][1] = np.matrix('1 0; 1 1')
    #two black bias shares 
    d[2][0] = np.matrix('1 0; 1 1')
    d[2][1] = np.matrix('1 0; 1 1')
    
    ##BLACK RESULT
    #two white bias shares
    d[3][0] = np.matrix('0 0; 1 1')
    d[3][1] = np.matrix('1 1; 0 0')
    #black and white bias shares
    d[4][0] = np.matrix('0 0; 1 1')
    d[4][1] = np.matrix('1 1; 1 0')
    #two black bias shares 
    d[5][0] = np.matrix('0 1; 1 1')
    d[5][1] = np.matrix('1 1; 1 0')
    
            
    
    maxX, maxY = img.shape
    result = d[5][1]
    row=np.zeros((2, (maxY*2)+2))

    if c_matrix == None:
        c_matrix = np.zeros((maxX,maxY))
    
    #print img
    #print bias
    for x in range(maxX):
        for y in range(maxY):
            if share ==0:
                dn = np.random.randint(0,2)
                c_matrix[x,y] = dn
            else:
                dn = not c_matrix[x,y] 
                
            if img[x,y]:
            
                if bias1[x,y] and bias2[x,y]:
                    result = np.bmat([result, d[5][dn]])
            
                elif bias1[x,y] and not bias2[x,y]:
                    if not share:
                        result = np.bmat([result, d[4][1]])
                    else:
                        result = np.bmat([result, d[4][0]])
                elif not bias1[x,y] and bias2[x,y]:
                    if share:
                        result = np.bmat([result, d[4][1]])
                    else:
                        result = np.bmat([result, d[4][0]])
                    
                elif not bias1[x,y] and not bias2[x,y]:
                    result = np.bmat([result, d[3][dn]])
            else:
                if bias1[x,y] and bias2[x,y]:
                    result = np.bmat([result, d[2][dn]])
                elif bias1[x,y] and not bias2[x,y]:
                    if not share:
                        result = np.bmat([result, d[1][1]])
                    else:     
                        result = np.bmat([result, d[1][0]])

                elif not bias1[x,y] and bias2[x,y]:
                    if share:
                        result = np.bmat([result, d[1][1]])
                    else:     
                        result = np.bmat([result, d[1][0]])
               
                elif not bias1[x,y] and not bias2[x,y]:
                    result = np.bmat([result, d[0][dn]])
                    
                    
                    
        #print (result.shape, row.shape)
        
        row = np.bmat('row; result')  
        result = d[5][1]
    if share == 0:
        return row, c_matrix
    else:
        return row
    
    return result
    '''
