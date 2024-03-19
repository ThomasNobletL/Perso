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
    
        horizontal_staircase = np.repeat(np.linspace(self.min_tension, self.max_tension, self.pixels_number), self.samples_per_step)
        self.complete_horizontal_staircase = np.tile(horizontal_staircase, self.pixels_number)
    
    # Generating the staircase signal for top-down scanning (unique for the entire image)
        self.vertical_staircase = np.repeat(np.linspace(self.max_tension, self.min_tension, self.pixels_number),
                                   self.samples_per_step * self.pixels_number)
    
        self.data_to_write = np.array([self.complete_horizontal_staircase, self.vertical_staircase])
    
    def NiInitConf(self):
        #Init#####
        with nidaqmx.Task() as init_task:
            init_task.ao_channels.add_ao_voltage_chan(self.channel_ud, min_val=self.min_tension, max_val=self.max_tension)
            init_task.write(self.max_tension)
            init_task.start()
            init_task.stop()
        #Conf#####
        self.write_task = nidaqmx.Task()
        self.read_task = nidaqmx.Task()
        
        # Channels configuration
        self.write_task.ao_channels.add_ao_voltage_chan(self.channel_lr, min_val=self.min_tension, max_val=self.max_tension)
        self.write_task.ao_channels.add_ao_voltage_chan(self.channel_ud, min_val=self.min_tension, max_val=self.max_tension)
        self.read_task.ai_channels.add_ai_voltage_chan(self.channel_read, min_val=self.min_tension, max_val=self.max_tension,
                                                  terminal_config=TerminalConfiguration.DIFF)
        
        # Timing configuration
        self.write_task.timing.cfg_samp_clk_timing(rate=self.sampling_frequency, sample_mode=AcquisitionType.FINITE,
                                              samps_per_chan=len(self.complete_horizontal_staircase))
        self.read_task.timing.cfg_samp_clk_timing(rate=self.sampling_frequency, sample_mode=AcquisitionType.FINITE,
                                             samps_per_chan=self.total_samples_to_read)
        
        # Trigger the read task at the start of the write task
        read_trigger_source = '/' + self.channel_lr.split('/')[0] + '/ao/StartTrigger'
        self.read_task.triggers.start_trigger.cfg_dig_edge_start_trig(read_trigger_source, trigger_edge=Edge.RISING)
    
    #DataAc####
    def Aqcont(self):
            
        # Create a StreamWriter for the analog outputs
        writer = AnalogMultiChannelWriter(self.write_task.out_stream)
        
        # Write both signals at the same time
        writer.write_many_sample(self.data_to_write)
        while (self.token==1):
            # Start the tasks
            self.read_task.start()
            self.write_task.start()
            
            # Read the data for the entire image
            raw_data = self.read_task.read(number_of_samples_per_channel=self.total_samples_to_read, timeout=self.timeout)
            # Wait for the end of the tasks
            self.write_task.wait_until_done(timeout=self.timeout)
            
            self.write_task.stop()
            self.read_task.stop()
            if self.samples_per_step == 1:

                    # Reshape to a numpy 2D array (pixels_number x pixels_number)
                    image_array = np.array(raw_data).reshape(self.pixels_number, self.pixels_number)

            else:

                    # Convert raw_data to a NumPy array for efficient processing
                    raw_data_array = np.array(raw_data)

                    # Reshape the array so that each row contains samples_per_step elements
                    reshaped_data = raw_data_array.reshape(-1, self.samples_per_step)

                    # Compute the mean along the second axis (axis=1) to average each group
                    averaged_data = np.mean(reshaped_data, axis=1)

                    # Reshape to a 2D array (pixels_number x pixels_number)
                    image_array = averaged_data.reshape(self.pixels_number, self.pixels_number)

                # To avoid weird behaviour we delete the first column and the first row of the image twice
            image_array = image_array[1:, 1:]
            image_array = image_array[1:, 1:]
            np_image_norm=ImPr.normalize(image_array)
            
            stride = self.pixels_number
            qImage = QImage(np_image_norm.data, self.pixels_number, self.pixels_number, stride, QImage.Format.Format_Grayscale8)
            pixmap = QPixmap.fromImage(qImage)
            pixmap = pixmap.scaled(self.label.width(), self.label.height(),
                                   Qt.AspectRatioMode.KeepAspectRatio)
            self.label.setPixmap(pixmap)
            self.repaint()
            time.sleep(0.01)

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
