from __future__ import print_function, division
import os
import numpy as np
import moose

from spspine import constants, logutil
from spspine.util import NamedList
log = logutil.Logger()

#Suggested specification of calcium buffers
#Similar approach for calcium pumps, but they need Km and power, and location dependent Vmax
cabuf_params=NamedList('cabuf_params', 'bufname kf kb diffconst total bound')
NAME_CALCIUM='CaPool'

def CaProto(params):
    if not moose.exists('/library'):
        lib = moose.Neutral('/library')
    #if the proto as been created already, this will not create a duplicate
    poolproto = moose.CaConc('/library/'+NAME_CALCIUM)
    poolproto.CaBasal = params.CaBasal
    poolproto.ceiling = 1
    poolproto.floor = 0.0
    poolproto.thick = params.CaThick
    poolproto.tau = params.CaTau
    return poolproto

def addCaPool(model, comp):
    caproto = moose.element('/library/' + NAME_CALCIUM)
    capool = moose.copy(caproto, comp, NAME_CALCIUM)[0]
    length=moose.Compartment(comp).length
    diam=moose.Compartment(comp).diameter
    if length == 0:
        SA = np.pi * diam ** 2 #create the calcium pools in each compartment
        rad = diam / 2
        vol = (4/3) * np.pi * rad ** 3
        rad_core= rad - capool.thick
        core_vol= (4/3) * np.pi * rad_core ** 3
        shell_vol = vol - core_vol
        capool.B = 1 / (constants.Faraday * shell_vol * 2) / model.CaPlasticityParams.BufCapacity
    else :
        SA = np.pi * length * diam
        vol = SA * capool.thick
        capool.B = 1 / (constants.Faraday*vol*2) / model.CaPlasticityParams.BufCapacity
    log.debug('CALCIUM {} {} {} {} {}', capool.path, length,diam,capool.thick,vol)
    return capool

def connectVDCC_KCa(model, ghkYN,comp,capool):
    if ghkYN:
        ghk=moose.element(comp.path + '/ghk')
        moose.connect(capool,'concOut',ghk,'set_Cin')
        moose.connect(ghk,'IkOut',capool,'current')
        log.debug('CONNECT GHK {.path} to Ca {.path}', ghk, capool)
        #connect them to the channels
    chan_list = (moose.wildcardFind(comp.path + '/#[TYPE=HHChannel]') +
                 moose.wildcardFind(comp.path + '/#[TYPE=HHChannel2D]'))
    for chan in chan_list:
        if model.Channels[chan.name].calciumPermeable:
            if ghkYN == 0:
                # do nothing if ghkYesNo==1, since already connected the single GHK object
                m = moose.connect(chan, 'IkOut', capool, 'current')
        if model.Channels[chan.name].calciumDependent:
            m = moose.connect(capool, 'concOut', chan, 'concen')
            log.debug('channel message {} {} {}', chan.path, comp.path, m)
 
def connectNMDA(nmdachans, ghkYesNo):
    for chan in nmdachans:
        caname = os.path.dirname(chan.path) + '/'+NAME_CALCIUM
        capool = moose.element(caname)
        log.debug('CONNECT {.path} to {.path}', chan, capool)
        moose.connect(chan, 'ICaOut', capool, 'current')
