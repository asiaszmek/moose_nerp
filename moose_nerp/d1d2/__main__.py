# -*- coding:utf-8 -*-

######## SPneuronSim.py ############
## Code to create two SP neuron classes 
##      using dictionaries for channels and synapses
##      calcium based learning rule/plasticity function, optional
##      spines, optionally with ion channels and synpases
##      Synapses to test the plasticity function, optional
##      used to tune parameters and channel kinetics (but using larger morphology)

from __future__ import print_function, division
import logging

import numpy as np
import matplotlib.pyplot as plt
plt.ion()

from pprint import pprint
import moose 

from moose_nerp.prototypes import (cell_proto,
                     calcium,
                     clocks,
                     inject_func,
                     tables,
                     plasticity_test,
                     logutil,
                     util,
                     standard_options,
                                   constants)
from moose_nerp import d1d2
from moose_nerp.graph import plot_channel, neuron_graph, spine_graph

option_parser = standard_options.standard_options(default_injection_current=[0.1e-9],default_stimtimes=[])#, 0.2e-9, 0.3e-9,.4e-9,.5e-9])
param_sim = option_parser.parse_args()
#param_sim.simtime = 0.01
d1d2.calYN=1
logging.basicConfig(level=logging.INFO)
log = logutil.Logger()

#################################-----------create the model
##create 2 neuron prototypes, optionally with synapses, calcium, and spines
MSNsyn,neuron= cell_proto.neuronclasses(d1d2)
#If calcium and synapses created, could test plasticity at a single synapse in syncomp

plas = {}

if d1d2.synYN:
    sim_time = []
    for ntype in d1d2.neurontypes():
        st, spines, pg = inject_func.ConnectPreSynapticPostSynapticStimulation(d1d2,ntype)
        sim_time.append( st)
        plas[ntype] = spines
    param_sim.simtime = max(sim_time)
    
if d1d2.plasYN:
    plas,stimtab=plasticity_test.plasticity_test(d1d2, param_sim.syncomp, MSNsyn, param_sim.stimtimes)


    
####---------------Current Injection
all_neurons={}
for ntype in neuron.keys():
    all_neurons[ntype]=list([neuron[ntype].path])
pg=inject_func.setupinj(d1d2, param_sim.injection_delay, param_sim.injection_width, all_neurons)

###############--------------output elements
if param_sim.plot_channels:
    for chan in d1d2.Channels.keys():
        libchan=moose.element('/library/'+chan)
        plot_channel.plot_gate_params(libchan,param_sim.plot_activation,
                                      d1d2.VMIN, d1d2.VMAX, d1d2.CAMIN, d1d2.CAMAX)

vmtab,catab,plastab,currtab = tables.graphtables(d1d2, neuron,
                                                 param_sim.plot_current,
                                                 param_sim.plot_current_message,
                                                 plas)
if d1d2.spineYN:
    spinecatab,spinevmtab=tables.spinetabs(d1d2,neuron)

moose.reinit()
########## clocks are critical. assign_clocks also sets up the hsolver
simpaths=['/'+neurotype for neurotype in d1d2.neurontypes()]
clocks.assign_clocks(simpaths, param_sim.simdt, param_sim.plotdt, param_sim.hsolve, d1d2.param_cond.NAME_SOMA)
print("simdt", param_sim.simdt, "hsolve", param_sim.hsolve)

if param_sim.hsolve and d1d2.calYN:
    calcium.fix_calcium(d1d2.neurontypes(), d1d2)

###########Actually run the simulation
def run_simulation(injection_current, simtime):
    print(u'◢◤◢◤◢◤◢◤ injection_current = {} ◢◤◢◤◢◤◢◤'.format(injection_current))
    pg.firstLevel = injection_current
    moose.reinit()
    moose.start(simtime)

    
calcium = d1d2.CaPlasticityParams.CaShellModeDensity[d1d2.CaPlasticityParams.soma]
fname = 'output/{}_{}_simtime_{}_inject_{}_5_inj_Ca_{}_spines_density{}.txt'
traces, names, catraces = [], [], []

#run_simulation(param_sim.injection_current[0],param_sim.simtime )
moose.reinit()
moose.start(param_sim.simtime)

neuron_graph.graphs(d1d2, param_sim.plot_current, param_sim.simtime,
                        currtab,param_sim.plot_current_label, catab, plastab)
inj = "Fino"#param_sim.injection_current[0]
for neurnum,neurtype in enumerate(d1d2.neurontypes()):
    print(fname.format(len(d1d2.neurontypes()),neurtype,'Vm',param_sim.simtime,inj,calcium,d1d2.spineYN))
    traces.append(vmtab[neurnum][0].vector)
    catraces.append(catab[neurnum][0].vector)
    names.append('{} @ {}'.format(neurtype, inj))
    time = np.linspace(0,param_sim.simtime,len(vmtab[neurnum][0].vector))
    Ca = np.zeros((len(time),2))
    Vm = np.zeros((len(time),2))
    Vm[:,0] = time
    Ca[:,0] = time
    Vm[:,1] = vmtab[neurnum][0].vector
    Ca[:,1] = catab[neurnum][0].vector
    spines = 'no_spines'
    if d1d2.spineYN:
            
        spines = 'spineDensity_{}'.format(d1d2.SpineParams.spineDensity)
                
    np.savetxt(fname.format(neurtype,'Vm',param_sim.simtime,inj,calcium,spines),Vm,comments='',header='time '+vmtab[neurnum][0].neighbors['requestOut'][0].path)
    np.savetxt(fname.format(neurtype,'Ca',param_sim.simtime,inj,calcium,spines),Ca,comments='',header='time '+catab[neurnum][0].neighbors['requestOut'][0].path)

        # In Python3.6, the following syntax works:
        #names.append(f'{neurtype} @ {inj}')
    # if d1d2.spineYN:
    #     spine_graph.spineFig(d1d2,spinecatab,spinevmtab, param_sim.simtime)
#neuron_graph.SingleGraphSet(traces, names, param_sim.simtime)
#neuron_graph.SingleGraphSet(catraces, names, param_sim.simtime)

# block in non-interactive mode
util.block_if_noninteractive()
