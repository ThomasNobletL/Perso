# -*- coding: utf-8 -*-
"""
Created on Fri Mar  8 05:03:36 2024

@author: Thomas
"""
import random
from PyQt6 import QtCore
from PyQt6.QtCore import QThread,QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.uic import loadUi
import sys
import numpy as np

class GenSign(QMainWindow):
    def __init__(self):
        super(GenSign, self).__init__()
        
        loadUi("TestGen.ui", self)
        self.setWindowTitle("TestImage")
        
        
        self.pixels_number=1024
        self.pixels_number+=2
        self.sampling_frequency=250000
        self.time_per_pixel = 4 / 1000000
        self.samples_per_step = int(self.time_per_pixel * self.sampling_frequency)
        self.min_tension=-10
        self.max_tension=10
        
        
        self.show()
        self.init_ui()
        
        
    def init_ui(self):
        
        self.Normal.clicked.connect(self.normal)
        self.Triangle.clicked.connect(self.triangle)
        self.Videor.clicked.connect(self.togglevideo)
        self.Quit.clicked.connect(self.close)
        
        self.video_in_progress = False
        self.timer=QTimer()
        self.timer.timeout.connect(self.VideoR)
    
    def togglevideo(self):
        if not self.video_in_progress:
            self.startvideo()
        else:
            self.stopvideo()
    
    def startvideo(self):
       self.video_in_progress = True
       self.Videor.setText('Arrêter')
       self.timer.start(100)     
       
    def stopAction(self):
        self.video_in_progress = False
        self.Videor.setText('Lancer')
        self.timer.stop()  
        
    def normal(self):
        horizontal_staircase = np.repeat(np.linspace(self.min_tension,self. max_tension, self.pixels_number), self.samples_per_step)
        complete_horizontal_staircase = np.tile(horizontal_staircase, self.pixels_number)
        
        
        complete_horizontal_staircase = (complete_horizontal_staircase * 255/(self.max_tension-self.min_tension)).astype(np.uint8)
        height, width = 1024,1024
        qimageh = QImage(
            complete_horizontal_staircase.data, width, height, -1, QImage.Format.Format_Grayscale8
        )
        pixmaph = QPixmap.fromImage(qimageh)
        pixmaph = pixmaph.scaled(self.labelh.width(), self.labelh.height(), Qt.AspectRatioMode.KeepAspectRatio)
        self.labelh.setPixmap(pixmaph)
        self.repaint()
        
        
        vertical_staircase = np.repeat(np.linspace(self.max_tension, self.min_tension, self.pixels_number),
                                   self.samples_per_step * self.pixels_number)
        vertical_staircase = (vertical_staircase * 255/(self.max_tension-self.min_tension)).astype(np.uint8)
        qimagev = QImage(
            vertical_staircase.data, width, height, -1, QImage.Format.Format_Grayscale8
        )
        pixmapv = QPixmap.fromImage(qimagev)
        pixmapv = pixmapv.scaled(self.labelv.width(), self.labelv.height(), Qt.AspectRatioMode.KeepAspectRatio)
        self.labelv.setPixmap(pixmapv)
        self.repaint()
        
    def triangle(self):
        
        horizontal_staircase = np.repeat(np.append(np.linspace(self.min_tension,self. max_tension, self.pixels_number), 
                                         np.linspace(self.max_tension,self. min_tension, self.pixels_number)), self.samples_per_step)
        
        complete_horizontal_staircase = np.tile(horizontal_staircase, self.pixels_number//2)
        
        
        complete_horizontal_staircase = (complete_horizontal_staircase * 255/(self.max_tension-self.min_tension)).astype(np.uint8)
        height, width = 1024,1024
        qimageh = QImage(
            complete_horizontal_staircase.data, width, height, -1, QImage.Format.Format_Grayscale8
        )
        pixmaph = QPixmap.fromImage(qimageh)
        pixmaph = pixmaph.scaled(self.labelh.width(), self.labelh.height(), Qt.AspectRatioMode.KeepAspectRatio)
        self.labelh.setPixmap(pixmaph)
        self.repaint()
        
        
        vertical_staircase = np.repeat(np.linspace(self.max_tension, self.min_tension, self.pixels_number),
                                   self.samples_per_step * self.pixels_number)
        vertical_staircase = (vertical_staircase * 255/(self.max_tension-self.min_tension)).astype(np.uint8)
        qimagev = QImage(
            vertical_staircase.data, width, height, -1, QImage.Format.Format_Grayscale8
        )
        pixmapv = QPixmap.fromImage(qimagev)
        pixmapv = pixmapv.scaled(self.labelv.width(), self.labelv.height(), Qt.AspectRatioMode.KeepAspectRatio)
        self.labelv.setPixmap(pixmapv)
        self.repaint()
    
    def VideoR(self):   
        
        self.VideoRthread = VideoR_thread()
        self.VideoRthread.image.connect(self.displayImage)
        self.VideoRthread.finished.connect(self.thread_cleanup)
        self.VideoRthread.start()
        
        
    def thread_cleanup(self):
        sender = self.sender()  # Retrieves the object that emitted the signal (in this case, the finished thread)
        if sender:
            sender.deleteLater()
            
    def displayImage(self,np_image):
        min_val = np_image.min()
        max_val = np_image.max()
        pixels_number=256
        if max_val > min_val:
            np_image = ((np_image - min_val) / (max_val - min_val)) * 255
            np_image = np_image.astype(np.uint8)

        self.currentImage = np_image   # Useful to save the image

        stride = pixels_number  # Number of bytes per line for a grayscale image
        qImage = QImage(np_image.data, pixels_number, pixels_number, stride, QImage.Format.Format_Grayscale8)
        pixmap = QPixmap.fromImage(qImage)
        pixmap = pixmap.scaled(self.labelhvid.width(), self.labelhvid.height(),
                                   Qt.AspectRatioMode.KeepAspectRatio)
        self.labelhvid.setPixmap(pixmap)
        self.repaint()
        
class VideoR_thread (QThread):
    errorOccurred = QtCore.pyqtSignal(str) 
    image = QtCore.pyqtSignal(np.ndarray)
    
    def __init__(self,parent=None):
        super(VideoR_thread, self).__init__(parent)
        
    def run(self):
        try:
            data = [random.random() for i in range( 256**2)]
            image_array = np.array(data).reshape(256, 256)
            self.image.emit(image_array)
        except Exception as e:
            self.errorOccurred.emit(str(e))
    
def main():
    app = QApplication(sys.argv)
    window = GenSign()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()