# -*- coding:utf-8 -*-

######## ep_net/multisim.py ############

from __future__ import print_function, division

def moose_main(p):
    stimfreq,presyn,stpYN,trialnum,prefix=p

    import numpy as np
    import moose

    from moose_nerp.prototypes import (create_model_sim,
                                       clocks,
                                       inject_func,
                                       create_network,
                                       tables,
                                       net_output,
                                       util)
    from moose_nerp import ep as model
    from moose_nerp import ep_net as net
    from moose_nerp.graph import net_graph, neuron_graph, spine_graph


    #additional, optional parameter overrides specified from with python terminal
    model.synYN = True
    model.stpYN = stpYN
    net.single=True
    stimtype='PSP_'
    outdir="ep_net/output/"
    if stimfreq>0:
        model.param_sim.stim_paradigm=stimtype+str(stimfreq)+'Hz'
        model.param_stim.Stimulation.StimLoc=model.param_stim.location[presyn]
    else:
        model.param_sim.stim_paradigm='inject'
    create_model_sim.setupOptions(model)
    param_sim = model.param_sim
    param_sim.injection_current = [0e-12]
    param_sim.injection_delay = 0.0
    param_sim.plot_synapse=False
       
    if prefix.startswith('POST-HFS'):
        net.connect_dict['ep']['ampa']['extern1'].weight=0.6 #STN - weaker
        net.connect_dict['ep']['gaba']['extern2'].weight=0.8 #GPe - weaker
        net.connect_dict['ep']['gaba']['extern3'].weight=1.4 #str - stronger
    if prefix.startswith('POST-NoDa'):
        net.connect_dict['ep']['ampa']['extern1'].weight=1.0 #STN - no change
        net.connect_dict['ep']['gaba']['extern2'].weight=2.8 #GPe - stronger
        net.connect_dict['ep']['gaba']['extern3'].weight=1.0 #str - no change
    
    #################################-----------create the model: neurons, and synaptic inputs
    
    model=create_model_sim.setupNeurons(model,network=not net.single)
    population,connections,plas=create_network.create_network(model, net, model.neurons)

    ####### Set up stimulation - could be current injection or plasticity protocol
    # set num_inject=0 to avoid current injection
    if net.num_inject<np.inf :
        model.inject_pop=inject_func.inject_pop(population['pop'],net.num_inject)
        if net.num_inject==0:
            param_sim.injection_current=[0]
    else:
        model.inject_pop=population['pop']

    ############## Set-up test of synaptic plasticity at single synapse ####################
    if presyn=='str':
        stp_params=net.param_net.str_plas
    elif presyn=='GPe':
        stp_params=net.param_net.GPe_plas
    else:
        print('########### unknown synapse type')

    param_sim.fname='ep'+prefix+'_syn'+presyn+'_freq'+str(stimfreq)+'_plas'+str(1 if model.stpYN else 0)+'_inj'+str(param_sim.injection_current[0])+'t'+str(trialnum)
    print('>>>>>>>>>> moose_main, presyn {} stpYN {} stimfreq {} trial {} plotcomps {}'.format(presyn,model.stpYN,stimfreq,trialnum, param_sim.plotcomps))

    create_model_sim.setupStim(model)

    ##############--------------output elements
    if net.single:
        create_model_sim.setupOutput(model)
    else:   #population of neurons
        spiketab,vmtab,plastab,catab=net_output.SpikeTables(model, population['pop'], net.plot_netvm, plas, net.plots_per_neur)
        #simpath used to set-up simulation dt and hsolver
        simpath=[net.netname]
        clocks.assign_clocks(simpath, param_sim.simdt, param_sim.plotdt, param_sim.hsolve,model.param_cond.NAME_SOMA)
        # Fix calculation of B parameter in CaConc if using hsolve
        if model.param_sim.hsolve and model.calYN:
            calcium.fix_calcium(util.neurontypes(model.param_cond), model)
    #
    if model.synYN and (param_sim.plot_synapse or net.single):
        #overwrite plastab above, since it is empty
        syntab, plastab, stp_tab=tables.syn_plastabs(connections,model)
    #
    #add short term plasticity to synapse as appropriate
    param_dict={'syn':presyn,'freq':stimfreq,'plas':model.stpYN,'inj':param_sim.injection_current,'simtime':param_sim.simtime, 'trial': trialnum,'dt':param_sim.plotdt}
    if stimfreq>0:
        from moose_nerp.prototypes import plasticity_test as plas_test
        extra_syntab={ntype:[] for ntype in  model.neurons.keys()}
        extra_plastabset={ntype:[] for ntype in  model.neurons.keys()}
        for ntype in model.neurons.keys():
            for tt_syn_tuple in model.tuples[ntype].values():
                if model.stpYN:
                    extra_syntab[ntype],extra_plastabset[ntype]=plas_test.short_term_plasticity_test(tt_syn_tuple,syn_delay=0,
                                                                            simdt=model.param_sim.simdt,stp_params=stp_params)
                else:
                    extra_syntab[ntype]=plas_test.short_term_plasticity_test(tt_syn_tuple,syn_delay=0)
            param_dict[ntype]={'syn_tt': [(k,tt[0].vector) for k,tt in model.tuples[ntype].items()]}
    #
    #################### Actually run the simulation

    print('$$$$$$$$$$$$$$ paradigm=', model.param_stim.Stimulation.Paradigm.name,' inj=0? ',np.all([inj==0 for inj in param_sim.injection_current]))
    if model.param_stim.Stimulation.Paradigm.name is not 'inject' and not np.all([inj==0 for inj in param_sim.injection_current]):
        pg=inject_func.setupinj(model, param_sim.injection_delay,model.param_sim.simtime,model.inject_pop)
        inj=[i for i in param_sim.injection_current if i !=0]
        pg.firstLevel = param_sim.injection_current[0]
        create_model_sim.runOneSim(model, simtime=model.param_sim.simtime)
    else:
        for inj in model.param_sim.injection_current:
            create_model_sim.runOneSim(model, simtime=model.param_sim.simtime, injection_current=inj)

    #net_output.writeOutput(model, param_sim.fname+'vm',spiketab,vmtab,population)
    #
    #Save results: spike time, Vm, parameters, input time tables
    vmtab={ntype:[tab.vector for tab in tabset] for ntype,tabset in model.vmtab.items()}
    import ISI_anal
    spike_time,isis=ISI_anal.spike_isi_from_vm(model.vmtab,param_sim.simtime,soma=model.param_cond.NAME_SOMA)
    if np.any([len(st) for tabset in spike_time.values() for st in tabset]):
        np.savez(outdir+param_sim.fname,spike_time=spike_time,isi=isis,params=param_dict,vm=vmtab)
    else:
        print('no spikes for',param_sim.fname, 'saving vm and parameters')
        np.savez(outdir+param_sim.fname,params=param_dict,vm=vmtab)
    if net.single:
        #save spiketime of all input time tables
        timtabs={}
        for neurtype,neurtype_dict in connections.items():
            for neur,neur_dict in neurtype_dict.items():
                for syn,syn_dict in neur_dict.items():
                    timtabs[syn]={}
                    for pretype,pre_dict in syn_dict.items():
                        timtabs[syn][pretype]={}
                        for branch,presyns in pre_dict.items():
                            if 'TimTab' in presyns:
                                timtabs[syn][pretype][branch]=moose.element(presyns).vector
        np.save(outdir+'tt'+param_sim.fname,timtabs)

    #create dictionary with the output (vectors) from test plasticity
    tab_dict={}
    if stimfreq>0:
        for ntype,tabset in extra_syntab.items():
            tab_dict[ntype]={'syn':tabset.vector,'syndt':tabset.dt, 
            'tt': {ntype+'_'+pt:tab.vector for pt,tab in model.tt[ntype].items()}}
            if model.stpYN:
                tab_dict[ntype]['plas']={tab.name:tab.vector for tab in extra_plastabset[ntype]}
    return param_dict,tab_dict,vmtab,spike_time,isis

