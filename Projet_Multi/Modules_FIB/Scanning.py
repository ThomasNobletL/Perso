import numpy as np
from Modules_FIB import Ni_Dependencies as NID
#import Ni_Dependencies as NID
import time

def Scanning_Rise(time_per_pixel, sampling_frequency, pixels_number, channel_lr, channel_ud, channel_read):
    """
    Generates and reads scanning signals for a Focused Ion Beam (FIB) system.

    This function configures and executes two simultaneous tasks: one for writing
    analog output signals for scanning (both horizontal and vertical), and another
    for reading the corresponding analog input signal. It initially sets a voltage
    for 'channel_ud' to avoid synchronization issues at the start. Then it performs
    scanning by generating staircase signals in both horizontal and vertical directions
    while reading the input signal synchronously. The function averages the read data
    if more than one sample per pixel is acquired.

    Parameters:
    - time_per_pixel: Time spent per pixel, in microseconds.
    - sampling_frequency: Sampling frequency for data acquisition, in Hz.
    - pixels_number: Number of pixels per row and column in the image.
                     Two additional pixels are considered to avoid synchronization issues.
    - channel_lr: Channel name for the left-right scanning signal.
    - channel_ud: Channel name for the up-down scanning signal.
    - channel_read: Channel name for reading the input signal.

    Returns:
    - A 2D NumPy array representing the acquired image. The array dimensions correspond
      to 'pixels_number' (minus 2 to compensate for the initial extra rows and columns),
      and each element represents the averaged signal value at the corresponding pixel.
    """

    # We have to take 2 more lines and columns because the acquisition isn't really synchronised at first
    
    #TEMPORAIRE###
    #parts = channel_read.split('/')

    #device_name = parts[0]
    
    #NID.Reset_Card(device_name)
    #######
    pixels_number += 2

    # Converts microseconds to seconds
    time_per_pixel = time_per_pixel / 1000000
    timeout = time_per_pixel * pixels_number * pixels_number + 1

    # Number of samples per step/pixel
    samples_per_step = int(time_per_pixel * sampling_frequency)
    total_samples_to_read = samples_per_step * pixels_number ** 2

    # Configuring the voltages for the staircases
    min_tension = -10
    max_tension = 10

    # Set initial voltage for channel_ud
    NID.initial_voltage_setting(min_tension, max_tension, channel_ud)

    # Generating the staircase signal for left-right scanning (repeated "pixels_number" times)
    horizontal_staircase = np.repeat(np.linspace(min_tension, max_tension, pixels_number), samples_per_step)
    complete_horizontal_staircase = np.tile(horizontal_staircase, pixels_number)

    # Generating the staircase signal for top-down scanning (unique for the entire image)
    vertical_staircase = np.repeat(np.linspace(max_tension, min_tension, pixels_number),
                                   samples_per_step * pixels_number)

    # Write both signal in one task and read with another
    write_task,read_task = NID.configure_tasks(channel_lr, channel_ud, channel_read, min_tension, max_tension, 
                        sampling_frequency, complete_horizontal_staircase, total_samples_to_read,
                        vertical_staircase)
    print(write_task,read_task)
    # Structure datas to write
    data_to_write = np.array([complete_horizontal_staircase, vertical_staircase])
    
    # Create a StreamWriter for the analog outputs
    raw_data=NID.write_and_read(write_task, read_task, data_to_write,total_samples_to_read, timeout)
    # Stop the tasks

    # If there is only one sample per pixel, we skip the averaging process
    if samples_per_step == 1:

            # Reshape to a numpy 2D array (pixels_number x pixels_number)
            image_array = np.array(raw_data).reshape(pixels_number, pixels_number)

    else:

            # Convert raw_data to a NumPy array for efficient processing
            raw_data_array = np.array(raw_data)

            # Reshape the array so that each row contains samples_per_step elements
            reshaped_data = raw_data_array.reshape(-1, samples_per_step)

            # Compute the mean along the second axis (axis=1) to average each group
            averaged_data = np.mean(reshaped_data, axis=1)

            # Reshape to a 2D array (pixels_number x pixels_number)
            image_array = averaged_data.reshape(pixels_number, pixels_number)

        # To avoid weird behaviour we delete the first column and the first row of the image twice
    image_array = image_array[1:, 1:]
    image_array = image_array[1:, 1:]
    NID.close(write_task,read_task)
    return image_array

