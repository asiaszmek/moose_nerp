#syn_proto.py
"""\
Function definitions for making channels.
"""

from __future__ import print_function, division
import numpy as np

from spspine.util import dist_num
import moose 
import param_syn as parsyn
import param_chan as parchan
import param_cond as parcond
from param_sim import printinfo, printMoreInfo

def make_synchan(chanpath,synparams,ghkYN,calYN):
    # for AMPA or GABA - just make the channel, no connections/messages
    if printinfo:
        print('synparams:', chanpath, synparams['tau1'], synparams['tau2'], synparams['Erev'])
    synchan=moose.SynChan(chanpath)
    synchan.tau1 = synparams['tau1']
    synchan.tau2 = synparams['tau2']
    synchan.Ek = synparams['Erev']
    #for NMDA, create Mg block and set up bi-directional messages
    #if mgblock is below nmda on element tree, it will be copied into compartment with nmda
    if synparams['name']=='nmda':
        blockname=synchan.path+'/mgblock'
        mgblock=moose.MgBlock(blockname)
        mgblock.KMg_A=parsyn.mgparams['A']
        mgblock.KMg_B=parsyn.mgparams['B']
        mgblock.CMg=parsyn.mgparams['C']
        mgblock.Ek=synparams['Erev']
        mgblock.Zk=2
        if printinfo:
            print('nmda',blockname,mgblock,parsyn.mgparams)
        moose.connect(synchan,'channelOut', mgblock,'origChannel')
        if calYN:
        #This duplicate nmda current prevents reversal of calcium current
        #It needs its own Mg Block, since the output will only go to the calcium pool
        #If necessary, can make the decay time faster for the calcium part of NMDA
            synchan2=moose.SynChan(synchan.path+'/CaCurr')
            synchan2.tau1 = synparams['tau1']
            synchan2.tau2 = synparams['tau2']
            synchan2.Ek = parchan.carev
            blockname=synchan2.path+'/mgblock'
            mgblock2=moose.MgBlock(blockname)
            mgblock2.KMg_A=parsyn.mgparams['A']
            mgblock2.KMg_B=parsyn.mgparams['B']
            mgblock2.CMg=parsyn.mgparams['C']
            mgblock2.Ek=parchan.carev
            mgblock2.Zk=2
            moose.connect(synchan2,'channelOut', mgblock2,'origChannel')
            if ghkYN:
                #Note that ghk must receive input from MgBlock, NOT MgBLock to ghk
                ghk=moose.GHK(synchan2.path+'/ghk')
                ghk.T=parcond.Temp
                ghk.Cout=parcond.ConcOut
                ghk.valency=2
                if printinfo:
                    print("CONNECT nmdaCa", synchan2.path, "TO", mgblock2.path, "TO", ghk.path)
                moose.connect(mgblock2,'ghk',ghk, 'ghk')
    return synchan

def synchanlib(ghkYN,calYN):
    if not moose.exists('/library'):
        lib = moose.Neutral('/library')
    synchan=list()
    for key in parsyn.SynChanDict:
        chanpath='/library/'+key
        synchan.append(make_synchan(chanpath,parsyn.SynChanDict[key],ghkYN,calYN))
    print(synchan)

def addoneSynChan(chanpath,syncomp,gbar,calYN,ghkYN):
    proto=moose.SynChan('/library/' +chanpath)
    if printMoreInfo:
        print("adding channel",chanpath,"to",syncomp.path,"from",proto.path)
    synchan=moose.copy(proto,syncomp,chanpath)[0]
    synchan.Gbar = np.random.normal(gbar,gbar*parsyn.GbarVar)
    if chanpath=='nmda':
        #mgblock, CaCurr, and ghk were copied above if they exist
        mgblock=moose.element(synchan.path+'/mgblock')
        #bidirectional connection from mgblock to compartment for non-Ca part of NMDA:
        m=moose.connect(mgblock, 'channel', syncomp, 'channel')
        #Send Vm message from comp to synchan
        m1=moose.connect(syncomp,'VmOut', synchan, 'Vm')
        if calYN:   #create separate "shadow" nmda channel to keep track of calcium
            #no message from CaCurr to comp, only Vm from comp to ghk and mgblock2
            synchan2=moose.element(synchan.path+'/CaCurr')
            mgblock2=moose.element(synchan2.path+'/mgblock')
            #unidirectional Vm connection from compartment to mgblock for non-Ca part of NMDA:
            moose.connect(syncomp,'VmOut',mgblock2, 'Vm')
            if ghkYN:
                ghk=moose.element(synchan2.path+'/ghk')
                synchan2.Gbar=synchan.Gbar*parsyn.nmdaCaFrac*parcond.ghKluge
                #unidirectional connection from comp to ghk
                moose.connect(syncomp, 'VmOut', ghk,'handleVm')
            else:
                synchan2.Gbar=synchan.Gbar*parsyn.nmdaCaFrac
    else:
        #bidirectional connection from synchan to compartment when not NMDA:
        m = moose.connect(syncomp, 'channel', synchan, 'channel')
    return synchan

def add_synchans(container,calYN,ghkYN):
    #synchans is 2D array, where each row has a single channel type
    #at the end they are concatenated into a dictionary
    synchans=[]
    comp_list = moose.wildcardFind('%s/#[TYPE=Compartment]' %(container))
    SynPerComp=np.zeros((len(comp_list),parsyn.NumSynClass),dtype=int)
    numspines=0
    #Create 2D array to store all the synapses.  Rows=num synapse types, columns=num comps
    for key in parsyn.SynChanDict:
        synchans.append([])
    allkeys = sorted(parsyn.SynChanDict)

    # i indexes compartment for array that stores number of synapses
    for i, comp in enumerate(comp_list):
                
        #create each type of synchan in each compartment.  Add to 2D array
        for key in parsyn.DendSynChans:
            keynum=allkeys.index(key)
            Gbar=parsyn.SynChanDict[key]['Gbar']
            synchans[keynum].append(addoneSynChan(key,comp,Gbar,calYN,ghkYN))
        for key in parsyn.SpineSynChans:
            keynum=allkeys.index(key)
            Gbar=parsyn.SynChanDict[key]['Gbar']
            numspines=0   #count number of spines in each compartment
            for spcomp in moose.wildcardFind('%s/#[ISA=Compartment]'%(comp.path)):
                if 'head' in spcomp.path:
                    synchans[keynum].append(addoneSynChan(key,spcomp,Gbar,calYN,ghkYN))
                    numspines=numspines+1
        #
        #calculate distance from soma
        xloc=moose.Compartment(comp).x
        yloc=moose.Compartment(comp).y
        dist=np.sqrt(xloc*xloc+yloc*yloc)
        #create array of number of synapses per compartment based on distance
        #possibly replace NumGlu[] with number of spines, or eliminate this if using real morph
        #Check in ExtConn - how is SynPerComp used

        num = dist_num(parcond.distTable, dist)
        SynPerComp[i,parsyn.GABA] = parsyn.NumGaba[num]
        SynPerComp[i,parsyn.GLU] = parsyn.NumGlu[num]

    #end of iterating over compartments
    #now, transform the synchans into a dictionary
    allsynchans={key:synchans[keynum]
                 for keynum, key in enumerate(sorted(parsyn.SynChanDict))}

    return SynPerComp,allsynchans
