# -*- coding: utf-8 -*-
"""
Created on Sun Feb 11 00:39:40 2024

@author: Thomas
"""
import pyvisa
import time

###############################################################################
#Class

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
###############################################################################
#Functions
def ResourcesList():
    """
    Lists the available VISA resources.

    This function retrieves a list of available VISA resources, such as connected instruments,
    using the PyVISA library.

    Returns:
        list: A list of strings representing the available VISA resources.
    """
    rm = pyvisa.ResourceManager()
    items = rm.list_resources()  # Lists the connected VISA devices
    rm.close()
    return items
