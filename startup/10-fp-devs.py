#Ophyd objects for XFP endstation devices.
#Includes: M50 pump, fraction collection, PHD2000 syringe pump
#Also incldues: DG535 delay gen., SR630 temp monitor, and quadEM.
#Motor classes are defined in 10-motors.py

import time
import datetime
from ophyd import (EpicsMotor, Device,
                   Component as Cpt, EpicsSignal,
                   EpicsSignalRO, DeviceStatus)

class SamplePump(Device):
    vel = Cpt(EpicsSignal, 'Val:Vel-SP')
    vol = Cpt(EpicsSignal, 'Val:Vol-SP')

    sts = Cpt(EpicsSignal, 'Sts:Flag-Sts')

    slew_cmd = Cpt(EpicsSignal, 'Cmd:Slew-Cmd')
    stop_cmd = Cpt(EpicsSignal, 'Cmd:Stop-Cmd')
    movr_cmd = Cpt(EpicsSignal, 'Cmd:MOVR-Cmd')

    sts = Cpt(EpicsSignal, 'Sts:Flag-Sts', string=True)

    def kickoff(self):
        # The timeout controls how long to wait for the pump
        # to report it started working before assuming it is broken
        st = DeviceStatus(self, timeout=1.5)
        enums = self.sts.enum_strs
        def inner_cb(value, old_value, **kwargs):

            old_value, value = enums[int(old_value)], enums[int(value)]
            # print('ko', old_value, value, time.time())
            if value == 'Moving':
                st._finished(success=True)
                self.sts.clear_sub(inner_cb)

        self.sts.subscribe(inner_cb)
        self.slew_cmd.put(1)
        return st

    def complete(self):
        st = DeviceStatus(self)
        enums = self.sts.enum_strs
        def inner_cb(value, old_value, **kwargs):
            old_value, value = enums[int(old_value)], enums[int(value)]
            # print('cp', kwargs['timestamp'], old_value, value, value == 'Stopped')
            if value == 'Stopped':
                st._finished(success=True)
                self.sts.clear_sub(inner_cb)

        self.sts.subscribe(inner_cb)

        self.stop_cmd.put(1)
        return st

    def stop(self):
        self.stop_cmd.put(1)

sample_pump = SamplePump('XF:17BMA-ES:1{Pmp:02}',
                         name='sample_pump',
                         read_attrs=['vel', 'sts'])

class FractionCollector(Device):
    run = Cpt(EpicsSignal, 'Run-Cmd')
    end = Cpt(EpicsSignal, 'Stop-Cmd')
    stp = Cpt(EpicsSignal, 'Pause-Cmd')
    tube = Cpt(EpicsSignal, 'RTube-RB', write_pv='RTube-SP')
    hm = Cpt(EpicsSignal, 'Home-Cmd')
    ftime = Cpt(EpicsSignal, 'Time:FSize-RB', write_pv='Time:FSize-SP')
    r1last = Cpt(EpicsSignal, 'Tube:R1Last-RB', write_pv='Tube:R1Last-SP')
    r2last = Cpt(EpicsSignal, 'Tube:R2Last-RB', write_pv='Tube:R2Last-SP')
    #pattern 1 = standard s-pattern; pattern 2 = left to right
    pattern = Cpt(EpicsSignal, 'Type:Pattn-Sel', write_pv='Type:Pattn-Sel')
    # valve 0 = waste, valve 1 = collect
    valve = Cpt(EpicsSignal, 'Vlv-Sel', write_pv='Vlv-Sel')
    # ftype 1 = time, ftype 2 = drops, ftype 3 = external counts
    ftype = Cpt(EpicsSignal, 'Type:Fraction-Sel', write_pv='Type:Fraction-Sel')

fc = FractionCollector('XF:17BM-ES:1{FC:1}', name='fc')

