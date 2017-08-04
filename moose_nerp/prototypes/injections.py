import moose
import numpy as np
import random
from moose_nerp.prototypes import connect

def MakeGenerators(container,Stimulation):
    
    StimParams = Stimulation.Paradigm
    pulse0 = moose.PulseGen(container+'/pulse0')
    pulse0.level[0] = StimParams.A_inject
    pulse0.width[0] = StimParams.width_AP
    pulse0.delay[0] = 0
    pulse0.delay[1] = StimParams.AP_interval
    pulse0.baseLevel = 0
    pulse0.trigMode = 2

    burst_gate = moose.PulseGen(container+'/burst_gate')
    burst_gate.level[0] = StimParams.A_inject
    burst_gate.delay[0] = 0
    burst_gate.delay[1] = 1./StimParams.f_burst
    burst_gate.width[0] = StimParams.n_AP*StimParams.AP_interval
    burst_gate.baseLevel = 0
    burst_gate.trigMode = 2

    moose.connect(burst_gate,'output',pulse0,'input')

    train_gate = moose.PulseGen(container+'/train_gate')
    train_gate.level[0] = StimParams.A_inject
    train_gate.delay[0] = 0
    train_gate.delay[1] = 1./StimParams.f_train
    train_gate.width[0] = StimParams.n_burst/StimParams.f_burst
    train_gate.baseLevel = 0
    train_gate.trigMode = 2

    moose.connect(train_gate,'output',burst_gate,'input')
    
    experiment_gate = moose.PulseGen(container+'/experiment_gate')
    experiment_gate.level[0] = StimParams.A_inject
    experiment_gate.delay[0] = Stimulation.stim_delay+StimParams.ISI
    experiment_gate.delay[1] = 1e9
    experiment_gate.width[0] = StimParams.n_train/StimParams.f_train
    experiment_gate.baseLevel = 0
    experiment_gate.trigMode = 0

    moose.connect(experiment_gate,'output',train_gate,'input')

    return [pulse0,burst_gate,train_gate,experiment_gate]

def loop_through_spines(i,j,k,spines,time_tables,delay,StimParams):
    for spine in spines:
        if spine not in time_tables:
            time_tables[spine] = []
            
        time_tables[spine].append(delay+i*1./StimParams.f_train+j*1./StimParams.f_burst+k*1./StimParams.f_pulse)

def MakeTimeTables(Stimulation,spine_no):

    StimParams = Stimulation.Paradigm
       
    if not StimParams.PreStim:
        return

    delay = Stimulation.stim_delay
    
    time_tables = {}
    if Stimulation.which_spines in ['all','ALL','All']:
        how_many  = round(Stimulation.spine_density*spine_no)
    elif Stimulation.which_spines:
        how_many  = round(Stimulation.spine_density*len(Stimulation.which_spines))
        
    for i in range(StimParams.n_train):
        for j in range(StimParams.n_burst):
            for k in range(StimParams.n_pulse):
                if Stimulation.pulse_sequence:
                    spines = Stimulation.pulse_sequence[k]
                    loop_through_spines(i,j,k,spines,time_tables,delay,StimParams)

                elif Stimulation.which_spines in ['all','ALL','All']:
                    spines = []
                    how_many_spines = 0
                    while True:
                        spine = random.randint(0,spine_no-1)
                        if spine not in spines:
                            spines.append(spine)
                            how_many_spines += 1
                            if how_many_spines == how_many:
                                break

                    loop_through_spines(i,j,k,spines,time_tables,delay,StimParams)
                        
                elif  Stimulation.which_spines:
                    spines = []
                    how_many_spines = 0
                    while True:
                        r = random.randint(0,len(Stimulation.which_spines)-1)
                        spine = Stimulation.which_spines[r]
                        if spine not in spines:
                            spines.append(spine)
                            how_many_spines += 1
                            if how_many_spines == how_many:
                                break
                    
                    loop_through_spines(i,j,k,spines,time_tables,delay,StimParams)
                    
        return time_tables
    
def HookUpDend(model,dendrite,path):
    
    #for dend in model.Stimulation.StimParams.which_dendrites:
    spines = list(set(moose.element(dendrite).neighbors['handleAxial']).intersection(set(moose.element(dendrite).children)))
    spine_no = len(spines)
    
    if not spine_no:
        return

    synapses = {}
    for spine in spines:
        spine_no = int(''.join(c for c in spine.name if c.isdigit()))
        synapses[spine_no] = []
        heads = moose.element(spine).neighbors['handleAxial']
        for head in heads:
            moose_head = moose.element(head)
            for child in moose_head.children:
                moose_child = moose.element(child)
                if moose_child.className == 'SynChan' or moose_child.className == 'NMDAChan':
                    synapses[spine_no].append(moose_child)
                    
    time_tables = MakeTimeTables(model.Stimulation,spine_no)
    stimtab = {}
 
    print(time_tables)
    for spine in time_tables:
        stimtab[spine] = moose.TimeTable('%s/TimTab%s_%s' % (path, dendrite.name,str(spine)))
        stimtab[spine].vector = np.array(time_tables[spine])
        
        for synapse in synapses[spine]:
            synchan = moose.element(synapse)
            connect.plain_synconn(synchan,stimtab[spine],0)


    

def ConnectPreSynapticPostSynapticStimulation(model,ntype):
    container = '/input'
    moose.Neutral(container)
    SP = model.Stimulation.Paradigm
    exp_duration = (SP.n_train-1)/SP.f_train+(SP.n_burst-1)/SP.f_burst+(SP.n_pulse-1)/SP.f_pulse+SP.n_AP*SP.AP_interval+2*model.Stimulation.stim_delay
    
    if SP.A_inject:
        pg = MakeGenerators(container,model.Stimulation)
        injectcomp = '/'+ntype+'/'+model.Stimulation.injection_compartment
        moose.connect(pg[0], 'output', injectcomp, 'injectMsg')

    for dend in model.Stimulation.stim_dendrites:
        name_dend = '/'+ntype+'/'+dend
        dendrite = moose.element(name_dend)
        HookUpDend(model,dendrite,container)
    
    return exp_duration
