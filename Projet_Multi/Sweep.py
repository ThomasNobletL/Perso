import numpy as np
import nidaqmx
from nidaqmx.constants import AcquisitionType, TerminalConfiguration, Edge
from nidaqmx.stream_writers import AnalogMultiChannelWriter


def Sweep(time_per_pixel, sampling_frequency, pixels_number, channel_lr, channel_ud, channel_read):
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
    with nidaqmx.Task() as init_task:
        init_task.ao_channels.add_ao_voltage_chan(channel_ud, min_val=min_tension, max_val=max_tension)
        init_task.write(max_tension)
        init_task.start()
        init_task.stop()

    # Generating the staircase signal for left-right scanning (repeated "pixels_number" times)
    horizontal_staircase = np.repeat(np.linspace(min_tension, max_tension, pixels_number), samples_per_step)
    complete_horizontal_staircase = np.tile(horizontal_staircase, pixels_number)

    # Generating the staircase signal for top-down scanning (unique for the entire image)
    vertical_staircase = np.repeat(np.linspace(max_tension, min_tension, pixels_number),
                                   samples_per_step * pixels_number)

    # Write both signal in one task and read with another
    with nidaqmx.Task() as write_task, nidaqmx.Task() as read_task:

        # Channels configuration
        write_task.ao_channels.add_ao_voltage_chan(channel_lr, min_val=min_tension, max_val=max_tension)
        write_task.ao_channels.add_ao_voltage_chan(channel_ud, min_val=min_tension, max_val=max_tension)
        read_task.ai_channels.add_ai_voltage_chan(channel_read, min_val=min_tension, max_val=max_tension,
                                                  terminal_config=TerminalConfiguration.DIFF)

        # Timing configuration
        write_task.timing.cfg_samp_clk_timing(rate=sampling_frequency, sample_mode=AcquisitionType.FINITE,
                                              samps_per_chan=len(complete_horizontal_staircase))
        read_task.timing.cfg_samp_clk_timing(rate=sampling_frequency, sample_mode=AcquisitionType.FINITE,
                                             samps_per_chan=total_samples_to_read)

        # Trigger the read task at the start of the write task
        read_trigger_source = '/' + channel_lr.split('/')[0] + '/ao/StartTrigger'
        read_task.triggers.start_trigger.cfg_dig_edge_start_trig(read_trigger_source, trigger_edge=Edge.RISING)

        # Structure datas to write
        data_to_write = np.array([complete_horizontal_staircase, vertical_staircase])

        # Create a StreamWriter for the analog outputs
        writer = AnalogMultiChannelWriter(write_task.out_stream)

        # Write both signals at the same time
        writer.write_many_sample(data_to_write)

        # Start the tasks
        read_task.start()
        write_task.start()

        # Read the data for the entire image
        raw_data = read_task.read(number_of_samples_per_channel=total_samples_to_read, timeout=timeout)

        # Wait for the end of the tasks
        write_task.wait_until_done(timeout=timeout)

        # Stop the tasks
        write_task.stop()
        read_task.stop()

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

        return image_array


if __name__ == "__main__":
    channel_read = "Dev1/ai1"
    channel_lr = "Dev1/ao0"
    channel_ud = "Dev1/ao1"
    sampling_frequency = 250000  # Sampling rate in Hz
    time_per_pixel = 4  # Time spent per pixel in microseconds
    pixels_number = 1024  # Number of pixels per row and column
    data = Sweep(time_per_pixel, sampling_frequency, pixels_number, channel_lr, channel_ud, channel_read)
