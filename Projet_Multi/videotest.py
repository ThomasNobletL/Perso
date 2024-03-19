# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 11:40:07 2024

@author: tp_tp4
"""

import sys
from PyQt6 import QtCore, QtWidgets, uic
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QThread, pyqtSignal, Qt
import warnings
from Modules_FIB import ImageProcessing as ImPr
from Modules_FIB import Scanning
from Modules_FIB import Ni_Dependencies as NID
from Modules_FIB import Visa_Dependencies as VID
from Modules_FIB.Visa_Dependencies import PowerSupply as PS
import time
import pyvisa
import numpy as np
from PIL import Image
import json
from math import ceil
import subprocess 

# Ignores the ResourceWarnings made by PyVISA library
warnings.simplefilter("ignore", ResourceWarning)

# Load the UI file created with QT Designer
Ui_MainWindow, QtBaseClass = uic.loadUiType("Videosimple.ui")


# Main class for the interface
class MyWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    """
    Main class for the Focused Ion Beam (FIB) control interface.
    Inherits from QMainWindow and the Ui_MainWindow generated from Qt Designer.
    """

    listChanged = QtCore.pyqtSignal(list)  # Signal to emit acquired data

    # Initialize the interface
    def __init__(self):
        """
        Initialize the interface and set up UI components and connections.
        """
        super(MyWindow, self).__init__()  # Initialize the parent class
        self.setupUi(self)  # Load the UI
        self.setWindowTitle("Interface de pilotage du FIB")  # Set window title
        # Connect buttons to their respective functions
        
        self.ButtonVideo.clicked.connect(self.clicked)
        
        # Initialize instance variables
        self.port_dev = "Dev1"
        self.sweep_thread = None
        self.currentImage = None
        self.token =0
        
        # Initialize the image to black
        self.displayImage(np.zeros(128**2, dtype=np.uint8).reshape(128, 128))
        

    # Connection to the NI Card and verification
    def connect_to_card(self):
        """
        Establishes a connection to the selected NI card and populates the corresponding comboboxes for analog input and output channels.

        This method checks if the selected device from the combobox is currently connected. If so, it retrieves and lists
        the available analog output and input channels of the selected NI device in their respective comboboxes.
        """
     
        self.port_dev = "Dev1"
        NID.Ni_Cards_Device(self.port_dev)
        




    #########################################################################################
    # Sweep part
    
    def clicked(self):
        if self.token ==1:
            self.token =0
            NID.Reset_Card("Dev1")
        else :
            self.token =1
        self.mauvaiseidee
    def mauvaiseidee(self):
        while self.token ==1 :
            self.sweep
    
    def Sweep(self):
        """
        Function to start the Sweep operation.
        Checks for valid configurations and starts the SweepThread and ProgressBarThread.
        """

        # Gets the values from the comboBoxes
        time_per_pixel = 4
        sampling_frequency = 250000
        pixels_number = 128
        channel_lr = "Dev1/ao0"
        channel_ud = "Dev1/ao1"
        channel_read = "Dev1/ai0"
        mode = "normal"
        # Sweep signal generation in a thread
        self.sweep_thread = SweepThread(time_per_pixel, sampling_frequency, pixels_number, channel_lr, channel_ud, channel_read,mode)
        self.sweep_thread.errorOccurred.connect(self.handleSweepError)
        self.sweep_thread.image.connect(self.displayImage)
        self.sweep_thread.finished.connect(self.thread_cleanup)
                
        self.sweep_thread.start()
          

    # If an error occurred in the thread, we display it to the user
    def handleSweepError(self, error_message):
        """
        Displays an error message if an error occurs during the sweep process.

        This method is connected to the `errorOccurred` signal of the SweepThread. It is triggered
        when the SweepThread encounters an error, and it displays the error message using the
        custom Message method of the MyWindow class.

        Parameters:
            error_message (str): The error message received from the SweepThread.
        """
        self.Message('Error', f"Sweep function returned: {error_message}")

    # Update the progression bar

    #########################################################################################
    # Image part

    # Display the image
    def displayImage(self, np_image):
        """
        Function to display the image in the interface.
        Normalizes the values and updates the QPixmap with the new image.

        Args:
        image (numpy.ndarray): List of pixel values to be displayed.
        """
        try:
            pixels_number = 128
            scanning_mode = "Normal"
            # Normalise the values between 0 and 255
            np_image_norm=ImPr.normalize(np_image)
            if scanning_mode=="Triangle":
                np_image_norm=ImPr.triangle_scanning(np_image_norm,pixels_number)
                
            self.currentImage = np_image_norm   # Useful to save the image

            stride = pixels_number  # Number of bytes per line for a grayscale image
            qImage = QImage(np_image_norm.data, pixels_number, pixels_number, stride, QImage.Format.Format_Grayscale8)
            pixmap = QPixmap.fromImage(qImage)
            pixmap = pixmap.scaled(self.label.width(), self.label.height(),
                                   Qt.AspectRatioMode.KeepAspectRatio)
            self.label.setPixmap(pixmap)
            self.repaint()
            

        except Exception as e:
            self.Message('Error', f" Couldn't display the image : {e}")


    #########################################################################################
    # Others part

    # Error message that doesn't freeze the interface
    def Message(self, title, message):
        """
        Displays a message to the user in a non-modal message box.

        This method is used throughout the MyWindow class to show various types of messages
        (such as errors, information, etc.) without freezing the interface. It creates a
        non-modal message box that does not block the rest of the UI while open.

        Parameters:
            title (str): The title of the message box.
            message (str): The message to be displayed in the message box.
        """
        # Create a non-modal message box
        msgBox = QtWidgets.QMessageBox(self)  # Message box
        msgBox.setIcon(QtWidgets.QMessageBox.Icon.Information)  # Icon
        msgBox.setText(message)  # Main message
        msgBox.setWindowTitle(title)  # Title of the window
        msgBox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)  # Ok button
        msgBox.setModal(False)  # Make it non-modal
        msgBox.show()  # Show the message box

    # Clean up the used thread resources
    def thread_cleanup(self):
        """
        Cleans up the resources used by finished threads.

        This method is typically connected to the 'finished' signal of QThread objects. It ensures
        that thread objects are deleted safely after their execution is complete, helping to free up
        resources and prevent memory leaks.
        """
        sender = self.sender()  # Retrieves the object that emitted the signal (in this case, the finished thread)
        if sender:
            sender.deleteLater()  # Safely deletes the thread object to free up resources

    # Calculation of the required time


#########################################################################################
# Classes

# Thread class for sweep
class SweepThread(QThread):
    """
    A QThread subclass for handling the sweep signal generation in a separate thread.

    This thread class is responsible for running the sweep signal generation process in the background,
    thereby keeping the main UI responsive. It communicates the results and errors through signals.

    Attributes:
        errorOccurred (pyqtSignal): Signal emitted when an error occurs in the thread.
        image (pyqtSignal): Signal emitted with the image data once the sweep process is complete.
    """
    errorOccurred = QtCore.pyqtSignal(str)  # Signal to handle possible errors
    image = QtCore.pyqtSignal(np.ndarray)

    def __init__(self, time_per_pixel, sampling_frequency, pixels_number, channel_lr, channel_ud, channel_read,mode,
                 parent=None):
        """
        Initializes the SweepThread with necessary parameters for the sweep process.

        Parameters:
            time_per_pixel (float): Time spent per pixel in the scan.
            sampling_frequency (int): The sampling frequency for the scan.
            pixels_number (int): Number of pixels in each dimension of the scan.
            channel_lr (str): The channel used for left-right movement.
            channel_ud (str): The channel used for up-down movement.
            channel_read (str): The channel used for reading the data.
            parent (QObject): The parent object for this thread, if any.
        """
        super(SweepThread, self).__init__(parent)  # Initialize the QThread parent class
        self.time_per_pixel = 4
        self.sampling_frequency = 250000
        self.pixels_number = 128
        self.channel_lr = "Dev1/ao0"
        self.channel_ud = "Dev1/ao1"
        self.channel_read = "Dev1/ai0"
        self.mode="Normal"

    # Get the list of pixels and send it back
    def run(self):
        """
        Executes the sweep operation in a separate thread.

        This method is automatically called when the thread starts. It runs the sweep process and emits
        the resulting image data or any errors encountered.
        """
        try:
            # Sweep signal generation from "Sweep.py"
            if self.mode=="Triangle" : 
                data = Scanning.Scanning_Triangle(self.time_per_pixel, self.sampling_frequency, self.pixels_number, self.channel_lr,
                               self.channel_ud, self.channel_read)
            else:
                data = Scanning.Scanning_Rise(self.time_per_pixel, self.sampling_frequency, self.pixels_number, self.channel_lr,
                                   self.channel_ud, self.channel_read)
            self.image.emit(data)
        except Exception as e:
            self.errorOccurred.emit(str(e))



#########################################################################################


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