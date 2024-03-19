# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 14:39:52 2024

@author: tp_tp4
"""
import sys
import nidaqmx
from PyQt6 import QtCore, QtWidgets, uic
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from nidaqmx.constants import AcquisitionType, TerminalConfiguration, Edge
from nidaqmx.stream_writers import AnalogMultiChannelWriter
from Modules_FIB import ImageProcessing as ImPr
import numpy as np
import time
from Modules_FIB import Scanning

Ui_MainWindow, QtBaseClass = uic.loadUiType("premierstep.ui")

class MyWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    
    def __init__(self):
        
        
        super(MyWindow, self).__init__()  # Initialize the parent class
        self.setupUi(self)  # Load the UI
        self.setWindowTitle("testvideo")
        
        device = nidaqmx.system.Device("Dev1")
        device.reset_device()
        
        #self.quit.clicked.connect(self.quit)
        
        
        self.time_per_pixel = 4/ 1000000
        self.sampling_frequency = 250000
        self.pixels_number = 130
        self.channel_lr = "Dev1/ao0"
        self.channel_ud = "Dev1/ao1"
        self.channel_read = "Dev1/ai0"
        self.mode = "normal"
        self.samples_per_step = int(self.time_per_pixel * self.sampling_frequency)
        self.total_samples_to_read = self.samples_per_step * self.pixels_number ** 2
        self.timeout = self.time_per_pixel * self.pixels_number * self.pixels_number + 1
        self.min_tension = -10
        self.max_tension = 10
        self.token=0
        self.Lancer.clicked.connect(self.run)
        self.STOP.clicked.connect(self.stop)
    
    
    
    def DataGen(self):
    
        self.data_to_write,self.horizontal_staircase,self.vertical_staircase=Scanning.VideoStair(self.token, self.time_per_pixel,
                                               self.sampling_frequency, self.pixels_number)
                                               
    
    def NiInitConf(self):
       self.samples_per_step,self.total_samples_to_read,self.timeout,self.write_task,self.read_task= Scanning.videoInitConf(self.min_tension, self.max_tension, self.channel_lr,self.channel_ud,self.channel_read,self.horizontal_staircase,
                              self.vertical_staircase,
                         self.pixels_number,self.time_per_pixel,self.data_to_write,self.sampling_frequency)
    
    
    #DataAc####
    def Aqcont(self):
            
        
        while (self.token==1):
            # Start the tasks
            image_array=Scanning.videoGo(self.write_task,self.read_task,self.samples_per_step,self.total_samples_to_read,self.timeout)
            np_image_norm=ImPr.normalize(image_array)
     
            stride = self.pixels_number
            qImage = QImage(np_image_norm.data, self.pixels_number, self.pixels_number, stride, QImage.Format.Format_Grayscale8)
            pixmap = QPixmap.fromImage(qImage)
            pixmap = pixmap.scaled(self.label.width(), self.label.height(),
                                   Qt.AspectRatioMode.KeepAspectRatio)
            self.label.setPixmap(pixmap)
            self.repaint()
            time.sleep(0.001)

    def run(self):   
         
        self.token=1
        self.DataGen()
        self.NiInitConf()
        self.Aqcont()
        
    def stop(self):          
        self.token=0
        
# Starts the interface
def run_interface():
    """
    Starts the Qt application and shows the main window.
    """
    app = QtWidgets.QApplication(sys.argv)  # Create a Qt application
    window = MyWindow()  # Create an instance of MyWindow
    window.show()  # Show the window
    sys.exit(app.exec())  # Start the application event loop
    

# Main function
if __name__ == '__main__':
    run_interface()
