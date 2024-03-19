import nidaqmx
import sys
from PyQt6 import QtCore, QtWidgets, uic
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QThread, pyqtSignal, Qt
import pyvisa
import warnings
import Sweep
import time
import numpy as np
from PIL import Image
import json
from math import ceil


# Ignores the ResourceWarnings made by PyVISA library
warnings.simplefilter("ignore", ResourceWarning)

# Load the UI file created with QT Designer
Ui_MainWindow, QtBaseClass = uic.loadUiType("final.ui")


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
        self.pushButton_quit.clicked.connect(self.quit)
        self.pushButton_dev_refresh.clicked.connect(self.populate_dev_combobox)
        self.pushButton_connect_dev.clicked.connect(self.connect_to_card)
        self.pushButton_gpp_4323_refresh.clicked.connect(self.populate_gpp_4323_combobox)
        self.pushButton_connect_gpp_4323.clicked.connect(self.connect_to_gpp_4323)
        self.pushButton_connect_gpp_4323_help.clicked.connect(self.gpp_4323_help)
        self.pushButton_sweep.clicked.connect(self.Sweep)
        self.pushButton_save_image.clicked.connect(self.saveImage)
        self.pushButton_load_config.clicked.connect(self.loadConfig)
        self.pushButton_save_config.clicked.connect(self.saveConfig)

        # Connect sliders to their respective functions
        self.brightness_slider.valueChanged.connect(self.gpp_4323_brightness_slider_changed)
        self.brightness_slider.sliderReleased.connect(self.gpp_4323_brightness_slider_released)

        # Ensure required time recalculation after modification
        self.spinBox_time_per_pixel.valueChanged.connect(self.required_time)
        self.spinBox_image_size.valueChanged.connect(self.required_time)

        # Initialize instance variables
        self.port_dev = None
        self.gpp_power_supply = None
        self.sweep_thread = None
        self.population_thread = None
        self.progressBarThread = None
        self.currentImage = None

        # Initialize the comboBoxes
        self.populate_dev_combobox()
        self.populate_gpp_4323_combobox()

        # Initialize the required time
        self.required_time()

        # Initialize the image to black
        self.displayImage(np.zeros(self.spinBox_image_size.value()**2, dtype=np.uint8).reshape(self.spinBox_image_size.value(), self.spinBox_image_size.value()))

    # Function to quit the application

    def quit(self):
        """
        Function to quit the application safely.
        Disconnects from the power supply if connected before exiting.
        """
        if self.gpp_power_supply is not None:
            self.gpp_power_supply.disconnect()
        QtCore.QCoreApplication.instance().quit()

    #########################################################################################
    # NI connection part

    # Function to display the current available devices
    def populate_dev_combobox(self):
        """
        Populates the combobox with the names of National Instruments (NI) devices currently connected to the system.

        This method queries the local NI system for all connected devices and updates the combobox with their names.
        It is used to provide a selection of available NI devices for user interaction.
        """
        try:
            system = nidaqmx.system.System.local()
            items = [device.name for device in system.devices]  # Lists the connected NI devices
            self.comboBox_dev.clear()  # Clear existing items
            self.comboBox_dev.addItems(items)  # Add new items

        except Exception as e:
            self.Message('Error', f"populate_dev_combobox function returned : {e}")

    # Connection to the NI Card and verification
    def connect_to_card(self):
        """
        Establishes a connection to the selected NI card and populates the corresponding comboboxes for analog input and output channels.

        This method checks if the selected device from the combobox is currently connected. If so, it retrieves and lists
        the available analog output and input channels of the selected NI device in their respective comboboxes.
        """
        try:
            self.port_dev = self.comboBox_dev.currentText()
            system = nidaqmx.system.System.local()
            if (not self.comboBox_dev.currentText() in system.devices) or (
                    self.comboBox_dev.currentText() == ""):  # Checks if the device is connected
                self.Message('Error', 'Wrong port choice')
                self.populate_dev_combobox()
                self.port_dev = None
            else:  # If the device is connected, we do this
                self.port_dev = self.comboBox_dev.currentText()
                device = nidaqmx.system.Device(self.port_dev)
                ao_channels = [chan.name for chan in device.ao_physical_chans]  # Lists the available analog output channels
                ai_channels = [chan.name for chan in device.ai_physical_chans]  # Lists the available analog input channels
                self.comboBox_vs.clear()  # Clear existing items
                self.comboBox_hs.clear()  # Clear existing items
                self.comboBox_vs.addItems(ao_channels)  # Add new items
                self.comboBox_hs.addItems(ao_channels)  # Add new items
                self.comboBox_sensor.clear()  # Clear existing items
                self.comboBox_sensor.addItems(ai_channels)  # Add new items

        except Exception as e:
            self.Message('Error', f"Connect_to_card function returned : {e}")

    #########################################################################################
    # Gpp_4323 connection part

    # Thread to display the current available devices because slow response
    def populate_gpp_4323_combobox(self):
        """
        Initiates a background thread to populate the GPP 4323 combobox with available device names.

        This method starts a separate thread to retrieve the list of connected devices (specifically for GPP 4323) to
        prevent the GUI from freezing during this potentially time-consuming operation. The retrieved device names are
        then listed in the GPP 4323 combobox.
        """
        try:
            self.population_thread = Population()
            self.population_thread.list.connect(self.send_to_GPP_comboBox)
            self.population_thread.finished.connect(self.thread_cleanup)
            self.population_thread.start()
        except Exception as e:
            self.Message('Error', f"populate_gpp_4323_combobox function returned : {e}")

    # Function to display the list to the comboBoxes
    def send_to_GPP_comboBox(self, items):
        """
        Displays the list of connected VISA devices in the comboBox.

        Args:
        items (list): List of device names to be displayed in the comboBox.
        """
        self.comboBox_gpp_4323.clear()  # Clear existing items
        self.comboBox_gpp_4323.addItems(items)  # Add new items

    # Connection to the gpp_4323 and verification
    def connect_to_gpp_4323(self):
        """
        Handles the connection to the selected GPP4323 power supply.
        Validates the selection and updates the UI based on the connection status.
        """
        try:
            currentText = self.comboBox_gpp_4323.currentText()
            if currentText == '':
                self.Message('Error', f"Please select something")
            else:
                self.gpp_power_supply = PowerSupply(currentText)

                error_checker = self.gpp_power_supply.connect()  # None if no error and "error message" otherwise
                if error_checker is None:
                    self.brightness_slider.setEnabled(True)  # Enables the brightness slider
                else:
                    self.Message('Error', f'Failed to connect to GPP4323 : {error_checker}')
        except Exception as e:
            self.Message('Error', f"Connect_to_gpp_4323 function returned : {e}")

    # Connection help button
    def gpp_4323_help(self):
        """
        Displays a help message regarding the connections for the GPP4323 power supply.
        """
        self.Message('Help', 'Connect both CH1(-) and CH2(-) together and take your output between CH1(+) and CH2().\nConnect the electron detector to CH4.')

    #########################################################################################
    # Sliders part

    # Updates the label as the user changes the slider
    def gpp_4323_brightness_slider_changed(self):
        """
        Updates the label to display the current brightness tension value based on the slider's position.
        This function is called whenever the slider value changes.
        """
        try:
            tension = self.brightness_slider.value()  # Gets the value of the slider
            self.label_current_brightness.setText(f'Brightness tension (V) : {str(tension)}')  # Shows to the user the current tension
        except Exception as e:
            self.Message('Error', f"Gpp_4323_brightness_slider_changed returned : {e}")

    # Updates the value only when the user release the slider
    def gpp_4323_brightness_slider_released(self):
        """
        Updates the brightness tension of the GPP power supply when the slider is released.
        This function ensures that the power supply's tension is updated only when the user finishes adjusting the slider.
        """
        try:
            self.gpp_power_supply.set_tension(self.brightness_slider.value())  # Gets the value of the slider and send it to the power supply
        except Exception as e:
            self.Message('Error', f"Gpp_4323_brightness_slider_released returned : {e}")

    #########################################################################################
    # Sweep part
    def Sweep(self):
        """
        Function to start the Sweep operation.
        Checks for valid configurations and starts the SweepThread and ProgressBarThread.
        """
        if self.port_dev is None:
            self.Message('Error', f"Please connect to NI Card first")
        elif self.comboBox_hs.currentText() == self.comboBox_vs.currentText():
            self.Message('Error', f"Please choose different channels for horizontal and vertical sweep")
        elif self.gpp_power_supply is None:
            self.Message('Error', f"Please connect to GPP power supply first")
        elif self.spinBox_time_per_pixel.value() < 1000000/self.spinBox_sampling_frequency.value():
            self.Message('Error', f"You must be at least have {ceil(1000000/self.spinBox_sampling_frequency.value())} µs per pixel")
        else:
            try:
                # Gets the values from the comboBoxes
                time_per_pixel = self.spinBox_time_per_pixel.value()
                sampling_frequency = self.spinBox_sampling_frequency.value()
                pixels_number = self.spinBox_image_size.value()
                channel_lr = self.comboBox_hs.currentText()
                channel_ud = self.comboBox_vs.currentText()
                channel_read = self.comboBox_sensor.currentText()

                # Sweep signal generation in a thread
                self.sweep_thread = SweepThread(time_per_pixel, sampling_frequency, pixels_number, channel_lr, channel_ud, channel_read)
                self.sweep_thread.errorOccurred.connect(self.handleSweepError)
                self.sweep_thread.image.connect(self.displayImage)
                self.sweep_thread.finished.connect(self.thread_cleanup)

                self.progressBarThread = ProgressBar(time_per_pixel, pixels_number)
                self.progressBarThread.progressUpdated.connect(self.updateProgressBar)
                self.progressBarThread.finished.connect(self.thread_cleanup)

                self.sweep_thread.start()
                self.progressBarThread.start()

            except Exception as e:
                self.Message('Error', f"Sweep function returned : {e}")

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
    def updateProgressBar(self, value):
        """
        Updates the progress bar's value during the sweep process.

        This method is connected to the `progressUpdated` signal of the ProgressBar thread. It is
        called periodically to update the progress bar on the UI to reflect the current progress of
        the sweep operation.

        Parameters:
            value (int): The current progress value to set on the progress bar.
        """
        self.progressBar_sweep.setValue(value)

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
            pixels_number = self.spinBox_image_size.value()

            # Normalise the values between 0 and 255
            min_val = np_image.min()
            max_val = np_image.max()
            if max_val > min_val:
                np_image = ((np_image - min_val) / (max_val - min_val)) * 255
                np_image = np_image.astype(np.uint8)

            self.currentImage = np_image   # Useful to save the image

            stride = pixels_number  # Number of bytes per line for a grayscale image
            qImage = QImage(np_image.data, pixels_number, pixels_number, stride, QImage.Format.Format_Grayscale8)
            pixmap = QPixmap.fromImage(qImage)
            pixmap = pixmap.scaled(self.QPixmap_ui.width(), self.QPixmap_ui.height(),
                                   Qt.AspectRatioMode.KeepAspectRatio)
            self.QPixmap_ui.setPixmap(pixmap)
            self.repaint()

        except Exception as e:
            self.Message('Error', f" Couldn't display the image : {e}")

    # Save the image
    def saveImage(self):
        """
        Function to save the current image displayed in the interface.
        Opens a dialog to choose the file location and format.
        """
        try:
            # Get the save name
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Image", "", "PNG Files (*.png);;JPEG Files (*.jpeg);;BMP Files (*.bmp);;TIFF Files (*.tiff);;All Files (*)")
            if filename:
                # Save the image currently displayed on the QPixmap
                img = Image.fromarray(self.currentImage)
                img.save(filename)
        except Exception as e:
            self.Message('Error', f"Failed to save image : {e}")

    #########################################################################################
    # Config part
    def saveConfig(self):
        """
        Function to save the current configuration to a JSON file.
        Extracts values from UI elements and writes them to 'config.json'.
        """
        try:
            # Gets the values from the UI
            config = {
                "time_per_pixel": self.spinBox_time_per_pixel.value(),
                "sampling_frequency": self.spinBox_sampling_frequency.value(),
                "pixels_number": self.spinBox_image_size.value(),
                "channel_lr": self.comboBox_hs.currentText(),
                "channel_ud": self.comboBox_vs.currentText(),
                "channel_read": self.comboBox_sensor.currentText(),
                "port_dev": self.comboBox_dev.currentText(),
                "gpp_power_supply": self.comboBox_gpp_4323.currentText()
            }

            # Saves into a json file
            with open('config.json', 'w') as config_file:
                json.dump(config, config_file)
            self.Message('Success', "Config saved successfully")

        except Exception as e:
            self.Message('Error', f"Couldn't save config : {e}")

    def loadConfig(self):
        """
        Function to load configuration from a JSON file.
        Reads 'config.json' and updates the UI elements with stored values.
        """
        try:
            # Loads the json config file
            with open('config.json', 'r') as config_file:
                config = json.load(config_file)

            # Updates the UI
            self.spinBox_time_per_pixel.setValue(config.get("time_per_pixel", 0))
            self.spinBox_sampling_frequency.setValue(config.get("sampling_frequency", 0))
            self.spinBox_image_size.setValue(config.get("pixels_number", 0))
            self.comboBox_dev.setCurrentText(config.get("port_dev", ""))
            self.connect_to_card()
            self.comboBox_hs.setCurrentText(config.get("channel_lr", ""))
            self.comboBox_vs.setCurrentText(config.get("channel_ud", ""))
            self.comboBox_sensor.setCurrentText(config.get("channel_read", ""))
            self.comboBox_gpp_4323.setCurrentText(config.get("gpp_power_supply", ""))

        # Handles errors
        except FileNotFoundError:
            self.Message('Error', "Configuration file not found.")
        except json.JSONDecodeError:
            self.Message('Error', "Error reading the configuration file.")
        except Exception as e:
            self.Message('Error', f"Failed to load the config : {e}")

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
    def required_time(self):
        """
        Calculates and displays the required time for the sweep operation.

        This method calculates the total time required for the sweep operation based on the
        time per pixel and the total number of pixels. It updates the UI to display this
        information in a user-friendly format.
        """
        time_per_pixel = self.spinBox_time_per_pixel.value() / 1000000   # µs to s
        pixels_number = self.spinBox_image_size.value() + 2

        # Change the display format to minutes if there are more than 60 seconds required
        seconds = int(time_per_pixel * pixels_number ** 2)
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if minutes == 0:
            result_str = f"{remaining_seconds} seconds"
        else:
            result_str = f"{minutes}mn {remaining_seconds}s"

        self.label_time.setText(f"Acquisition time : {result_str}")   # Write the required time on the UI


