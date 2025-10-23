# Copyright 2014-2021 Keysight Technologies
# Copyright 2025-2025 University of British Columbia QSTL
#!/usr/bin/env python
import sys
sys.path.append('C:\Program Files\Keysight\SD1\Libraries\Python')

from BaseDriver import LabberDriver, Error, IdError
import keysightSD1

import numpy as np
import os, time
import filelock


class TimeoutError(Error):
    def __init__(self, resource_name, timeout):
        self.resource_name = resource_name
        self.timeout = timeout

    def __str__(self):
        return f'Driver timeout waiting {self.timeout} seconds for another process to release resource {self.resource_name}. ' +\
            'Try increasing this driver\'s timeout in the \"advanced interface settings\" section of the \"Communication\" settings'

class Lock(filelock.FileLock):
    """
    Subclass FileLock to augment error message during timeout

    """

    def acquire(self):
        try:
            ret = super().acquire()
        except filelock.Timeout:
            resource_name = os.path.split(self.lock_file)[-1][:-5] # remove path and .lock extension
            raise TimeoutError(resource_name, self.timeout) from None

        return ret


class Driver(LabberDriver):
    """ This class implements the Keysight PXI digitizer"""
    qstl_pxi_digitizer_k7z = os.path.join(os.path.dirname(__file__), 'bitstreams',
                             'qstl_digitizer.k7z')
    factory_k7z = os.path.join(os.path.dirname(__file__), 'bitstreams',
                               'default_M3102A_ch4_clf_k41_BSP_02_02_06.k7z')

    def get_lock(self, chassis, slot, **kwargs):
        # return a lock file name for that module
        timeout = kwargs.pop('timeout', self.timeout_ms/1e3)
        fn = 'pxi_module_{}-{}.lock'.format(chassis, slot)
        full_fn = os.path.join(self.lock_directory, fn)
        l = Lock(full_fn, timeout=timeout, **kwargs)
        return l

    def load_sandbox(self, reset=False):
        if reset:
            fn = self.factory_k7z
        else:
            fn = self.qstl_pxi_digitizer_k7z
        self.log('Loading bitfile {}'.format(fn), level=30)
        with self.lock:
            error = self.dig.FPGAload(fn)
        if error < 0:
            message = keysightSD1.SD_Error.getErrorMessage(error)
            raise Error(f'Error loading bitfile {fn}: {message}')

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # set time step and resolution
        self.nBit = 16
        self.bitRange = float(2**(self.nBit-1)-1)
        # timeout
        self.timeout_ms = int(1000 * self.dComCfg['Timeout'])
        self.lock_directory = self.dPrefs['Temporary items']
        # get PXI chassis
        self.chassis = int(self.dComCfg.get('PXI chassis', 1))
        self.slot = int(self.comCfg.address)
        # set up Lock
        self.lock = self.get_lock(self.chassis, self.slot)
        # create AWG instance
        self.dig = keysightSD1.SD_AIN()
        with self.lock:
            AWGPart = self.dig.getProductNameBySlot(self.chassis, self.slot)
            serial_no = self.dig.getSerialNumberBySlot(self.chassis, self.slot)
        self.log('Serial:', serial_no)
        if not isinstance(AWGPart, str):
            raise Error('Unit not available')
        # check that model is supported
        dOptionCfg = self.dInstrCfg['options']
        for validId, validName in zip(dOptionCfg['model_id'], dOptionCfg['model_str']):
            if AWGPart.find(validId)>=0:
                # id found, stop searching
                break
        else:
            # loop fell through, raise ID error
            raise IdError(AWGPart, dOptionCfg['model_id'])
        # set model
        self.setModel(validName)
        # sampling rate and number of channles is set by model
        if validName in ('M3102', 'M3302'):
            # 500 MHz models
            self.dt = 2E-9
            self.nCh = 4
        else:
            # assume 100 MHz for all other models
            self.dt = 10E-9
            self.nCh = 4
        # create list of sampled data
        self.lTrace = [np.array([])] * self.nCh
        with self.lock:
            self.dig.openWithSlot(AWGPart, self.chassis, self.slot)
            # get hardware version - changes numbering of channels
            hw_version = self.dig.getHardwareVersion()
            self.log('Digitizer Hardware Version: {}'.format(hw_version) )
            self.log('Digitizer Firmware Version: {}'.format(self.dig.getFirmwareVersion()) )
        if isinstance(hw_version, str):
            hw_version = int(hw_version.split('.')[0])
        if hw_version >= 4:
            # KEYSIGHT - channel numbers start with 1
            self.ch_index_zero = 1
        else:
            # SIGNADYNE - channel numbers start with 0
            self.ch_index_zero = 0

        self.log('Loading QSTL PXI Digitizer bitstream')
        self.load_sandbox()

        self.log('Get accum_init register')   
        self.accum_init_reg = self.dig.FPGAgetSandBoxRegister('HostRegBank_accum_init')
        if isinstance(self.accum_init_reg, int):
            message = keysightSD1.SD_Error.getErrorMessage(self.accum_init_reg)
            raise Error(f'Error in opening a register HostRegBank_accum_init: {message}')
        self.accum_init()

        self.log('Get accum_num register')
        self.accum_num_reg = self.dig.FPGAgetSandBoxRegister('HostRegBank_accum_num')
        if isinstance(self.accum_num_reg, int):
            message = keysightSD1.SD_Error.getErrorMessage(self.accum_num_reg)
            raise Error(f'Error in opening a register HostRegBank_accum_num: {message}')

        self.log('Get accum_length register')
        self.accum_length_reg = self.dig.FPGAgetSandBoxRegister('HostRegBank_accum_length')
        if isinstance(self.accum_length_reg, int):
            message = keysightSD1.SD_Error.getErrorMessage(self.accum_length_reg)
            raise Error(f'Error in opening a register HostRegBank_accum_length: {message}')
    
    def accum_init(self) -> None:
        self.log('Initialize TraceAccum')   
        error = self.accum_init_reg.writeRegisterInt32(1)
        if error < 0:
            message = keysightSD1.SD_Error.getErrorMessage(error)
            raise Error(f'Error in initiating TraceAccum HostRegBank_accum_init: {message}')
        
        error = self.accum_init_reg.writeRegisterInt32(0)
        if error < 0:
            message = keysightSD1.SD_Error.getErrorMessage(error)
            raise Error(f'Error in initiating TraceAccum HostRegBank_accum_init: {message}')

    def accum_num(self, num: int) -> None:
        self.log('Initialize TraceAccum')   
        error = self.accum_num_reg.writeRegisterInt32(num)
        if error < 0:
            message = keysightSD1.SD_Error.getErrorMessage(error)
            raise Error(f'Error in initiating TraceAccum HostRegBank_accum_num: {message}')
    
    def accum_length(self, samples: int) -> None:
        self.log('Initialize TraceAccum')   
        error = self.accum_length_reg.writeRegisterInt32(samples)
        if error < 0:
            message = keysightSD1.SD_Error.getErrorMessage(error)
            raise Error(f'Error in initiating TraceAccum HostRegBank_accum_num: {message}')

    def getHwCh(self, n):
        """Get hardware channel number for channel n. n starts at 0"""
        return n + self.ch_index_zero

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # do not check for error if close was called with an error
        try:
            # flush all memory
            for n in range(self.nCh):
                self.log('Close ch:', n, self.dig.DAQflush(self.getHwCh(n)))
            # close instrument
            with self.lock:
                self.dig.close()
        except:
            # never return error here
            pass


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # start with setting local quant value
        quant.setValue(value)
        # check if channel-specific, if so get channel + name
        if quant.name.startswith('Ch') and len(quant.name)>6:
            ch = int(quant.name[2]) - 1
            name = quant.name[6:]
        else:
            ch, name = None, ''
        # proceed depending on command
        if quant.name in ('External Trig Source', 'External Trig Config',
                          'Trig Sync Mode'):
            extSource = int(self.getCmdStringFromValue('External Trig Source'))
            trigBehavior = int(self.getCmdStringFromValue('External Trig Config'))
            sync = int(self.getCmdStringFromValue('Trig Sync Mode'))
            with self.lock:
                self.dig.DAQtriggerExternalConfig(0, extSource, trigBehavior, sync)
        elif quant.name in ('Trig I/O', ):
            # get direction and sync from index of comboboxes
            direction = int(self.getCmdStringFromValue('Trig I/O'))
            with self.lock:
                self.dig.triggerIOconfig(direction)
        elif quant.name in ('Analog Trig Channel', 'Analog Trig Config', 'Trig Threshold'):
            # get trig channel
            trigCh = self.getValueIndex('Analog Trig Channel')
            mod = int(self.getCmdStringFromValue('Analog Trig Config'))
            threshold = self.getValue('Trig Threshold')
            with self.lock:
                self.dig.channelTriggerConfig(self.getHwCh(trigCh), mod, threshold)
        elif name in ('Range', 'Impedance', 'Coupling'):
            # set range, impedance, coupling at once
            rang = self.getRange(ch)
            imp = int(self.getCmdStringFromValue('Ch%d - Impedance' % (ch + 1)))
            coup = int(self.getCmdStringFromValue('Ch%d - Coupling' % (ch + 1)))
            with self.lock:
                self.dig.channelInputConfig(self.getHwCh(ch), rang, imp, coup)
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # check if channel-specific, if so get channel + name
        if quant.name.startswith('Ch') and len(quant.name) > 6:
            ch = int(quant.name[2]) - 1
            name = quant.name[6:]
        else:
            ch, name = None, ''

        if name == 'Signal':
            if self.isHardwareLoop(options):
                return self.getSignalHardwareLoop(ch, quant, options)
            # get traces if first call
            if self.isFirstCall(options):
                # don't arm if in hardware trig mode
                self.getTraces(bArm=(not self.isHardwareTrig(options)))
            # return correct data
            value = quant.getTraceDict(self.lTrace[ch], dt=self.dt)
        else:
            # for all others, return local value
            value = quant.getValue()

        return value


    def performArm(self, quant_names, options={}):
        """Perform the instrument arm operation"""
        # make sure we are arming for reading traces, if not return
        signal_names = ['Ch%d - Signal' % (n + 1) for n in range(4)]
        signal_arm = [name in signal_names for name in quant_names]
        if not np.any(signal_arm):
            return

        # arm by calling get traces
        if self.isHardwareLoop(options):
            # in hardware looping, number of records is set by the hw loop
            (seq_no, n_seq) = self.getHardwareLoopIndex(options)
            nSample = int(self.getValue('Number of samples'))
            n_accum = int(self.getValue('Number of accumulation'))
            self.accum_init()
            self.accum_length(nSample)
            self.accum_num(n_accum)
            self.accum_init()

            # arm instrument, then report completed to allow client to continue
            self.reportStatus('Digitizer - Waiting for signal')
            # Setup DAQ
            self.getTraces(bArm=True, bMeasure=False, n_seq = n_seq)
            # Report Arm is done
            self.report_arm_completed()

            # directly start collecting data (digitizer buffer is limited)
            self.getTraces(bArm=False, bMeasure=True)

            # re-shape data and place in trace buffer
            self.reshaped_traces = []
            for trace in self.lTrace:
                if len(trace) > 0:
                    trace = trace.reshape((n_seq, nSample))
                self.reshaped_traces.append(trace)

        else:
            raise Error('Only Hardware loop is supported')


    def getTraces(self, bArm=True, bMeasure=True, n_seq=1):
        """Get all active traces"""
        # find out which traces to get
        lCh = []
        iChMask = 0
        # get current settings
        nPts = int(self.getValue('Number of samples'))
        nCyclePerCall = int(self.getValue('Records per Buffer'))
        n_accum = int(self.getValue('Number of accumulation'))
        n_reps = int(self.getValue('Number of repetition'))

        nSeg = n_seq * n_reps

        for n in range(self.nCh):
            if self.getValue('Ch%d - Enabled' % (n + 1)):
                lCh.append(n)
                iChMask += 2**n

        # trigger delay is in 1/sample rate
        # adding 20 ns to match demod latency
        nTrigDelay = int(round( ( self.getValue('Trig Delay') + 20e-9 ) / self.dt)) 

        if bArm:
            with self.lock:
                # clear old data
                self.accum_init()
                self.dig.DAQflushMultiple(iChMask)
                self.lTrace = [np.array([])] * self.nCh
                # configure trigger for all active channels
                for nCh in lCh:
                    # init data. Get repetition * number of samples of data
                    self.lTrace[nCh] = np.zeros(nPts)
                    # channel number depens on hardware version
                    ch = self.getHwCh(nCh)
                    # extra config for trig mode
                    if self.getValue('Trig Mode') == 'Digital trigger':
                        (extSource, trigBehavior, sync) = (
                            int(self.getCmdStringFromValue('External Trig Source')),
                            int(self.getCmdStringFromValue('External Trig Config')),
                            int(self.getCmdStringFromValue('Trig Sync Mode'))
                        )
                        self.dig.DAQtriggerExternalConfig(ch, extSource, trigBehavior, sync)
                        self.dig.DAQdigitalTriggerConfig(ch, extSource, trigBehavior)

                    elif self.getValue('Trig Mode') == 'Analog channel':
                        digitalTriggerMode= 0
                        digitalTriggerSource = 0
                        trigCh = self.getValueIndex('Analog Trig Channel')
                        analogTriggerMask = 2**trigCh
                        self.dig.DAQtriggerConfig(ch, digitalTriggerMode, digitalTriggerSource, analogTriggerMask)

                    # config daq and trig mode
                    trigMode = int(self.getCmdStringFromValue('Trig Mode'))
                    self.dig.DAQconfig(ch, nPts, nSeg, nTrigDelay, trigMode)
                # start acquiring data
                self.dig.DAQstartMultiple(iChMask)

        # return if not measure
        if not bMeasure:
            return
        # Calculate scale value for each channel
        lScale = [(self.getRange(ch) / self.bitRange) for ch in range(self.nCh)]
        # capture traces one by one
        for nCh in lCh:
            # channel number depens on hardware version
            ch = self.getHwCh(nCh)
            self.reportStatus(f'Digitizer {nCh} getting traces...')
            data = self.DAQread(
                self.dig,
                ch,
                nPts * nSeg,
                10000
            )
            data = data.reshape(n_seq, n_reps, -1).mean(axis = 1)
            data = data.reshape(-1)
            self.log(f'Data = {data}',level=20)
            # stop if no data
            if data.size == 0:
                return
            # adjust scaling to account for summing averages
            scale = lScale[nCh] * (1 / n_accum)
            data = np.repeat(data, 5)
            # convert to voltage, add to total average
            self.lTrace[nCh] += data * scale

        # lT.append('N: %d, Tot %.1f ms' % (n, 1000 * (time.perf_counter() - t0)))

    def getRange(self, ch):
        """Get channel range, as voltage.  Index start at 0"""
        rang = float(self.getCmdStringFromValue('Ch%d - Range' % (ch + 1)))
        # range depends on impedance
        if self.getValue('Ch%d - Impedance' % (ch + 1)) == 'High':
            rang = rang * 2
            # special case if range is .25, 0.5, or 1, scale to 0.2, .4, .8
            if rang < 1.1:
                rang *= 0.8
        return rang


    def DAQread(self, dig, nDAQ, nPoints, timeOut):
        """Read data diretly to numpy array"""
        if dig._SD_Object__handle > 0:
            if nPoints > 0:
                data = (keysightSD1.c_short * nPoints)()
                nPointsOut = dig._SD_Object__core_dll.SD_AIN_DAQread(dig._SD_Object__handle, nDAQ, data, nPoints, timeOut)
                if nPointsOut > 0:
                    data = np.frombuffer(data, dtype=np.uint16, count=nPoints)
                    step = 5
                    n = len(data) // step
                    high = data[1::step]
                    low = data[::step]
                    x = ((high.astype(np.uint32) << 16) | low.astype(np.uint32)).astype(np.int32)
                    return x
                else:
                    return np.array([], dtype=np.int32)
            else:
                return keysightSD1.SD_Error.INVALID_VALUE
        else:
            return keysightSD1.SD_Error.MODULE_NOT_OPENED


    def getSignalHardwareLoop(self, ch, quant, options):
        """Get data from round-robin type averaging"""
        (seq_no, n_seq) = self.getHardwareLoopIndex(options)
        # after getting data, pick values to return
        return quant.getTraceDict(self.reshaped_traces[ch][seq_no], dt=self.dt)


if __name__ == '__main__':
    pass
