"""\
Function definitions for connecting populations of neurons
1. single synaptic connection
2. creating an array of post-synaptic channels, to randomly select without replacement
3. connect each post-syn channel type of each neuron to either a pre-synaptic neuron or a timetable

"""

from __future__ import print_function, division
import numpy as np
import moose

from moose_nerp.prototypes import logutil, util
from moose_nerp.prototypes.spines import NAME_HEAD
log = logutil.Logger()

def plain_synconn(synchan,presyn,syn_delay):
    sh=moose.element(synchan.path)
    jj=sh.synapse.num
    sh.synapse.num = sh.synapse.num+1
    sh.synapse[jj].delay=syn_delay
    log.debug('SYNAPSE: {} index {} num {} delay {}', synchan.path, jj, sh.synapse.num, sh.synapse[jj].delay)
    #It is possible to set the synaptic weight here.
    if presyn.className=='TimeTable':
        moose.connect(presyn, 'eventOut', sh.synapse[jj], 'addSpike')
    else:
        moose.connect(presyn, 'spikeOut', sh.synapse[jj], 'addSpike')

def synconn(synpath,dist,presyn_path, syn_params ,mindel=1e-3,cond_vel=0.8):
    presyn=moose.element(presyn_path)
    if dist:
        syn_delay = max(mindel,np.random.normal(mindel+dist/cond_vel,mindel))
    else:
        syn_delay=mindel
    synchan=moose.element(synpath)
    plain_synconn(synchan,presyn,syn_delay)
                
    if synchan.name==syn_params.NAME_AMPA:
       nmda_synpath=synchan.parent.path+'/'+syn_params.NAME_NMDA
       if moose.exists(nmda_synpath):
           nmda_synchan=moose.element(nmda_synpath)
           plain_synconn(nmda_synchan,presyn,syn_delay)

def select_entry(table):
    row=np.random.random_integers(0,len(table)-1)
    element=table[row][0]
    table[row][1]=int(table[row][1])-1
    if table[row][1]==0: 
        table[row]=table[len(table)-1]
        table=np.resize(table,(len(table)-1,2))
    return element

def distance_dependent_connection_probability(prob,dist):
    #Two possibilites:
    #1. sigmoid increase (if steep>0) or decrease (if steep<0) in probability of synapse with distance from soma
    # sigmoid increases to maximum of maxprob (default=1) between mindist and maxdist
    #dist_prob=maxprob*(distance)**steep/(distance**steepp+half_dist**steep)
    #2. constant probability between mindist and maxdist
    if prob.postsyn_fraction:
        maxprob=prob.postsyn_fraction
    else:
        maxprob=1
    #if prob.steep:
    steep=prob.steep
    if steep>0:
        if dist<prob.mindist:
            dist_prob=0
        elif dist>prob.maxdist:
            dist_prob=1
        else:
            dist_prob=maxprob*(dist-prob.mindist)**steep/((dist-prob.mindist)**steep+prob.half_dist**steep)
    elif steep<0:
        if dist<prob.mindist:
            dist_prob=1
        elif dist>prob.maxdist:
            dist_prob=0
        else:
            dist_prob=maxprob*prob.half_dist**(-steep)/((dist-prob.mindist)**(-steep)+prob.half_dist**(-steep))
    else:
        if dist<prob.mindist or dist>prob.maxdist:
            dist_prob=0
        else:
            dist_prob=maxprob
    return dist_prob

def create_synpath_array(allsyncomp_list,syntype,NumSyn,prob=None):
    #list of possible synapses with connection probability, which takes into account prior creation of synapses
    syncomps=[]
    totalsyn=0;totalprob=0
    for syncomp in allsyncomp_list:
        dist,nm=util.get_dist_name(syncomp.parent)
        if prob: #calculate dendritic distance dependent connection probability to store with table
            dist_prob=distance_dependent_connection_probability(prob,dist)
        else:
            dist_prob=1
        #print('syncomp',syncomp,'dist',dist,'prob',dist_prob)
        if dist_prob>0: #only add synchan to list if connection probability is non-zero
            sh=moose.element(syncomp.path+'/SH')
            SynPerComp = util.distance_mapping(NumSyn[syntype], dist)-sh.numSynapses
            for i in range(SynPerComp):
                syncomps.append([syncomp.path+'/SH',dist_prob])
                totalprob+=dist_prob #totalprob=total synapses to connect if not using sigmoid
    #normalize probability to pdf
    for syn in syncomps:
        syn[1]=syn[1]/totalprob
    return syncomps,totalprob

def connect_timetable(post_connection,syncomps,totalsyn,netparams,syn_params):
    dist=0
    #tt_list is list of time tables stored with number of times the time table can be used in the network
    tt_list=post_connection.pre.stimtab
    dend_loc=post_connection.dend_loc
    connections={}
    num_choices=np.int(np.round(totalsyn))
    #randomly select subset of synapses on post-synaptic neuron
    if not dend_loc.steep:
        #randomly select the correct fraction of synapses, and then match to randomly selected preyn_tt
        syn_choices=np.random.choice([sc[0] for sc in syncomps],size=num_choices,replace=False)
    else:
        #randomly select the correct fraction of synapses, and then match to randomly selected preyn_tt
        syn_choices=np.random.choice([sc[0] for sc in syncomps],size=num_choices,replace=False,p=[sc[1] for sc in syncomps])
    #randomly select subset of time-tables for spike train input
    presyn_tt=[select_entry(tt_list) for syn in syn_choices]
    for tt,syn in zip(presyn_tt,syn_choices):
        #connect the time table to the synapse with mindelay (dist=0)
        postbranch=util.syn_name(moose.element(syn).parent.path,NAME_HEAD)
        log.debug('CONNECT: TT {} POST {} {}', tt,syn, postbranch)
        synconn(syn,dist,tt,syn_params,netparams.mindelay)
        #save the connection in a dictionary for inspection later
        connections[postbranch]=tt
    return connections

