from spspine.util import NamedList, NamedDict
from spspine import param_sim, param_cond
from spspine.syn_proto import SynChannelParams, MgParams

#Parameters for inhibitory synpases:
#Erev, tau1, tau2  (SI units)

#C is concentration of Mg, A is 1/eta and B is 1/gamma,
#Rebekah's:
#These params are too insensitive to voltage
#mgparams={'A':(1/18.0), 'B':(1/99.0), 'C': 1.4}
#Classic (allows significant calcium at resting potential):
#mgparams={'A':(1/3.57), 'B':(1/62.0), 'C': 1.4}
#Intermediate
_NMDA_MgParams = MgParams(A = 1/6.0,
                           B = 1/80.0,
                           C = 1.4)

#Sriram uses 0.109e-9 for AMPA and 0.9e-9 for Gaba
_SynGaba = SynChannelParams(Erev = -60e-3,
                             tau1 = 0.25e-3,
                             tau2 = 3.75e-3,
                             Gbar = 0.2e-9,
                             var=0.05)
_SynAMPA = SynChannelParams(Erev = 5e-3,
                             tau1 = 1.1e-3,
                             tau2 = 5.75e-3,
                             Gbar = 2e-9,
                             var=0.05,
                             spinic = True)
_SynNMDA = SynChannelParams(Erev = 5e-3,
                             tau1 = 1.1e-3,
                             tau2 = 37.5e-3,
                             Gbar = 2e-9,
                             var=0.05,
                             MgBlock = _NMDA_MgParams,
                             spinic = True,
                             NMDA=True,
                             nmdaCaFrac = 0.05
)

#nmdaCaFra fraction of nmda current carried by calcium
#Note that since Ca reversal produces ~2x driving potential,
#need to make this half of typical value.  Default is 0.02 in Moose

SynChanParams = NamedDict(
    'SynChanParams',
    ampa =  _SynAMPA,
    gaba =  _SynGaba,
    nmda =  _SynNMDA
)

# number of synapses at each distance
NumGaba = {param_cond.prox:3, param_cond.med:2, param_cond.dist:1}
NumGlu = {param_cond.prox:1, param_cond.med:2, param_cond.dist:3}
NumSyn={'Gaba':NumGaba,'Glu':NumGlu}

def SpineSynChans():
    return sorted(key for key,val in SynChanParams.items()
                  if val.spinic and param_sim.spineYesNo)

def DendSynChans():
    # If synapses are disabled, put all synaptic channels in the dendrite
    return sorted(key for key,val in SynChanParams.items()
                  if not (val.spinic and param_sim.spineYesNo))