def multi_main(prefix,num_trials,syntype,stpYN,stimfreq):
    from multiprocessing.pool import Pool
    import os
    
    max_pools=os.cpu_count()
    params=[(stimfreq,syntype,stpYN,trial,prefix) for trial in range(num_trials)]
    num_pools=min(len(params),max_pools)
    print('************* number of processors',max_pools,' params',num_pools,params, 'syn', syntype,stimfreq)
    p = Pool(num_pools,maxtasksperchild=1)
    #
    results = p.map(moose_main,params)

if __name__ == "__main__":
    import sys
    print('running main')
    try:
        args = ARGS.split(" ")
        print("ARGS =", ARGS, "commandline=", args)
        plot_stuff=1
        do_exit = False
    except NameError: #NameError refers to an undefined variable (in this case ARGS)
        args = sys.argv[1:]
        plot_stuff=0
        print("commandline =", args)
        do_exit = True
    condition=args[0] #GABA for ctrl, POST-HFS or POST-NoDa
    num_trials=int(args[1])
    syn=args[2] #str, GPe or non
    stpYN=int(args[3]) #either 0 or 1
    stimfreq=int(args[4])
    results = multi_main(condition,num_trials,syn,stpYN,stimfreq)

'''
for neurtype,neurtype_dict in connections.items():
    for neur,neur_dict in neurtype_dict.items():
        for syn,syn_dict in neur_dict.items():
            for pretype,pre_dict in syn_dict.items():
                for branch,presyn in pre_dict.items():
                    if 'TimTab' not in presyn:
                        preflag='** Intrinsic **'
                    else:
                        preflag='ext'
                    print(preflag,neurtype,neur,syn,pretype,branch,presyn)

import numpy as np
data=np.load('gp_connect.npz')
conns=data['conn'].item()
for neurtype,neurdict in conns.items():
  for cell in neurdict.keys():
     for pre,post in neurdict[cell]['gaba'].items():
        print(cell,pre,post)
'''
