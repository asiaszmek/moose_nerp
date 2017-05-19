# -*- coding:utf-8 -*-

######## SPneuronSim.py ############
## Code to create two globus pallidus neurons
##      using dictionaries for channels and synapses
##      calcium based learning rule/plasticity function, optional
##      spines, optionally with ion channels and synpases
##      Synapses to test the plasticity function, optional
##      used to tune parameters and channel kinetics (but using larger morphology)

from __future__ import print_function, division
import logging

import os
os.environ['NUMPTHREADS'] = '1'
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
                     test_plasticity,
                     logutil,
                     util,
                     standard_options,
                     constants)
from moose_nerp import gp
from moose_nerp.graph import plot_channel, neuron_graph, spine_graph

option_parser = standard_options.standard_options(
    default_injection_current=[25e-12], #0.5e-9, 1.0e-9, 1.4e-9, 1.8e-9, 2.2e-9
    default_simulation_time=0.6,
    default_injection_width=0.4,
    default_plotdt=0.0001)

param_sim = option_parser.parse_args()

logging.basicConfig(level=logging.INFO)
log = logutil.Logger()

print(param_sim)
print(gp.synYN)

#################################-----------create the model
##create 2 neuron prototypes, optionally with synapses, calcium, and spines

gp.neurontypes(['arky'])
MSNsyn,neuron = cell_proto.neuronclasses(gp)
print('MSNsyn:', MSNsyn)
print('neuron:', neuron)

#If calcium and synapses created, could test plasticity at a single synapse in syncomp
if gp.synYN:
    plas,stimtab=test_plasticity.test_plasticity(gp, param_sim.syncomp, MSNsyn, param_sim.stimtimes)
else:
    plas = {}

####---------------Current Injection
all_neurons={}
for ntype in neuron.keys():
    all_neurons[ntype]=list([neuron[ntype].path])
pg=inject_func.setupinj(gp, param_sim.injection_delay, param_sim.injection_width, all_neurons)


###############--------------output elements
if param_sim.plot_channels:
    for chan in gp.Channels.keys():
        libchan=moose.element('/library/'+chan)
        plot_channel.plot_gate_params(libchan,param_sim.plot_activation,
                                      gp.VMIN, gp.VMAX, gp.CAMIN, gp.CAMAX)


vmtab,catab,plastab,currtab = tables.graphtables(gp, neuron, param_sim.plot_current,  param_sim.plot_current_message, plas)

if gp.spineYN:
    spinecatab,spinevmtab=tables.spinetabs(gp,neuron)
########## clocks are critical. assign_clocks also sets up the hsolver
simpaths=['/'+neurotype for neurotype in gp.neurontypes()]
clocks.assign_clocks(simpaths, param_sim.simdt, param_sim.plotdt, param_sim.hsolve,gp.param_cond.NAME_SOMA)

##print soma conductances
moose.reinit()
if param_sim.hsolve:
    chantype='ZombieHHChannel'
else:
    chantype='HHChannel'
for neur in gp.neurontypes():
  for chan in moose.wildcardFind('{}/soma/#[TYPE={}]'.format(neur, chantype)):
    print (neur, chan.name,chan.Ik*1e9, chan.Gk*1e9)
  for chan in moose.wildcardFind('/'+neur+'/soma/#[TYPE=HHChannel2D]'):
    print (neur, chan.name,chan.Ik*1e9, chan.Gk*1e9)

if param_sim.hsolve and gp.calYN:
    calcium.fix_calcium(gp.neurontypes(), gp)

spikegen=moose.SpikeGen('/data/spikegen')
#spikegen.threshold=0.0
#spikegen.refractT=1.0e-3
#msg=moose.connect(soma1,'VmOut',spikegen,'Vm')

####
spiketab=moose.Table('/data/spike')
moose.connect(spikegen,'spikeOut',spiketab,'spike')

###########Actually run the simulation
def run_simulation(injection_current, simtime):
    print(u'◢◤◢◤◢◤◢◤ injection_current = {} ◢◤◢◤◢◤◢◤'.format(injection_current))
    pg.firstLevel = injection_current
    moose.reinit()
    moose.start(simtime)



if __name__ == '__main__':
    traces, names = [], []
    value = {}
    label = {}
    calcium_traces=[]
    for inj in param_sim.injection_current:
        run_simulation(injection_current=inj, simtime=param_sim.simtime)
        #neuron_graph.graphs(gp, param_sim.plot_current, param_sim.simtime,
        #                    currtab,param_sim.plot_current_label, catab, plastab)
        for neurnum,neurtype in enumerate(gp.neurontypes()):
            #
            if param_sim.plot_current:
                for channame in gp.Channels.keys():
                    key =  neurtype+'_'+channame
                    print(channame,key)
                    value[key] = currtab[neurtype][channame][0].vector
                    label[key] = '{} @ {}'.format(neurtype, channame)
            traces.append(vmtab[neurnum][0].vector)
            #traces.append(vmtab[neurnum][2].vector)
            calcium_traces.append(catab[neurnum][0].vector)
            #calcium_traces.append(catab[neurnum][2].vector)
            names.append('c0{} @ {}'.format(neurtype, inj))
            #names.append('c1{} @ {}'.format(neurtype, inj))

    if gp.spineYN:
            spine_graph.spineFig(gp,spinecatab,spinevmtab, param_sim.simtime)
    #
    #
    #subset1=['proto_HCN1','proto_HCN2' ]
    #subset2=['proto_NaS']
    #subset3=['proto_Ca']
    #subset4=['proto_BKCa']
    #subset5=['proto_NaS']
    #subset6 = ['proto_KvS']
    #subsetin=['proto_HCN1','proto_HCN2','proto_NaS', 'proto_Ca' ,'proto_NaF']
    #subsetout=['proto_KCNQ','proto_KvS', 'proto_KvF', 'proto_Kv3', 'proto_SKCa','proto_KDr' ]
    #neuron_graph.CurrentGraphSet(value,label,subsetin, param_sim.simtime)
    #neuron_graph.CurrentGraphSet(value, label, subsetout, param_sim.simtime)
    #neuron_graph.CurrentGraphSet(value, label, subset3, param_sim.simtime)
    #neuron_graph.CurrentGraphSet(value, label, subset4, param_sim.simtime)
    #neuron_graph.CurrentGraphSet(value, label, subset5, param_sim.simtime)
    #neuron_graph.CurrentGraphSet(value, label, subset6, param_sim.simtime)
    if param_sim.plot_calcium:
        neuron_graph.SingleGraphSet(calcium_traces,names,param_sim.simtime, title='Ca')
    if param_sim.plot_vm:
        neuron_graph.SingleGraphSet(traces, names, param_sim.simtime)

    # block in non-interactive mode
    util.block_if_noninteractive()

    #End of inject loop
l=len(spiketab.vector)
print(l)
