#Capillary destructive testing (pre-shutter only)

import datetime

def timed_shutter_pre(exp_time, *, md=None):
    '''Opens the pre-shutter for a defined exposure time.
    Prerequisites: FE photon shutter and any downstream shutters are open

    Parameter
    ---------
    exp_time: float
        Exposure time in seconds
    '''
    dets = [shutter]

    if md is None:
        md = {}

    md['exp_time'] = exp_time

    @bpp.run_decorator(md={'plan_name': 'timed_shutter_pre'})
    def inner_plan():
        yield from bps.clear_checkpoint()
        
        #check state of FE shutter
        if pps_shutter.status.get() == 'Not Open' and EpicsSignalRO(pps_shutter.enabled_status.pvname).get() == 1:
            raise Exception("The photon shutter is not open. Open it first!")

        # open the shutter
        yield from bps.abs_set(shutter, 'Open', wait=True)
        yield from bps.trigger_and_read(dets)

        print('Pre-shutter opened')
        print("({}) Exposing for {:.2f} s".format(datetime.datetime.now().strftime(_time_fmtstr), exp_time))

       # wait
        yield from bps.sleep(exp_time)

        # close the shutter
        yield from bps.abs_set(shutter, 'Close', wait=True)
        print('closed pre-shutter')
        yield from bps.trigger_and_read(dets)

    def clean_up():
        yield from bps.abs_set(shutter, 'Close', wait=True)


    yield from bpp.finalize_wrapper(inner_plan(), clean_up())

def timed_shutter(exp_time, *, md=None):
    '''Opens the PPS shutter and pre-shutter for a defined exposure time.
    Prerequisites: Any other downstream shutters are open

    Parameter
    ---------
    exp_time: float
        Exposure time in seconds
    '''
    dets = [pps_shutter, shutter]

    if md is None:
        md = {}

    md['exp_time'] = exp_time

    @bpp.run_decorator(md={'plan_name': 'timed_shutter'})
    def inner_plan():
        yield from bps.clear_checkpoint()
        
        # open the PPS and preshutters
        if EpicsSignalRO(pps_shutter.enabled_status.pvname).get() == 0:
            raise Exception("Can't open FE shutter! Check that the hutch is interlocked and the shutter is enabled.")
        
        yield from bps.abs_set(pps_shutter, 'Open', wait=True)
        print('FE shutter opened')
        yield from bps.sleep(1)
        
        yield from bps.abs_set(shutter, 'Open', wait=True)
        yield from bps.trigger_and_read(dets)

        print('Pre-shutter opened')
        print("({}) Exposing for {:.2f} s".format(datetime.datetime.now().strftime(_time_fmtstr), exp_time))

       # wait
        yield from bps.sleep(exp_time)

        # close the shutters
        yield from bps.abs_set(shutter, 'Close', wait=True)
        print('closed pre-shutter')
        yield from bps.sleep(1)
        yield from bps.abs_set(pps_shutter, 'Close', wait=True)
        print('closed FE shutter')
        yield from bps.trigger_and_read(dets)

    def clean_up():
        yield from bps.abs_set(shutter, 'Close', wait=True)
        yield from bps.abs_set(pps_shutter, 'Close', wait=True)

    yield from bpp.finalize_wrapper(inner_plan(), clean_up())

#Functions to actuate BIFS sample shutter

