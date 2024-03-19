# -*- coding: utf-8 -*-
"""
Created on Tue Jan  9 10:19:38 2024

@author: Leo CHAKRI
"""

import sys
import time
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QMessageBox
import serial
from serial import SerialException
from threading import Thread, Lock

# Name of the QT file
MyUI = "FinalUI.ui"
Ui_MainWindow, _ = uic.loadUiType(MyUI)


class Window(QtWidgets.QMainWindow, Ui_MainWindow):  # Creation of the window class

    def __init__(self):  # Init function (variables, window, controls)
        
        # VARIABLES INIT
        self.VRange = [0, 10000]  # Voltage range for all power supplies
        # Communication states with the source (energy, extractor, suppressor and condensor (L1)) and the L2
        self.Source_state = False
        self.L2_state = False
        
        self.Source_connection_tried = False
        self.L2_connection_tried = False
        
        self.Source_port_survive = True
        self.L2_port_survive = True
        
        ## Window Init ##
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        
        ## Interface Init ##
        # Status
        self.L2_COM_Status.setEnabled(False)
        self.L2_COM_Status.setChecked(False)
        self.Source_COM_Status.setEnabled(False)
        self.Source_COM_Status.setChecked(False)
        self.Source_Gun_Status.setEnabled(False)
        self.Source_Gun_Status.setChecked(False)
        # Controls
        self.Source_Gun.setEnabled(False)
        self.Source_PowerSuppliesControl.setEnabled(False)
        self.L1.setEnabled(False)
        self.L2.setEnabled(False)
        self.Lenses_SendValues.setEnabled(False)

        ## Click Events ##
        self.Source_Connect.clicked.connect(self.connectSource)
        self.Source_Gun.clicked.connect(self.gun)
        self.L2_Connect.clicked.connect(self.connectL2)
        self.Source_SendValues.clicked.connect(self.setVoltageSource)
        self.Lenses_SendValues.clicked.connect(self.setVoltageLenses)
        self.Quit.clicked.connect(self.stop)


    def connectSource(self):

        if self.Source_connection_tried:
            self.Source_Connect.setText("Connect")
            self.Source_port.close()
            self.Source_connection_tried = False
        
        else:
            try:
                self.Source_port = serial.Serial(port=self.Source_COM_Choice.currentText(), baudrate=57600, bytesize=8, timeout=0.5, stopbits=1)
                self.Source_COM_Status.setChecked(True)
                self.Source_connection_tried = True
                self.Source_Connect.setText("Disconnect")

            except SerialException:
                QMessageBox.information(self, 'Communication Error', 'Wrong port choice or power supply off.')
                self.Source_COM_Status.setChecked(False)

            if self.Source_COM_Status.isChecked():
                self.Source_port.write(b'>3,17,0,100,100,65,65,65,65,1.0,1.0,1\r')
                if self.Source_port.readline() != b'>3,17,2\r':
                    QMessageBox.information(self, 'Power Supply Error', 'High Voltages Power Supply could not be activated.')
                else:
                    self.Source_Gun.setEnabled(True)
                    self.Source_state = True

                    self.Source_lock = Lock()
                    self.Source_thread = Thread(target=self.Source_Readingloop, args=(self.Source_port, self.Source_lock))
                    self.Source_thread.start()

    def gun(self):
        if self.Source_Gun_Status.isChecked():
            self.Source_port.write(b'>1,10,0\r')  # CMD_SET_GUN_STATUS Off
            self.Source_Gun.setText("Gun ON")
            self.Source_Gun_Status.setChecked(False)
            self.L1.setEnabled(False)
            self.Source_PowerSuppliesControl.setEnabled(False)
            self.Lenses_SendValues(False)

        else:
            self.Source_port.write(b'>1,10,2\r')  # CMD_SET_GUN_STATUS On
            self.Source_Gun.setText("Gun OFF")
            self.Source_Gun_Status.setChecked(True)
            self.L1.setEnabled(True)
            self.Source_PowerSuppliesControl.setEnabled(True)
            self.Lenses_SendValues(True)

    def connectL2(self):

        if self.L2_connection_tried:
            self.L2_Connect.setText("Connect")
            self.L2_port.close()
            self.L2_connection_tried = False
            
        else:
            try:
                self.L2_port = serial.Serial(port=self.L2_COM_Choice.currentText(), baudrate=57600, bytesize=8, timeout=0.05, stopbits=1) #Open and configure the port
                self.L2_COM_Status.setChecked(True)
                self.L2_connection_tried = True
                self.L2_Connect.setText("Disconnect")
                
            except SerialException:
                QMessageBox.information(self, 'Communication Error', 'Wrong port choice or power supply off.')
                self.L2_COM_Status.setChecked(False)
                 
            if self.checkBox_ConnectionStatus_Source.isChecked():
                   self.L2_port.write(b'>1,10,2\r')
                   if self.L2_port.readline() != b'>1,10,2\r':
                       QMessageBox.information(self, 'Power Supply Error', 'High Voltages Power Supply could not be activated.')
                   else:
                       self.L2.setEnabled(True)
                       self.Lenses_SendValues(True)
                       self.L2_state = True
                       
                       self.L2_lock = Lock()
                       self.L2_thread = Thread(target=self.L2_Readingloop, args=(self.L2_port, self.L2_lock))
                       self.L2_thread.start()
       

    def setVoltageSource(self):

        self.Energy_voltage = self.Energy_TargetVoltage.value()
        self.Extractor_voltage = self.Extractor_TargetVoltage.value()
        self.Suppressor_voltage = self.Suppressor_TargetVoltage.value()

        if self.Energy_voltage >= self.VRange[0] and self.Energy_voltage <= self.VRange[1]:
            self.Source_port.write(b'>1,1,%f,0\r' % float(self.Energy_voltage))  # CMD_SET_VOLTAGE for Energy

        elif self.Extractor_voltage >= self.VRange[0] and self.Extractor_voltage <= self.VRange[1]:
            self.Soure_port.write(b'>3,1,%f,0\r' % float(self.Extractor_voltage))  # CMD_SET_VOLTAGE for Extractor

        elif self.Suppressor_voltage >= self.VRange[0] and self.Energy_voltage <= self.VRange[1]:
            self.Source_port.write(b'>2,1,%f,0\r' % float(self.Energy_voltage))  # CMD_SET_VOLTAGE for Suppressor

        else:
            QMessageBox.information(self, 'Source Voltage Error', 'The voltage you are trying to set is out of range.')

    def setVoltageLenses(self):

        self.L2_voltage = self.L2_TargetVoltage.value()
        self.L1_voltrage = self.L1_TargetVoltage.value()
        
        if self.L2_voltage >= self.VRange[0] and self.L2_voltage <= self.VRange[1] and self.L2_state:
            self.L2_port.write(b'>1,1,%f,0\r'%float(self.voltage))

        elif self.L1_voltage >= self.VRange[0] and self.L1_voltage <= self.VRange[1] and self.Source_state:
            self.Source_port.write(b'>4,1,%f,0\r' % float(self.L1_voltage))  # CMD_SET_VOLTAGE for L1
        else:
            QMessageBox.information(self, 'Lenses Voltage Error', 'The voltage you are trying to set is out of range.')

    def Source_Readingloop(self, port, lock):

        while self.Source_port_survive:
            lock.acquire()

            port.write(b'>1,2\r')
            energy_line = str(port.readline())
            if len(energy_line) > 3:
                self.label_Actual_Voltage.setText(energy_line.split(",")[2])
                self.label_Actual_Current.setText(energy_line.split(",")[3])

            port.write(b'>3,2\r')
            extractor_line = str(port.readline())
            if len(extractor_line) > 3:
                self.label_Actual_Voltage.setText(extractor_line.split(",")[2])
                self.label_Actual_Current.setText(extractor_line.split(",")[3])

            port.write(b'>2,2\r')
            suppressor_line = str(port.readline())
            if len(suppressor_line) > 3:
                self.label_Actual_Voltage.setText(suppressor_line.split(",")[2])
                self.label_Actual_Current.setText(suppressor_line.split(",")[3])

            port.write(b'>4,2\r')
            L1_line = str(port.readline())
            if len(L1_line) > 3:
                self.label_Actual_Voltage.setText(L1_line.split(",")[2])
                self.label_Actual_Current.setText(L1_line.split(",")[3])

            lock.release()
            time.sleep(1.1)

    def L2_Readingloop(self, port, lock):
        
        while self.L2_port_survive:
            lock.acquire()
            
            port.write(b'>1,2\r')
            line = str(port.readline())
            if len(line) > 3:
                self.label_Actual_Voltage.setText(line.split(",")[2])
                self.label_Actual_Current.setText(line.split(",")[3])
            
            lock.release()
            time.sleep(1.1)
        
                  
    def stop(self):
        
        if self.Source_COM_Status.isChecked():
            self.Source_port.write(b'>1,1,0,0\r')
            self.Source_port.write(b'>1,10,0\r')
            self.Source_port.write(b'>3,1,0,0\r')
            self.Source_port.write(b'>3,10,0\r')
            self.Source_port.write(b'>2,1,0,0\r')
            self.Source_port.write(b'>2,10,0\r')
            self.Source_port.write(b'>4,1,0,0\r')
            self.Source_port.write(b'>4,10,0\r')
            
        if self.Source_Gun_Status.isChecked():
            self.Source_port.write(b'>1,10,0\r')
            
        if self.L2_COM_Status.isChecked():
            self.L2_port.write(b'>1,1,0,0\r')
            self.L2_port.write(b'>1,10,0\r')
        
        if self.Source_connection_tried:
            self.Source_port.close()
            
        if self.L2_connection_tried:
            self.L2_port.close()
            
        self.Source_port_survive = False
        self.L2_port_survive = False
        QtWidgets.QMainWindow.close(self) 
            
        
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())