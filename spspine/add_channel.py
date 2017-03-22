import moose 
import numpy as np
from spspine import logutil
log = logutil.Logger()

def addOneChan(chanpath,gbar,comp,ghkYN, ghk=None, calciumPermeable=False):
    length = moose.Compartment(comp).length
    diam = moose.Compartment(comp).diameter
    SA = np.pi*length*diam
    if length == 0:
         SA = np.pi*diam**2
         log.info('Check RA for spherical compartment',comp.name)
    proto = moose.element('/library/'+chanpath)
    chan = moose.copy(proto, comp, chanpath)[0]
    chan.Gbar = gbar * SA
    #If we are using GHK AND it is a calcium channel, connect it to GHK
    if ghkYN and calciumPermeable:
        ghk = moose.element(comp.path+'/ghk')
        moose.connect(chan,'permeability',ghk,'addPermeability')
        m = moose.connect(comp,'VmOut',chan,'Vm')
    else:
        m = moose.connect(comp,'VmOut',chan,'Vm')
        m = moose.connect(chan, 'channelOut', comp, 'handleChannel')
    log.debug('channel message {.path} {.path} {}', chan, comp, m)
    print(chan,chan.Gbar)
