from __future__ import print_function, division
import numpy as np
from matplotlib import pyplot
import moose

from moose_nerp.prototypes import syn_proto, logutil
log = logutil.Logger()

def graphs(neurons, simtime, vmtab,catab=[],plastab=[]):
    t = np.linspace(0, simtime, len(vmtab[0][0].vector))
    fig,axes =pyplot.subplots(len(vmtab), 1,sharex=True)
    axis=fig.axes
    fig.canvas.set_window_title('Population Vm')
    for typenum,neur in enumerate(neurons.keys()):
        for vmoid in vmtab[typenum]:
            neur_name=vmoid.msgOut[0].e2.path.split('/')[-2][0:-3]
            axis[typenum].plot(t, vmoid.vector, label=neur_name)
        axis[typenum].set_ylabel(neur+' Vm, volts')
        axis[typenum].legend(fontsize=8,loc='upper left')
    axis[typenum].set_xlabel('Time, sec')
    #
    if len(catab):
        fig,axes =pyplot.subplots(len(vmtab), 1,sharex=True)
        axis=fig.axes
        fig.canvas.set_window_title('Population Calcium')
        for tabset in catab:
            if len(tabset)==1:
                caoid=tabset
                typenum=neurons.keys().index(caoid.name.partition('_')[0][2:])
                axis[typenum].plot(t, caoid.vector*1e3, label=caoid.name.partition('_')[2])
            else:
                for caoid in tabset:
                    typenum=neurons.keys().index(caoid.name.partition('_')[0][2:])
                    axis[typenum].plot(t, caoid.vector*1e3, label=caoid.name.partition('_')[2])
        for typenum,neur in enumerate(neurons.keys()):
            axis[typenum].set_ylabel(neur+' Calcium, uM')
            axis[typenum].legend(fontsize=8,loc='upper left')
        axis[typenum].set_xlabel('Time, sec')
    #
    if len(plastab):
        fig,axes =pyplot.subplots(len(vmtab), len(plastab[0].keys()), sharex=True)
        axis=fig.axes
        fig.canvas.set_window_title('Population Plasticity')
        for neurnum,tabset in enumerate(plastab):
            for plasnum, plastype in enumerate(tabset.keys()):
                if plastype=='plas':
                    scaling=1000
                else:
                    scaling=1
                plasoid=tabset[plastype]
                typenum=neurons.keys().index(plasoid.name.split(plastype)[1].split('_')[0])
                t=np.linspace(0, simtime, len(plasoid.vector))
                axis[typenum][plasnum].plot(t,plasoid.vector*scaling, label=plasoid.path.partition('_')[2])
            axis[typenum][plasnum].legend(fontsize=8,loc='best')
        for typenum,neur in enumerate(neurons.keys()):
            for plasnum, plastype in enumerate(tabset.keys()):
                axis[typenum][plasnum].set_ylabel(neur+''+plastype)
                axis[typenum][plasnum].set_xlabel('Time, sec')
        fig.tight_layout()
        fig.canvas.draw()

def syn_graph(connections, syntabs, simtime):
    numrows=len(syntabs.keys()) #how many neuron types
    max_index=np.argmax([len(connections[k].keys()) for k in connections.keys()])
    syntypes=[list(connections[k].keys()) for k in connections.keys()][max_index] #how many synapse types
    numcols=len(syntypes)
    fig,axes =pyplot.subplots(numrows, numcols,sharex=True)
    axis=fig.axes #convert to 1D list in case numrows or numcols=1
    fig.canvas.set_window_title('Syn Chans')
    for typenum,neurtype in enumerate(syntabs.keys()):
        for oid in syntabs[neurtype]:
            synnum=syntypes.index(oid.path.rpartition('_')[2].split('[')[0]) #extract synapse type from table name
            axisnum=typenum*len(syntypes)+synnum
            t = np.linspace(0, simtime, len(oid.vector))
            axis[axisnum].plot(t, oid.vector*1e9, label=oid.name.split('_')[1])
        print(neurtype,axisnum,oid.path.rpartition('_')[2].split('[')[0])
        axis[axisnum].set_ylabel('I (nA), {}'.format(oid.path.rpartition('_')[2]))
    for ax in range(len(axis)):
        axis[ax].legend(fontsize=8,loc='upper left') #add legend