#########################################################################################
# Classes


# Class for the GPP4323 power supply
class PowerSupply:
    """
    A class to handle the operations related to the GPP4323 power supply.

    This class provides functionalities to connect to, configure, and control the GPP4323 power supply
    using the PyVISA library. It allows setting the tension, and disconnecting from the power supply.

    Attributes:
        port (str): The port name where the power supply is connected.
        device (pyvisa.Resource): A PyVISA resource representing the power supply.
    """

    def __init__(self, port):
        """
        Initializes the PowerSupply object with the specified port.

        Parameters:
            port (str): The port name where the power supply is connected.
        """
        self.port = port
        self.device = None

    def connect(self):
        """
        Connects to the power supply and initializes its settings.

        This method establishes a connection to the power supply and sets initial current and voltage settings.
        It also prints the device's identification string.

        Returns:
            Exception: Any exception raised during connection, if any.
        """
        try:
            rm = pyvisa.ResourceManager()
            self.device = rm.open_resource(self.port)
            print(self.device.query('*IDN?'))
            print("A CHANGER IMPERATIVEMENT")
            self.device.write(f'ISET1:0.03')
            self.device.write(f'ISET2:0.03')
            self.device.write(f'ISET4:0.03')
            self.device.write(f'VSET1:32')
            self.device.write(f'VSET2:32')
            self.device.write(f'VSET3:0')
            self.device.write(f'VSET4:0')
            self.device.write(f':ALLOUTON')
        except Exception as e:
            return e

    def set_tension(self, tension):
        """
        Sets the tension of the power supply to the specified value.

        Parameters:
            tension (float): The tension value to set on the power supply.
        """
        if self.device:
            self.device.write(f'VSET4:{tension}')

    def disconnect(self):
        """
        Disconnects the power supply and resets its settings.

        This method turns off all outputs and closes the connection to the power supply.
        """
        if self.device:
            self.device.write(f'ISET1:0')
            self.device.write(f'ISET2:0')
            self.device.write(f'ISET4:0')
            self.device.write(f'VSET1:0')
            self.device.write(f'VSET2:0')
            self.device.write(f'VSET3:0')
            self.device.write(f'VSET4:0')
            self.device.write(f':ALLOUTOFF')
            time.sleep(0.1)
            self.device.close()


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

    def __init__(self, time_per_pixel, sampling_frequency, pixels_number, channel_lr, channel_ud, channel_read,
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
        self.time_per_pixel = time_per_pixel
        self.sampling_frequency = sampling_frequency
        self.pixels_number = pixels_number
        self.channel_lr = channel_lr
        self.channel_ud = channel_ud
        self.channel_read = channel_read

    # Get the list of pixels and send it back
    def run(self):
        """
        Executes the sweep operation in a separate thread.

        This method is automatically called when the thread starts. It runs the sweep process and emits
        the resulting image data or any errors encountered.
        """
        try:
            # Sweep signal generation from "Sweep.py"
            data = Sweep.Sweep(self.time_per_pixel, self.sampling_frequency, self.pixels_number, self.channel_lr,
                               self.channel_ud, self.channel_read)
            self.image.emit(data)
        except Exception as e:
            self.errorOccurred.emit(str(e))


# Thread class for GPP ComboBox population
class Population(QThread):
    list = QtCore.pyqtSignal(list)

    def __init__(self, parent=None):
        super(Population, self).__init__(parent)  # Initialize the QThread parent class

    # Get the list of connected devices and send it back
    def run(self):
        rm = pyvisa.ResourceManager()
        items = rm.list_resources()  # Lists the connected VISA devices
        rm.close()
        self.list.emit(items)


# Thread class for the progress bar
class ProgressBar(QThread):
    """
    A QThread subclass for populating the list of connected GPIB devices.

    This thread class is used to asynchronously retrieve and emit the list of connected GPIB devices,
    ensuring that the UI remains responsive during this potentially time-consuming process.

    Attributes:
        list (pyqtSignal): Signal emitted with the list of connected GPIB devices.
    """
    progressUpdated = pyqtSignal(int)  # Signal to update the progression

    def __init__(self, time_per_pixel, pixels_number, parent=None):
        """
        Initializes the Population thread.

        Parameters:
            parent (QObject): The parent object for this thread, if any.
        """
        super(ProgressBar, self).__init__(parent)
        time_per_pixel = time_per_pixel / 1000000
        self.total_time = time_per_pixel * (pixels_number +2) ** 2
        self.interval = time_per_pixel  # Update interval

    # Calculates the percentage progress and send it back
    def run(self):
        """
        Executes the device population process in a separate thread.

        This method is automatically called when the thread starts. It retrieves the list of connected
        GPIB devices and emits it through the 'list' signal.
        """
        start_time = time.time()
        while time.time() - start_time < self.total_time:
            elapsed_time = time.time() - start_time
            progress = int((elapsed_time / self.total_time) * 100)
            self.progressUpdated.emit(progress)
            time.sleep(self.interval)  # Wait for the next update
        self.progressUpdated.emit(100)


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