class Pump(Device):
    # This needs to be turned into a PV positioner
    mode = Cpt(EpicsSignal, 'Mode', string=True)
    direction = Cpt(EpicsSignal, 'Direction', string=True)

    diameter = Cpt(EpicsSignal, 'Diameter_RBV', write_pv='Diameter')
    infusion_rate = Cpt(AgressiveSignal, 'InfusionRate_RBV', write_pv='InfusionRate')
    run = Cpt(EpicsSignal, 'Run', string=True)
    state = Cpt(EpicsSignalRO, 'State_RBV', string=True)
    infusion_volume = Cpt(AgressiveSignal, 'InfusionVolume_RBV', write_pv='InfusionVolume')

    delivered = Cpt(EpicsSignalRO, 'Delivered_RBV')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._kickoff_st = None
        self._complete_st = None
        self.read_attrs = ['delivered']
        self.configuration_attrs = ['diameter', 'infusion_rate', 'infusion_volume']
    def clear_ko_cb(self):
        if self._clear_ko_cb is not None:
            try:
                self._clear_ko_cb()
            finally:
                self._clear_ko_cb = None

    def clear_cp_cb(self):
        pass

    def reset_state(self):
        self._kickoff_st = None

    def kickoff(self):
        # house keeping to make sure this is a valid command
        if self._kickoff_st is not None:
            raise RuntimeError('trying to kickoff before previous kickoff done')

        # set up local caches of pv information
        enums = self.state.enum_strs
        target = self.infusion_volume.get()

        # status objects
        self._complete_st = cp_st = DeviceStatus(self)
        self._kickoff_st = ko_st = DeviceStatus(self)


        def inner_cb_state(value, old_value, **kwargs):
            '''state changed based callback to identify starting
            '''
            old_value, value = enums[int(old_value)], enums[int(value)]

            if value == 'Interrupted':
                ko_st._finished(success=False)
                self.clear_ko_cb()

            if value in {'Infusing', 'Withdrawing'}:
                ko_st._finished(success=True)
                self.clear_ko_cb()

        def inner_complete_cb(value, old_value, **kwargs):
            '''State based callback to identify finishing
            '''
            old_value, value = enums[int(old_value)], enums[int(value)]

            if value == 'Idle' and old_value != 'Idle':
                cp_st._finished(success=True)
                self.clear_cp_cb()
                self.reset_state()

            if value == 'Interrupted':
                cp_st._finished(success=False)
                self.clear_cp_cb()
                self.reset_state()

        def inner_cb_delivered(value, **kwargs):
            '''volume based call back as a backup'''
            # TODO make this a smarter check!
            if abs(value - target) < .015:
                ko_st._finished(success=True)
                cp_st._finished(success=True)
                self.clear_ko_cb()
                self.clear_cp_cb()
                self.reset_state()

        def _clear_ko_cb():
            self.state.clear_sub(inner_cb_state)
            self.delivered.clear_sub(inner_cb_delivered)

        def _clear_cp_cb():
            self.state.clear_sub(inner_complete_cb)

        self._clear_ko_cb = _clear_ko_cb
        self._clear_cp_cb = _clear_cp_cb


        self.state.subscribe(inner_cb_state, run=False)
        self.delivered.subscribe(inner_cb_delivered, run=False)
        self.state.subscribe(inner_complete_cb, run=False)

        self.run.set('Run')
        return ko_st

    def complete(self):
        if self._complete_st is None:
            raise RuntimeError('trying to complete before kickingoff '
                               '(or you called complete twice)')
        st = self._complete_st
        self._complete_st = None
        self._kickoff_st = None
        return st

    def stop(self, success=False):
        if self._kickoff_st is not None:
            self._kickoff_st._finished(success=success)

        if self._complete_st is not None:
            self._complete_st._finished(success=success)

        self._complete_st = None
        self._kickoff_st = None
        self.run.set('Stop')


pump1 = Pump('XF:17BM-ES:1{Pmp:01}', name='food_pump')
spump = Pump('XF:17BM-ES:1{Pmp:01}', name='syringe_pump')

