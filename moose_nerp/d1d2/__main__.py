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

option_parser = standard_options.standard_options(default_calcium=True, default_spines=False)
param_sim = option_parser.parse_args()

# set the model settings if specified by command-line options and retain model defaults otherwise
if param_sim.calcium is not None:
    d1d2.calYN = param_sim.calcium
if param_sim.spines is not None:
    d1d2.spineYN = param_sim.spines

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

if param_sim.injection_current:
    pg=inject_func.setupinj(d1d2, param_sim.injection_delay, param_sim.injection_width, all_neurons)
else:
    param_sim.injection_current = [0]

###############--------------output elements
if param_sim.plot_channels:
    for chan in d1d2.Channels.keys():
        libchan=moose.element('/library/'+chan)
        plot_channel.plot_gate_params(libchan,param_sim.plot_activation,
                                      d1d2.VMIN, d1d2.VMAX, d1d2.CAMIN, d1d2.CAMAX)

grtables = tables.graphtables(d1d2, neuron,
                              param_sim.plot_current,
                              param_sim.plot_current_message,
                              plas)
if param_sim.save:
    tables.setup_hdf5_output(d1d2, neuron, param_sim.save)

if d1d2.spineYN:
    spinecatab,spinevmtab=tables.spinetabs(d1d2,neuron)
########## clocks are critical. assign_clocks also sets up the hsolver
simpaths=['/'+neurotype for neurotype in d1d2.neurontypes()]
clocks.assign_clocks(simpaths, param_sim.simdt, param_sim.plotdt, param_sim.hsolve, d1d2.param_cond.NAME_SOMA)
print("simdt", param_sim.simdt, "hsolve", param_sim.hsolve)

if param_sim.hsolve and d1d2.calYN:
    calcium.fix_calcium(d1d2.neurontypes(), d1d2)

###########Actually run the simulation
def run_simulation( simtime,injection_current=None):
    if injection_current:
        print(u'◢◤◢◤◢◤◢◤ injection_current = {} ◢◤◢◤◢◤◢◤'.format(injection_current))
        pg.firstLevel = injection_current
        
    moose.reinit()
    moose.start(simtime)

traces, names, catraces = [], [], []
for inj in param_sim.injection_current:
    run_simulation(simtime=param_sim.simtime,injection_current=inj)
    neuron_graph.graphs(d1d2, param_sim.plot_current, param_sim.simtime,
                        grtables.currtab, param_sim.plot_current_label,
                        grtables.catab, grtables.plastab)

    for neurnum,neurtype in enumerate(d1d2.neurontypes()):
        traces.append(grtables.vmtab[neurnum][0].vector)
        if d1d2.calYN:
            catraces.append(grtables.catab[neurnum][0].vector)
        names.append('{} @ {}'.format(neurtype, inj))
        # In Python3.6, the following syntax works:
        #names.append(f'{neurtype} @ {inj}')
    if d1d2.spineYN:
        spine_graph.spineFig(d1d2,spinecatab,spinevmtab, param_sim.simtime)
neuron_graph.SingleGraphSet(traces, names, param_sim.simtime)
if d1d2.calYN:
    neuron_graph.SingleGraphSet(catraces, names, param_sim.simtime)


# block in non-interactive mode
util.block_if_noninteractive()