def Scanning_Triangle(time_per_pixel, sampling_frequency, pixels_number, channel_lr, channel_ud, channel_read):
    """
    Generates and reads scanning signals for a Focused Ion Beam (FIB) system.

    This function configures and executes two simultaneous tasks: one for writing
    analog output signals for scanning (both horizontal and vertical), and another
    for reading the corresponding analog input signal. It initially sets a voltage
    for 'channel_ud' to avoid synchronization issues at the start. Then it performs
    scanning by generating staircase signals in both horizontal and vertical directions
    while reading the input signal synchronously. The function averages the read data
    if more than one sample per pixel is acquired.

    Parameters:
    - time_per_pixel: Time spent per pixel, in microseconds.
    - sampling_frequency: Sampling frequency for data acquisition, in Hz.
    - pixels_number: Number of pixels per row and column in the image.
                     Two additional pixels are considered to avoid synchronization issues.
    - channel_lr: Channel name for the left-right scanning signal.
    - channel_ud: Channel name for the up-down scanning signal.
    - channel_read: Channel name for reading the input signal.

    Returns:
    - A 2D NumPy array representing the acquired image. The array dimensions correspond
      to 'pixels_number' (minus 2 to compensate for the initial extra rows and columns),
      and each element represents the averaged signal value at the corresponding pixel.
    """

    # We have to take 2 more lines and columns because the acquisition isn't really synchronised at first
    pixels_number += 2

    # Converts microseconds to seconds
    time_per_pixel = time_per_pixel / 1000000
    timeout = time_per_pixel * pixels_number * pixels_number + 1

    # Number of samples per step/pixel
    samples_per_step = int(time_per_pixel * sampling_frequency)
    total_samples_to_read = samples_per_step * pixels_number ** 2

    # Configuring the voltages for the staircases
    min_tension = -10
    max_tension = 10

    # Set initial voltage for channel_ud
    NID.initial_voltage_setting(min_tension, max_tension, channel_ud)

    # Generating the staircase signal for left-right scanning (repeated "pixels_number" times)
    horizontal_staircase = np.repeat(np.append(np.linspace(min_tension, max_tension, pixels_number), 
                                     np.linspace(max_tension, min_tension, pixels_number)), samples_per_step)
    complete_horizontal_staircase = np.tile(horizontal_staircase, pixels_number//2)                                
                                                                   


    # Generating the staircase signal for top-down scanning (unique for the entire image)
    vertical_staircase = np.repeat(np.linspace(max_tension, min_tension, pixels_number),
                                   samples_per_step * pixels_number)
    
    # Write both signal in one task and read with another
    write_task,read_task = NID.configure_tasks(channel_lr, channel_ud, channel_read, min_tension, max_tension, 
                        sampling_frequency, complete_horizontal_staircase, total_samples_to_read,
                        vertical_staircase)
    
    # Structure datas to write
    data_to_write = np.array([complete_horizontal_staircase, vertical_staircase])
    # Create a StreamWriter for the analog outputs
    raw_data=NID.write_and_read(write_task, read_task, data_to_write,total_samples_to_read, timeout)

    # If there is only one sample per pixel, we skip the averaging process
    if samples_per_step == 1:

            # Reshape to a numpy 2D array (pixels_number x pixels_number)
            image_array = np.array(raw_data).reshape(pixels_number, pixels_number)

    else:

            # Convert raw_data to a NumPy array for efficient processing
            raw_data_array = np.array(raw_data)

            # Reshape the array so that each row contains samples_per_step elements
            reshaped_data = raw_data_array.reshape(-1, samples_per_step)

            # Compute the mean along the second axis (axis=1) to average each group
            averaged_data = np.mean(reshaped_data, axis=1)

            # Reshape to a 2D array (pixels_number x pixels_number)
            image_array = averaged_data.reshape(pixels_number, pixels_number)

        # To avoid weird behaviour we delete the first column and the first row of the image twice
    image_array = image_array[1:, 1:]
    image_array = image_array[1:, 1:]
    NID.close(write_task,read_task)
    return image_array
    
def VideoStair(time_per_pixel, sampling_frequency, pixels_number):
    
    pixels_number += 2
    # Converts microseconds to seconds
    time_per_pixel = time_per_pixel / 1000000
    # Number of samples per step/pixel
    samples_per_step = int(time_per_pixel * sampling_frequency)
    # Configuring the voltages for the staircases
    min_tension = -10
    max_tension = 10
    horizontal_staircase = np.repeat(np.linspace(min_tension, max_tension, pixels_number), samples_per_step)
    complete_horizontal_staircase = np.tile(horizontal_staircase, pixels_number)
# Generating the staircase signal for top-down scanning (unique for the entire image)
    vertical_staircase = np.repeat(np.linspace(max_tension, min_tension, pixels_number),
                               samples_per_step * pixels_number)
    data_to_write = np.array([complete_horizontal_staircase, vertical_staircase])
    return data_to_write,complete_horizontal_staircase,vertical_staircase
    
def videoInitConf(channel_lr,channel_ud,channel_read,complete_horizontal_staircase,vertical_staircase,
                  pixels_number,time_per_pixel,data_to_write,sampling_frequency):
    # We have to take 2 more lines and columns because the acquisition isn't really synchronised at first
    pixels_number += 2

    # Converts microseconds to seconds
    time_per_pixel = time_per_pixel / 1000000
    timeout = time_per_pixel * pixels_number * pixels_number + 1

    # Number of samples per step/pixel
    samples_per_step = int(time_per_pixel * sampling_frequency)
    total_samples_to_read = samples_per_step * pixels_number ** 2

    # Configuring the voltages for the staircases
    min_tension = -10
    max_tension = 10
    
    NID.initial_voltage_setting(min_tension, max_tension, channel_ud)
    write_task,read_task=NID.configure_tasks(channel_lr, channel_ud, channel_read, min_tension, max_tension, 
                        sampling_frequency, complete_horizontal_staircase, total_samples_to_read,
                        vertical_staircase)
    print("initialvoltset")
    NID.writer(write_task,data_to_write)
    print("writer")
    return samples_per_step,total_samples_to_read,timeout,write_task,read_task
    
def videoGo(pixels_number,write_task,read_task,samples_per_step,total_samples_to_read,timeout):
    pixels_number+=2
    print("quickavt")
    raw_data = NID.quickwrite_and_read(write_task, read_task,total_samples_to_read, timeout)
    print("quick")
    # If there is only one sample per pixel, we skip the averaging process

    image_array = np.array(raw_data).reshape(pixels_number, pixels_number)

    image_array = image_array[1:, 1:]
    image_array = image_array[1:, 1:]
    
    
    return image_array
    
if __name__ == "__main__":
    channel_read = "Dev1/ai0"
    channel_lr = "Dev1/ao0"
    channel_ud = "Dev1/ao1"
    sampling_frequency = 250000  # Sampling rate in Hz
    time_per_pixel = 4  # Time spent per pixel in microseconds
    pixels_number = 256  # Number of pixels per row and column
    data_to_write,complete_horizontal_staircase,vertical_staircase=VideoStair(time_per_pixel, sampling_frequency, pixels_number)
    
    samples_per_step,total_samples_to_read,timeout,write_task,read_task=videoInitConf(channel_lr,channel_ud,channel_read,complete_horizontal_staircase,vertical_staircase,
                      pixels_number,time_per_pixel,data_to_write,sampling_frequency)
    
    data=videoGo(pixels_number,write_task,read_task,samples_per_step,total_samples_to_read,timeout)
    NID.close(write_task,read_task)
    print(data)
