#Do not define EREST_ACT or ELEAK here - they are in the .p file
# Contains maximal conductances, name of .p file, and some other parameters
# such as whether to use GHK, or whether to have real spines

import numpy as np

from moose_nerp.prototypes import util as _util

#if ghkYesNo=0 then ghk not implemented
#Note that you can use GHK without a calcium pool, it uses a default of 5e-5 Cin
if False: # param_sim.Config['ghkYN']:
    ghKluge=0.35e-6
else:
    ghKluge=1

#using 0.035e-9 makes NMDA calcium way too small, using single Tau calcium
ConcOut=2e-3     # default for GHK is 2e-3
Temp=30         # Celsius, needed for GHK objects, some channels

_neurontypes = None
def neurontypes(override=None):
    "Query or set names of neurontypes of each neuron created"
    global _neurontypes
    if override is None:
        return _neurontypes if _neurontypes is not None else sorted(Condset.keys())
    else:
        if any(key not in Condset.keys() for key in override):
            raise ValueError('unknown neuron types requested')
        _neurontypes = override

morph_file = {'ep':'EP_41comp.p'}
NAME_SOMA='soma'

#CONDUCTANCES

# helper variables to index the Conductance and synapses with distance
#soma spherical so x,y=0,0, 1e-6 means prox=soma
prox = (0,1e-6)
#med =  (0,50e-6)
dist = (1e-6, 1000e-6)
axon = (0.,1., 'axon')

_ep = _util.NamedDict(
    'ep',
    KDr={prox: 4, dist: 6, axon: 20}, #KDr is Kv2
    Kv3={prox: 600, dist: 70, axon: 1400},  
    KvF={prox: 100, dist: 100, axon: 100},  
    NaF={prox: 40000, dist: 400, axon: 40000}, 
    NaS={prox: 0.3, dist: 0.3, axon: 0.3},
    Ca={prox: 0.1, dist: 0.06, axon: 0},  
    HCN1={prox: 0.4, dist: 0.4, axon: 0}, 
    SKCa={prox: 2, dist: 0.15, axon: 0},  
    BKCa={prox: 0.1, dist: 0.1, axon: 0}, 
)


Condset  = _util.NamedDict(
    'Condset',
    ep = _ep,
)