class DelayGenerator(Device):
    mode = Cpt(EpicsSignal, 'trigModeSetMO', write_pv='trigModeSetMO')
    exp_time = Cpt(EpicsSignal, 'bDelaySetAO', write_pv='bDelaySetAO')

    delay = Cpt(EpicsSignalRO, 'bDelayAI')
    delay_status = Cpt(EpicsSignalRO, 'bDelayAI.STAT')
    exp_time_status = Cpt(EpicsSignalRO, 'bDelaySetAO.STAT')
    fire = Cpt(EpicsSignal, 'genSingleShotTrigBO', write_pv='genSingleShotTrigBO')

    _complete_set = None
    
    def set(self, val, *, timeout=None, settle_time=None):
        cp_st = DeviceStatus(self)
        if val == self.delay.get():
            cp_st._finished()
            return cp_st
        
        self._complete_st = cp_st
        rekicking = False
        
        def stat_monitor(value, **kwargs):
            nonlocal rekicking
            
            if not rekicking and value:
                print('err', value)
                rekicking = True
                print('wait, then set to 0')
                sleep(5)
                self.exp_time.set(0)
                print('wait, then set to val')
                sleep(5)
                rekicking = False
                self.exp_time.set(val)
                print('rekicked')

        def stat_write_monitor(value, **kwargs):
            if value:
                print('delay generator write failed')
                sleep(5)
                self.exp_time.set(self.exp_time.get())                          
                
        self.delay_status.subscribe(stat_monitor, run=False)
        self.exp_time_status.subscribe(stat_write_monitor, run=False)
        
        def rb_monitor(value, **kwargs):
            nonlocal rekicking
            if rekicking:
                print('bail')
                return
            
            if np.isclose(value, val):
                self._complete_st = None
                self.delay_status.clear_sub(stat_monitor)
                self.delay.clear_sub(rb_monitor)
                self.exp_time_status.clear_sub(stat_write_monitor)
                cp_st._finished()
        self.delay.subscribe(rb_monitor, run=False)
        self.exp_time.set(val)
        
        return cp_st

    def stop(self, *, success):
        # TODO make this less brute force
        self.delay_status._reset_sub('value')
        self.delay._reset_sub('value')
        self.exp_time_status._reset_sub('value')

dg = DelayGenerator('XF:17BMA-ES:2{DG:1}', name = 'dg')


class SR630(Device):
#Note: Channels start at 0 (i.e. setting channel to 0 is actually choosing Ch1)
    channel = Cpt(EpicsSignal, 'rCurr_Chan', write_pv='wCurr_Chan')
    val = Cpt(EpicsSignalRO, 'rCurr_Measure')
    unit = Cpt(EpicsSignalRO, 'rCurr_Units', string=True)

tcm1 = SR630('XF:17BMA-ES:2{TCM:1}', name='tcm1', 
        read_attrs=['val'], configuration_attrs=['unit', 'channel'])
#pin_diode = SR630('XF:17BMA-ES:2{TCM:1}', name='pin_diode')


class QuadEM(Device):
#    ch1 = Cpt(EpicsSignalRO, 'EM180:Current1:MeanValue_RBV')
#    ch2 = Cpt(EpicsSignalRO, 'EM180:Current2:MeanValue_RBV')
    ch3 = Cpt(EpicsSignalRO, 'EM180:Current3:MeanValue_RBV')
#    ch4 = Cpt(EpicsSignalRO, 'EM180:Current4:MeanValue_RBV')

quad = QuadEM('XF:17BM-BI{EM:1}', name='quad', 
        read_attrs=['ch3'])

pin_diode = QuadEM('XF:17BM-BI{EM:1}', name='pin_diode')

# MR20190913: this 'diode' object below is misconfigured and causes a malformed
# PV names for QuadEM devices in 15-electrometer.py.
# See https://github.com/NSLS-II-XFP/profile_collection/pull/15 for details.
# diode = QuadEM('XF:17BM-BI{EM:BPM1}Current4:MeanValue_RBV', name = 'diode')