def timed_sam_shutter_fe(ss_exp_time, *, md=None):
    '''Opens the FE photon shutter, then the sample shutter for a defined time.
    Prerequisites: pre-shutter is open.
    
    Parameter
    ---------
    ss_exp_time: float
        Exposure time in seconds
    '''
    
    _md = {'plan_name': 'timed_sam_shutter_fe',
           'exp_time': ss_exp_time}
    _md.update(md or {})

    @bpp.run_decorator(md=_md)
    def inner_shutter_plan():
        #check state of FE shutter, raise exception if it is not enabled.
        #check state of pre-shutter, throw exception if it is not open
        if EpicsSignalRO(pps_shutter.enabled_status.pvname).get() == 0:
            raise Exception("Can't open photon shutter! Check that the hutch is interlocked and the shutter is enabled.")
        if pre_shutter.status.get() == 'Not Open':
            print("WARNING: Pre-shutter is not open. No X-rays will reach the sample.")
    
        #Open FE shutter, actuate sample shutter, then close FE shutter
        yield from bps.abs_set(pps_shutter, 'Open', wait=True)
        print('Photon shutter opened.')
        yield from bps.sleep(1)
    
        yield from bps.abs_set(diode_shutter, 'Open', wait=True)
        print(f"Opening DIODE sample shutter for a {ss_exp_time} second(s) exposure.")
        yield from bps.sleep(ss_exp_time)

        yield from bps.abs_set(diode_shutter, 'Close', wait=True)
        print("Closed DIODE sample shutter.")
        yield from bps.sleep(1)
        yield from bps.abs_set(pps_shutter, 'Close', wait=True)
        print('Closed Photon shutter.')
   
    return (yield from inner_shutter_plan())

def timed_sam_shutter(ss_exp_time, *, md=None):
    '''Opens the sample shutter for a defined exposure time.
    Prerequisites: FE photon shutter and pre-shutter are open

    Parameter
    ---------
    ss_exp_time: float
        Exposure time in seconds
    '''

    _md = {'plan_name': 'timed_sam_shutter',
           'exp_time': ss_exp_time}
    _md.update(md or {})

    @bpp.run_decorator(md=_md)
    def inner_shutter_plan():
        
        #Check state of PPS and pre_shutters, warn user but don't open.

        if EpicsSignalRO(pps_shutter.enabled_status.pvname).get() == 0:
            print("WARNING: Photon shutter is not enabled. No beam will reach sample.")
        if pps_shutter.status.get() == 'Not Open':
            print("WARNING: Photon shutter is closed. No beam will reach sample.")
        if pre_shutter.status.get() == 'Not Open':
            print("WARNING: Pre-shutter is closed. No beam will reach sample.")
        
        #Open sample shutter for specified time
        yield from bps.abs_set(diode_shutter, 'Open')
        print(f"Opening DIODE sample shutter for a {ss_exp_time} second(s) exposure.")
        yield from bps.sleep(ss_exp_time)
        yield from bps.abs_set(diode_shutter, 'Close')
        print("Closed DIODE sample shutter.")
    
    return(yield from inner_shutter_plan())

#Functions to actuate Uniblitz fast shutter

def timed_uniblitz(fire_time, *, md=None):
    '''Opens the Uniblitz shutter for a defined exposure time.
    Prerequisites: All upstream shutters are open

    Parameter
    ---------
    fire_time: float
        Exposure time in seconds
    '''

    _md = {'plan_name': 'timed_uniblitz',
           'exp_time': fire_time}
    _md.update(md or {})

    @bpp.run_decorator(md=_md)
    def inner_uniblitz_plan():
        
        #Check state of upstream shutters, warn user but don't open.

        if EpicsSignalRO(pps_shutter.enabled_status.pvname).get() == 0:
            print("WARNING: Photon shutter is not enabled. No beam will reach sample.")
        if pps_shutter.status.get() == 'Not Open':
            print("WARNING: Photon shutter is closed. No beam will reach sample.")
        if pre_shutter.status.get() == 'Not Open':
            print("WARNING: Pre-shutter is closed. No beam will reach sample.")
        if diode_shutter.status_closed.get() == 1:
            print("WARNING: Sample shutter is closed. No beam will reach sample.")

        
        yield from bps.mv(dg, fire_time)        #set Uniblitz opening time
        yield from bps.mv(dg.fire, 1)           #fire Uniblitz
        yield from bps.sleep(fire_time*1.1)     #wait for shutter to finish
        if fire_time <= 1:
            print(f"Fired Uniblitz shutter for {fire_time*1000} millseconds.")
        else:
            print(f"Fired Uniblitz shutter for {fire_time} seconds.")
    
    return(yield from inner_uniblitz_plan())