def timetable_input(cells, netparams, postype, model):
    #connect post-synaptic synapses to time tables
    #used for single neuron models only, since populations are connected in connect_neurons
    log.info('CONNECT set: {} {} {}', postype, cells[postype],netparams.connect_dict[postype])
    post_connections=netparams.connect_dict[postype]
    connect_list = {}
    postcell = cells[postype][0]
    for syntype in post_connections.keys():
        connect_list[syntype]={}
        for pretype in post_connections[syntype].keys():
            connect_list[syntype][pretype]={}
            dend_prob=post_connections[syntype][pretype].dend_loc
            print('################',postcell, syntype,pretype)
            allsyncomp_list=moose.wildcardFind(postcell+'/##/'+syntype+'[ISA=SynChan]')
            syncomps,totalsyn=create_synpath_array(allsyncomp_list,syntype,model.param_syn.NumSyn,prob=dend_prob)
            print('SYN TABLE for {} has {} compartments to make {} synapses'.format( syntype, len(syncomps),totalsyn))
            if 'extern' in pretype:
                connect_list[syntype][pretype]=connect_timetable(post_connections[syntype][pretype],syncomps,totalsyn,netparams,model.param_syn)
    return connect_list
                    
def connect_neurons(cells, netparams, postype, model):
    log.debug('CONNECT set: {} {} {}', postype, cells[postype],netparams.connect_dict[postype])
    post_connections=netparams.connect_dict[postype]
    connect_list = {}
    #loop over post-synaptic neurons - convert to list if only singe instance of any type
    if not isinstance(cells[postype],list):
        temp=cells[postype]
        cells[postype]=list([temp])
    for postcell in cells[postype]:
        connect_list[postcell]={}
        postsoma=postcell+'/'+model.param_cond.NAME_SOMA
        xpost=moose.element(postsoma).x
        ypost=moose.element(postsoma).y
        zpost=moose.element(postsoma).z
        #set-up array of post-synapse compartments/synchans
        for syntype in post_connections.keys():
            connect_list[postcell][syntype]={}
            #make a table of possible post-synaptic connections
            for pretype in post_connections[syntype].keys():
                dend_prob=post_connections[syntype][pretype].dend_loc
                allsyncomp_list=moose.wildcardFind(postcell+'/##/'+syntype+'[ISA=SynChan]')
                syncomps,totalsyn=create_synpath_array(allsyncomp_list,syntype,model.param_syn.NumSyn,prob=dend_prob)
                print('SYN TABLE for {} {} {} has {} compartments and {} synapses'.format( postsoma, syntype, pretype,len(syncomps),totalsyn))
                if 'extern' in pretype:
                    print('connect to tt')
                    ####### connect to time tables instead of other neurons in network
                    connect_list[postcell][syntype]=connect_timetable(post_connections[syntype][pretype],syncomps,totalsyn,netparams,model.param_syn)
                else:
                    print('connect to neuron')
                    spikegen_conns=[]
                    ###### connect to other neurons in network: loop over pre-synaptic neurons
                    for precell in cells[pretype]:
                        presoma=precell+'/'+model.param_cond.NAME_SOMA
                        fact=post_connections[syntype][pretype].space_const
                        xpre=moose.element(presoma).x
                        ypre=moose.element(presoma).y
                        zpre=moose.element(presoma).z
                        #calculate distance between pre- and post-soma
                        dist=np.sqrt((xpre-xpost)**2+(ypre-ypost)**2+(zpre-zpost)**2)
                        prob=np.exp(-(dist/fact))
                        connect=np.random.uniform()
                        log.debug('{} {} {} {} {} {}', presoma,postsoma,dist,fact,prob,connect)
                        #select a random number to determine whether a connection should occurmore
                        if connect<prob and dist>0:
                            spikegen_conns.append([moose.wildcardFind(presoma+'/#[TYPE=SpikeGen]')[0],(xpre,ypre,zpre),dist])
                    num_conn=np.random.poisson(post_connections[syntype][pretype].num_conns,len(spikegen_conns))
                    num_choices=min(len(spikegen_conns),len(syncomps))
                    if not dend_loc.steep:
                        syn_choices=np.random.choice([sc[0] for sc in syncomps],size=num_choices,replace=False)
                    else:
                        #randomly select the correct fraction of synapses, and then match to randomly selected preyn_tt
                        syn_choices=np.random.choice([sc[0] for sc in syncomps],size=num_choices,replace=False,p=[sc[1] for sc in syncomps])
                    #log.debug('CONNECT: PRE {} POST {} DIST {}', spikegen,synpath,dist)
                    #list of connections for further processing if desired.  Assumes one conn per synpath (which might be a problem)
                    for prespike,syn,nc in zip(spikegen_conns,syn_choices,numconn):
                        for i in range(nc):
                            postbranch=util.syn_name(moose.element(syn).parent.path,NAME_HEAD)
                            connect_list[postcell][syntype][postbranch]={'postloc':(xpost,ypost,zpost),'pre':precell,'preloc':prespike[1],'dist':prespike[2]}
                            log.debug('{}',connect_list[postcell][syntype])
                            #connect the synapse
                            synconn(syn,prespike[2],prespike[0], model.param_syn,netparams.mindelay,netparams.cond_vel)
    return connect_list

