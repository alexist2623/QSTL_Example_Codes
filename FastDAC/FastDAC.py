"""
This module provides a `pyserial` interface to instruments called FastDACs that live in the Quantum Devices Group at UBC, Vancouver. The original author is Ruiheng Su. 
"""
import time
import serial
import struct
from re import I
import numpy as np
from pathlib import Path
import logging
from scipy import signal

logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-9s) %(message)s',)


class FastDAC():

    def __init__(self, port: str, baudrate: int, timeout: int, testing=False, verbose=False, datapath="Measurement_Data"):
        """ Makes a new FastDac object. 

        Parameters
        ----------
        port : str 
            Example "COM5", "dev/ttyacm0"

        baudrate : int 
            Common values are 1750000

        timeout : int 
            How long to wait before giving up trying to connnect to this device 

        testing : bool, optional
            Whether we are testing this class. Will not connect to a device when set to True.

        Returns
        -------
        A str 
        """
        self.verbose = verbose
        # private class variables
        self.__baudrate = baudrate
        self.__timeout = timeout
        self.__port = port
        if not testing:
            try:
                """
                some times the port is already occupied, and will throw an exception
                if the port is not connected anywhere else, restarting the terminal,
                or the jupyter session will help.
                """
                self.ser = serial.Serial(port, baudrate, timeout=timeout)
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                self.ser.read_all()
                id = self.IDN()
                assert id, "Empty IDN Received."
                print(id)
            except Exception as e:
                try:
                    self.ser.close()
                except:
                    pass
                print(e)
                # raise
        else:
            self.ser = None

        self.__datapath = datapath
        Path(datapath).mkdir(parents=True, exist_ok=True)

    @property
    def datapath(self):
        return Path(self.__datapath)

    @property
    def baudrate(self):
        return self.__baudrate

    @baudrate.setter
    def baudrate(self, br):
        # set the baudrate
        self.__baudrate = br
        # make new Serial port object
        self.ser.baudrate = self.__baudrate
        print("Baudrate MODIFIED")

    @property
    def timeout(self):
        return self.__timeout

    @timeout.setter
    def timeout(self, to):
        # set the timeout
        self.__timeout = to
        self.ser.timeout = self.__timeout
        print("Timeout MODIFIED")

    @property
    def port(self):
        return self.__port

    @port.setter
    def port(self, po):
        # set the baudrate
        self.__port = po
        # make new Serial port object
        self.ser.port = self.__port
        print("Port MODIFIED")

    def OPEN(self):
        """Open the underlying serial port if present and closed."""
        if getattr(self, 'ser', None) is None:
            return
        try:
            if not self.ser.is_open:
                self.ser.open()
        except Exception:
            # ignore open errors here; callers may handle
            pass

    def CLOSE(self):
        """Close the underlying serial port if present and swallow errors."""
        try:
            if getattr(self, 'ser', None) is None:
                return
            if self.ser.is_open:
                self.ser.close()
        except Exception:
            pass

    def query(self, command, close=False):
        """Queries a command from the instrument.

        Accepts either bytes or str for `command`. Ensures proper encoding
        and more robust reading logic.
        """
        if self.verbose:
            print("CMD: {}".format(command))

        if getattr(self, 'ser', None) is None:
            raise RuntimeError('No serial object available (testing mode or failed init).')

        # normalize command to bytes
        if isinstance(command, str):
            command_bytes = command.encode('ascii')
        else:
            command_bytes = command

        if not self.ser.is_open:
            try:
                self.ser.open()
            except Exception as e:
                raise

        self.ser.write(command_bytes)

        try:
            data = self.ser.readline()
            if self.verbose:
                print(data)
            data = data.decode('ascii').rstrip('\r\n')
            if 'ACK' in data:
                try:
                    data = self.ser.readline()
                    if self.verbose:
                        print(data)
                    data = data.decode('ascii').rstrip('\r\n')
                except Exception:
                    # on failure, optionally close and re-raise
                    if close:
                        try:
                            self.ser.close()
                        except Exception:
                            pass
                    raise
        except Exception:
            if close:
                try:
                    self.ser.close()
                except Exception:
                    pass
            raise

        if close:
            try:
                self.ser.close()
            except Exception:
                pass

        return data

    def write(self, command, close=False):
        """Write a command to the instrument.

        Accepts either bytes or str for `command`.
        """
        if self.verbose:
            print("CMD: {}".format(command))
        if getattr(self, 'ser', None) is None:
            raise RuntimeError('No serial object available (testing mode or failed init).')

        if not self.ser.is_open:
            self.ser.open()

        if isinstance(command, str):
            self.ser.write(command.encode('ascii'))
        else:
            self.ser.write(command)

        if close:
            try:
                self.ser.close()
            except Exception:
                pass

    @staticmethod
    def two_bytes_to_int(two_bytes, bigEndian=True):
        """Converts a byte string of two bytes to a single integer

        **Now implemented using the struct module.**

        "<<" is the right shift operator; "|" is the bitwise OR operator. We made this a static method so it is not tied to any objects of the class.

        Parameters 
        ----------
        two_bytes : byte
            A byte string of two bytes 

        bigEndian : bool, optional
            whether to unpack using big or little endian

        Returns
        -------
        An integer between 0 to 2^(16)
        """
        if bigEndian:
            # struct unpack returns a tuple
            # ">" represents big endian
            # "H" represents to unpack into an unsigned short
            # alternatively we can just do it manually
            # return int(two_bytes[0] << 8 | two_bytes[1])
            return struct.unpack(">H", two_bytes)[0]
        else:
            return struct.unpack("<H", two_bytes)[0]

    @staticmethod
    def four_bytes_to_float(four_bytes, bigEndian=True):
        """Converts a byte string of four bytes to a single floating point number.

        **Implemented using the struct module**

        Parameters 
        ----------
        four_bytes : byte str
            A byte string of four bytes 

        bigEndian : bool, optional
            whether to unpack using big or little endian

        Returns
        -------
        A signed floating point number
        """

        if bigEndian:
            # struct unpack returns a tuple
            # ">" represents big endian
            # "H" represents to unpack into an unsigned short
            # alternatively we can just do it manually
            # return int(four_bytes[0] << 8*3 | four_bytes[1] << 8*2 | four_bytes[2] << 8 | four_bytes[3])
            return struct.unpack(">f", four_bytes)[0]
        else:
            return struct.unpack("<f", four_bytes)[0]

    @staticmethod
    def map_int16_to_mV(int_val):
        """Maps an integer between 0 to 2^(16) to +/- 10000

        (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

        Parameters 
        ----------
        int_val: int

        Returns
        -------
        An double  
        """
        return (int_val - 0) * (20000.0) / (65536.0) - 10000.0

    def STOP(self):
        """Stops any sweeps or reads that the FastDAC is currently doing
        """
        return self.ser.write(b"STOP\r")
    
    def CLOSE(self):
        """Close the underlying serial port if present and swallow errors."""
        try:
            if getattr(self, 'ser', None) is None:
                return
            if self.ser.is_open:
                self.ser.close()
        except Exception:
            pass

    def NOP(self):
        """The most useful command. Does absolutely nothing. 

        Returns
        -------
        A str 
        """
        return self.query(b"NOP\r")

    def IDN(self):
        """Confirms the identity of the instrument 

        Returns
        -------
        A string, for example:'DAC-ADC_AD7734-AD5764_UNIT5_PIDTEST'
        """
        return self.query(b"*IDN?\r")

    def RDY(self):
        return self.query(b"*RDY?\r")

    def RESET(self):
        """Resets the ADCs, and sets the range to default +/-10 V
        """
        return self.query(b"RESET\r")

    def GET_DAC(self, channel=0):
        """Reads the current DAC output in millivolts

        A DAC output can be thought of as the output of a variable voltage source. 

        Parameters
        ----------
        channel : int, optional 
            The DAC channel to read

        Returns
        -------
        DAC reading : str
            The DAC reading you are looking for     
        """
        cmd = "GET_DAC,{}\r".format(channel)
        return self.query(bytes(cmd, "ascii"))

    def GET_ADC(self, channel=0):
        """Reads the current ADC input in mV

        An ADC input can be thought of as the reading of a voltmeter

        Parameters
        ----------
        channel : int, optional 
            The ADC channel to read

        Returns 
        -------
        ADC reading : str 
            The ADC reading you are looking for

        "NOP" : str
            Something is wrong 
        """
        cmd = "GET_ADC,{}\r".format(channel)
        return self.query(bytes(cmd, "ascii"))

    def SPEC_ANA(self, channels=[0, ], steps=10):
        """Reads a number of points equal to ``steps" from each ADC channels as specified in channels in mV.

        Parameters
        ----------
        channels : list, optional 
            The ADC channels to read

        steps : int, optional
            The number of data points to read 

        Returns 
        -------
        A dictionary where the keys represents the adc channels that was read, and the value is a numpy array of readings. 
        """

        cmd = "SPEC_ANA,{},{}\r".format("".join(str(ac) for ac in channels), steps)

        if self.verbose:
            print(cmd)
        if not getattr(self, 'ser', None):
            raise RuntimeError("No serial port open for SPEC_ANA")
        if not self.ser.is_open:
            self.ser.open()

        self.ser.write(cmd.encode('ascii'))

        ack = self.ser.readline()
        try:
            ack = ack.decode('ascii').rstrip('\r\n')
        except Exception:
            ack = ""

        channel_readings = {ac: [] for ac in channels}
        first_chan = channels[0]
        try:
            # continue until desired count collected for the first channel
            while self.ser.in_waiting > 15 or len(channel_readings[first_chan]) < steps:
                # read a reasonable chunk (or minimal)
                waiting = self.ser.in_waiting
                if waiting >= 1000:
                    chunk = self.ser.read(1000)
                elif waiting >= 200:
                    chunk = self.ser.read(200)
                else:
                    chunk = self.ser.read(2)

                # split chunk into 2-byte words
                for i in range(0, len(chunk), 2):
                    two_b = chunk[i:i+2]
                    if len(two_b) < 2:
                        continue
                    try:
                        int_val = FastDAC.two_bytes_to_int(two_b)
                    except Exception:
                        continue
                    voltage_reading = FastDAC.map_int16_to_mV(int_val)
                    # append reading in round-robin fashion across channels
                    # estimate which channel this reading corresponds to
                    # simple approach: append to the last channel if ambiguous
                    # (the device typically streams per-channel values in order)
                    # try to append to the channel with currently smallest length
                    target = min(channel_readings.keys(), key=lambda k: len(channel_readings[k]))
                    channel_readings[target].append(voltage_reading)

        except Exception:
            try:
                self.ser.close()
            except Exception:
                pass
            raise

        # read trailing line, close
        try:
            data = self.ser.readline()
            # safe decode but ignore errors
            _ = data.decode('ascii', errors='ignore')
        except Exception:
            pass
        try:
            self.ser.close()
        except Exception:
            pass

        # convert to numpy arrays and trim to expected length
        for k in list(channel_readings.keys()):
            arr = np.array(channel_readings[k], dtype=float)
            if arr.size > steps:
                arr = arr[:steps]
            channel_readings[k] = arr

        return channel_readings
    
    def CLEAR_BUFFER(self, channel=0):

        if not self.ser.is_open:
            self.ser.open()

        return self.ser.flush()

    def RAMP_SMART(self, channel=0, setPoint=0, rampRate=1000):
        """Changes the output of a DAC channel to the setPoint from its initial value at the rampRate [mV/s].

        Ramps one DAC channel in mV to a specified setPoint at a given ramp rate in 1ms steps. It looks up the current DAC value internally to make sure there are no sudden jumps in voltage. Internally it calls RAMP1 to do the actual ramp. 

        THe FastDAC handles 16 bit numbers. So between +/- 10 V, it is precise to within 1000*(20/2^(16)) mV.

        Parameters
        ----------
        channel : int, optional 
            The DAC channel to ramp

        setPoint : double, optional 
            The voltage in mV to ramp to. The FastDAC has a precision of ~0.3 mV

        rampRate : str, optional 

        Returns
        -------
        "RAMP_FINISHED" : str
            A sucess

        "NOP" : str
            Something is wrong
        """
        cmd = "RAMP_SMART,{},{},{}\r".format(channel, setPoint, rampRate)

        return self.query(bytes(cmd, "ascii"))

    def RAMP_AND_READ(self, DAC_channels=[0, ], ADC_channels=[0, ],  steps=1000, rampRanges={0: [-100, 100], }):
        """Ramps the specified DAC channels, and read on the specified ADC channels at the same time. 

        Parameters
        ----------
        DAC_channels : list, optional 
            A sorted list of DAC channels to ramp. Typically 0,1,2,3

        ADC_channels : list, optional 
            A sorted list of ADC channels to read. Typically 0,1,2,3,4,5,6,7

        steps : int, optional 
            The number of steps each DAC channel should take to go from an initial to a final value in mV.

        rampRanges : dict, optional 
            A dictionary. The key represents the DAC channel number, the associated value is a list containing the initial ad final values that the DAC channel should ramp. The dictionary should be sorted to match the order that the DAC channels are specified in DAC_channels

        Returns
        -------
        A dictionary where the keys represents the adc channels that was read, and the value is a numpy array of readings. 

        "NOP" : str
            Something is wrong
        """
        cmd = "INT_RAMP,"
        cmd = cmd + "".join(str(dc) for dc in DAC_channels) + ","
        cmd = cmd + "".join(str(ac) for ac in ADC_channels) + ","

        for key in rampRanges.keys():
            cmd = cmd + str(rampRanges[key][0]) + ","
        for key in rampRanges.keys():
            cmd = cmd + str(rampRanges[key][1]) + ","

        cmd = cmd + str(steps) + "\r"

        if self.verbose:
            print(cmd)
        if not self.ser.is_open:
            self.ser.open()

        self.ser.write(bytes(cmd, "ascii"))

        ack_message = self.ser.readline()

        print(ack_message)

        channel_readings = {ac: np.zeros(steps) for ac in ADC_channels}
        try:
            for i in range(0, steps):
                for channel in ADC_channels:

                    int_val = FastDAC.two_bytes_to_int(self.ser.read(2))
                    voltage_reading = FastDAC.map_int16_to_mV(int_val)
                    channel_readings[channel][i] = voltage_reading
                    

        except:
            self.ser.close()
            raise


        data = self.ser.readline()
        data = data.decode('ascii').rstrip('\r\n')
        self.ser.close()
        print(data)


        return channel_readings
    
    def SCAN_2D(self, ADC_channels=[0,],  SlowSteps=10, FastSteps=100, rampRangeSlow={0: [-100, 100]}, rampRangeFast={1: [-100, 100]}):

        SlowCh = list(rampRangeSlow.keys())[0]
        FastCh = list(rampRangeFast.keys())[0]

        SlowRange = rampRangeSlow[SlowCh]
        FastRange = rampRangeFast[FastCh]

        FastDAC.RAMP_SMART(self, channel=SlowCh, setPoint=SlowRange[0], rampRate=1000)
        time.sleep(0.1)
        FastDAC.RAMP_SMART(self, channel=FastCh, setPoint=FastRange[0], rampRate=1000)

        time.sleep(0.1)

        SlowIncrements = np.linspace(SlowRange[0], SlowRange[1], SlowSteps)
        FastIncrements = np.linspace(FastRange[0], FastRange[1], FastSteps)

        channel_readings = np.zeros((SlowSteps, FastSteps))

        for i in range(SlowSteps):

            FastRampReadings = FastDAC.RAMP_AND_READ(self, DAC_channels=[FastCh,], ADC_channels=ADC_channels, steps=FastSteps, rampRanges=rampRangeFast)
            time.sleep(0.1)

            FastDAC.RAMP_SMART(self, channel=SlowCh, setPoint=SlowIncrements[i], rampRate=1000)
            time.sleep(0.1)

            channel_readings[i] = FastRampReadings[ADC_channels[0]]

            del FastRampReadings

        return channel_readings, SlowIncrements, FastIncrements
        

    def SET_CONVERT_TIME(self, channel=0, convertTime=1000):
        """Sets the conversion time in microseconds. This is the time required to digitize the analog signal.  

        "The sum of the conversion times of all selected channels will determine overall sample rate.  Shorter conversion times result in more measured noise; Refer to the AD7734 datasheet for typical noise vs conversion times (chopping is always enabled). For the AD7734, conversion times faster than approximately 300us will start to exhibit a linear calibration offset >1mV at full range. If desired, this offset can be calibrated out using the provided calibration functions. Maximum conversion time: 2686us. Minimum conversion time: 82us. The function will return the actual closest possible setting."

        Parameters
        ----------
        channel : int, optional 
            ADC channel to set the conversion time for 

        convert_time : int, optional
            Conversion time in uS

        Returns
        -------
        An integer representing the closest possible conversion time setting.

        """
        #print("Set CONVERT_TIME to " + str(convertTime) + " uS")
        cmd = "CONVERT_TIME,{},{}\r".format(channel, convertTime)
        return self.query(bytes(cmd, "ascii"))
    
    def SET_CONVERT_TIME_ALL(self, convertTime=1000):
        """Sets the conversion time in microseconds. This is the time required to digitize the analog signal. Sets the conversion time for all channels on the ADCs 

        "The sum of the conversion times of all selected channels will determine overall sample rate.  Shorter conversion times result in more measured noise; Refer to the AD7734 datasheet for typical noise vs conversion times (chopping is always enabled). For the AD7734, conversion times faster than approximately 300us will start to exhibit a linear calibration offset >1mV at full range. If desired, this offset can be calibrated out using the provided calibration functions. Maximum conversion time: 2686us. Minimum conversion time: 82us. The function will return the actual closest possible setting."

        Parameters
        ----------
        channel : int, optional 
            ADC channel to set the conversion time for 

        convert_time : int, optional
            Conversion time in uS

        Returns
        -------
        An integer representing the closest possible conversion time setting.

        """
        for channel in range(4):
            self.SET_CONVERT_TIME(channel, convertTime)
        return 

    def READ_CONVERT_TIME(self, channel=0):
        """Returns the convert time on the specified channel in uS

        Parameters
        ----------
        channel : int, optional 
            ADC channel to get the conversion time for 

        Returns
        -------
        An string which can be cast into an integer representing the current conversion time setting.

        """

        cmd = "READ_CONVERT_TIME,{}\r".format(channel)
        return self.query(bytes(cmd, "ascii"))

    # This function would be better placed in a testing suite!
    # def check_conversion_time(self, channels=[0, 1, 2, 3], reps=100):
    #     """Checks conversion time on every channel, for the specified reps

    #     Parameters
    #     ----------
    #     channels : list, optional
    #         List of ADC channels to check conversion time for

    #     Returns
    #     -------
    #     A list containing the read conversion times as integers
    #     """

    #     read = list()
    #     for i in range(0, reps):
    #         for ac in channels:
    #             time_read = int(self.READ_CONVERT_TIME(ac))
    #             if time_read not in read:
    #                 read.append(time_read)

    #     return read

    def read_vs_time(self, fig, duration: int, channels=[0, ]):
        """Reads the specified channel in chuncks, for a number of seconds as specified in duration.

        Parameters
        ----------
        duration : int
            The number of seconds to read ADC channels specifed for 

        channels : list, optional 
            The ADC channels on the fastDAC to read from 
        """
        logging.debug('Starting')
        assert len(channels) > 0, "What? No ADC channel selected \U0001F923"

        c_time = list()
        for c in channels:
            t_read = int(self.READ_CONVERT_TIME(channel=c))
            if t_read not in c_time:
                c_time.append(t_read)

        assert len(c_time) == 1, "What? Bad conversion time \U0001F923"

        c_freq = 1/(c_time[0]*10**-6)  # in Hz

        measure_freq = c_freq/len(channels)
        steps = int(np.round(measure_freq*duration))

        cmd = "SPEC_ANA,{},{}\r".format(
            "".join(str(ac) for ac in channels), steps)

        if self.verbose:
            print(cmd)
        if not self.ser.is_open:
            self.ser.open()

        self.ser.write(bytes(cmd, "ascii"))
        channel_readings = {ac: list() for ac in channels}

        x_array = np.linspace(0, duration, steps)

        try:
            if not self.ser.is_open:
                self.ser.open()
            time.sleep(0.1)
            while self.ser.in_waiting > 15 or len(channel_readings[channels[0]]) < steps:
                new_readings = []
                # print(self.ser.in_waiting)
                for channel in channels:
                    buffer = ""
                    waiting = self.ser.in_waiting
                    if waiting > 1000 + 15:
                        buffer = self.ser.read(1000)
                    elif self.ser.in_waiting > 200+15:
                        buffer = self.ser.read(200)
                    else:
                        buffer = self.ser.read(2)

                    big_end_arr = np.ndarray(
                        shape=(int(len(buffer)/2)), dtype='>u2', buffer=buffer)
                    voltage_reading = FastDAC.map_int16_to_mV(
                        big_end_arr).tolist()
                    new_readings += voltage_reading

                channel_readings[channel] += new_readings

                if fig is not None:

                    scatter = fig.data[0]
                    with fig.batch_update():
                        scatter.x += tuple(x_array[len(scatter.x)
                                           :len(scatter.x) + len(new_readings)])
                        scatter.y += tuple(new_readings)

        except Exception as e:
            print(e)
            self.ser.close()
            raise

        self.STOP()
        data = self.ser.readline()
        print(data)
        self.ser.close()
        logging.debug('Exiting')

    def FDacSpectrumAnalyzer(self, duration: int, PDS_fig, TimeSeries_fig=None,  repeat=0, channels=[0, ], ):
        """Reads the specified channel in chuncks, for a number of seconds as specified in duration.

        Parameters
        ----------
        duration : int
            The number of seconds to read ADC channels specifed for 

        channels : list, optional 
            The ADC channels on the fastDAC to read from 
        """
        logging.debug('Starting')
        assert len(channels) > 0, "What? No ADC channel selected \U0001F923"

        c_time = list()
        for c in channels:
            t_read = int(self.READ_CONVERT_TIME(channel=c))
            if t_read not in c_time:
                c_time.append(t_read)

        assert len(c_time) == 1, "What? Bad conversion time \U0001F923"

        c_freq = 1/(c_time[0]*10**-6)  # in Hz

        measure_freq = c_freq/len(channels)
        steps = int(np.round(measure_freq*duration))

        cmd = "SPEC_ANA,{},{}\r".format(
            "".join(str(ac) for ac in channels), steps)

        if self.verbose:
            print(cmd)

        x_array = np.linspace(0, duration, steps)

        for i in range(repeat):
            if not self.ser.is_open:
                self.ser.open()

            self.ser.write(bytes(cmd, "ascii"))
            channel_readings = {ac: list() for ac in channels}

            try:
                if not self.ser.is_open:
                    self.ser.open()
                time.sleep(0.1)
                while self.ser.in_waiting > 15 or len(channel_readings[channels[0]]) < steps:
                    new_readings = []
                    for channel in channels:
                        buffer = ""
                        waiting = self.ser.in_waiting
                        if waiting > 1000 + 15:
                            buffer = self.ser.read(1000)
                        elif self.ser.in_waiting > 200+15:
                            buffer = self.ser.read(200)
                        else:
                            buffer = self.ser.read(2)

                        info = [buffer[i:i+2]
                                for i in range(0, len(buffer), 2)]

                        for two_b in info:
                            int_val = FastDAC.two_bytes_to_int(two_b)
                            voltage_reading = FastDAC.map_int16_to_mV(int_val)
                            new_readings.append(voltage_reading)

                    channel_readings[channel] += new_readings
                    if TimeSeries_fig is not None:
                        scatter = TimeSeries_fig.data[0]
                        with TimeSeries_fig.batch_update():
                            scatter.x += tuple(x_array[len(scatter.x)
                                               :len(scatter.x) + len(new_readings)])
                            scatter.y += tuple(new_readings)

            except Exception as e:
                print(e)
                self.ser.close()
                raise

            if PDS_fig is not None:
                PDS_fig.add_scatter(x=[],
                                    y=[],
                                    line=dict(width=0.5)
                                    )
                scatter = PDS_fig.data[i]
                with PDS_fig.batch_update():
                    f, Pxx_den = signal.welch(
                        channel_readings[channels[0]], fs=measure_freq,)
                    scatter.x = tuple(f)
                    scatter.y = tuple(10*np.log10(Pxx_den/1))
                    # scatter.y = tuple(Pxx_den)

            self.STOP()
            data = self.ser.readline()
            print(data)

            self.ser.close()
        logging.debug('Exiting')


if __name__ == "__main__":
    import plotly.graph_objs as go
    from threading import Thread, Timer

    fd = FastDAC("COM3", baudrate=1750000, timeout=1, verbose=True)

    fig = go.FigureWidget(data=[go.Scatter(x=[], y=[])])
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Voltage",
    )

    plot = Thread(name="ReadVersusTime",
                  target=fd.read_vs_time, args=(fig, 1, [1, ]),)
    plot.start()
    fig.show()