def timed_uniblitz_ss(fire_time, *, md=None):
    '''Opens the sample shutter, then Uniblitz shutter for a defined exposure time.
    Prerequisites: FE photon shutter and pre-shutter are open

    Parameter
    ---------
    fire_time: float
        Exposure time in seconds
    '''
    _md = {'plan_name': 'timed_uniblitz_ss',
           'exp_time': fire_time}
    _md.update(md or {})

    @bpp.run_decorator(md=_md)
    def inner_uniblitz_plan():
        
        #Check state of PPS and pre shutters, warn user but don't open.
        
        if EpicsSignalRO(pps_shutter.enabled_status.pvname).get() == 0:
            print("WARNING: Photon shutter is not enabled. No beam will reach sample.")
        if pps_shutter.status.get() == 'Not Open':
            print("WARNING: Photon shutter is closed. No beam will reach sample.")
        if pre_shutter.status.get() == 'Not Open':
            print("WARNING: Pre-shutter is closed. No beam will reach sample.")

        yield from bps.mv(diode_shutter, 'Open')
        print("Opened DIODE sample shutter.")
        if fire_time <= 0.5:                    #sample-shutter sleep for short exposure times   
            yield from bps.sleep(0.5)               
        #yield from timed_uniblitz(fire_time)

        yield from bps.mv(dg, fire_time)        #set Uniblitz opening time
        yield from bps.mv(dg.fire, 1)           #fire Uniblitz
        yield from bps.sleep(fire_time*1.1)     #wait for shutter to finish
        if fire_time <= 1:
            print(f"Fired Uniblitz shutter for {fire_time*1000} millseconds.")
        else:
            print(f"Fired Uniblitz shutter for {fire_time} seconds.")
        if fire_time <= 0.5:
            yield from bps.sleep(0.5)
        yield from bps.mv(diode_shutter, 'Close')
        print("Closed DIODE sample shutter.")

    return(yield from inner_uniblitz_plan())

def timed_uniblitz_fe(fire_time, *, md=None):
    '''Opens the PPS + sample shutters, then Uniblitz shutter for a defined exposure time.
    Prerequisites: Pre-shutter is open

    Parameter
    ---------
    fire_time: float
        Exposure time in seconds
    '''
    _md = {'plan_name': 'timed_uniblitz_fe',
           'exp_time': fire_time}
    _md.update(md or {})

    @bpp.run_decorator(md=_md)
    def inner_uniblitz_plan():
        
        #Check state of PPS and pre-shutters
        #Raise exception of PPS shutter is disabled; warn user about pre-shutter but don't open.
        
        if EpicsSignalRO(pps_shutter.enabled_status.pvname).get() == 0:
            raise Exception("Can't open photon shutter! Check that the hutch is interlocked and the shutter is enabled.")
        if pre_shutter.status.get() == 'Not Open':
            print("WARNING: Pre-shutter is closed. No beam will reach sample.")

        yield from bps.abs_set(pps_shutter, 'Open', wait=True)
        print('Photon shutter opened.')
        yield from bps.sleep(1)

        yield from bps.mv(diode_shutter, 'Open')
        print("Opened DIODE sample shutter.")
        if fire_time <= 0.5:                    #sample-shutter sleep for short exposure times   
            yield from bps.sleep(0.5)               
        #yield from timed_uniblitz(fire_time)

        yield from bps.mv(dg, fire_time)        #set Uniblitz opening time
        yield from bps.mv(dg.fire, 1)           #fire Uniblitz
        yield from bps.sleep(fire_time*1.1)     #wait for shutter to finish
        if fire_time <= 1:
            print(f"Fired Uniblitz shutter for {fire_time*1000} millseconds.")
        else:
            print(f"Fired Uniblitz shutter for {fire_time} seconds.")
        if fire_time <= 0.5:
            yield from bps.sleep(0.5)
        yield from bps.mv(diode_shutter, 'Close')
        print("Closed DIODE sample shutter.")

        yield from bps.sleep(1)
        yield from bps.abs_set(pps_shutter, 'Close', wait=True)
        print('Closed photon shutter.')

    return(yield from inner_uniblitz_plan())
