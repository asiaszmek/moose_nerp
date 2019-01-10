#param_net.py
####################### Populations
from moose_nerp.prototypes.util import NamedList
from moose_nerp.prototypes.ttables import TableSet
from moose_nerp.prototypes import util as _util

neur_distr=NamedList('neur_distr', 'neuronname spacing percent')

netname='/ep'
confile='ep_connect'
outfile='ep_out'

spacing=60e-6 #need value and reference
#
#0,1,2 refer to x, y and z
grid={}
grid[0]={'xyzmin':0,'xyzmax':100e-6,'inc':spacing}
grid[1]={'xyzmin':0,'xyzmax':100e-6,'inc':spacing}
grid[2]={'xyzmin':0,'xyzmax':0,'inc':0}

#Do not include a neuron type in pop_dict if the the prototype does not exist
#Change neuronname to cellType
neuron1pop=neur_distr(neuronname='ep', spacing=grid,percent=1.0) 

#Change pop_dict to popParams
pop_dict={'ep':neuron1pop}

chanSTD = {
    'KDr': 0.0397,
    'Kv3': 0.0386,
    'KvS': 0.0743,
    'KvF': 0.0173,
    'BKCa': 0.0238,
    'SKCa': 0.295,
    'HCN1': 0.2454,
    'HCN2': 0.253,
    'Ca': 0.1671,
    'NaF': 0.0635,
    'NaS': 0.215,
}
chanvar={'ep':chanSTD}

####################### Connections
#for improved NetPyne correspondance: change synapse to synMech, change pre to source
#mindist, maxdist, half_dist, steep are alternatives to postsyn_fraction (ext_connect) or probability (connect)
#these refer to dendritic location of post-synaptic target as follows:
#connect_prob=0 if dist<mindist
#connect_prob=0 if dist>maxdist
#connect_prob = probability if dist between mindist and maxdist
#if half_dist is defined:
#for steep>0: connect_prob=1 if dist>maxdist and 0 if dist<mindist 
#connect_prob=(dist-mindist)^steep/((dist-mindist)^steep+half_dist^steep)
#make steep<0 to switch slope and have connect_prob=1 if dist<mindist and 0 if dist>maxdist
#do not use steep (or set to zero) to have constant connection probability between min and maxdist
dend_location=NamedList('dend_location','mindist=0 maxdist=1 maxprob=None half_dist=None steep=0 postsyn_fraction=None')
#probability for intrinsic is the probability of connecting pre and post. space_const allows cell body distance dependence
connect=NamedList('connect','synapse pre post space_const=None probability=None dend_loc=None')
ext_connect=NamedList('ext_connect','synapse pre post dend_loc=None')

#tables of extrinsic inputs
#first string is name of the table in moose, and 2nd string is name of external file
tt_STN = TableSet('tt_STN', 'STN_4x4',syn_per_tt=2)
tt_STR = TableSet('tt_Str', 'Str_4x4',syn_per_tt=2)
tt_GPe = TableSet('tt_GPe', 'GPe_4x4',syn_per_tt=2)

ConnSpaceConst=125e-6

#description of intrinsic inputs
#neur1pre_neur1post=connect(synapse='gaba', pre='ep', post='gaba', probability=0)#need reference for no internal connections
#description of synapse and dendritic location of extrinsic inputs
GPe_distr=dend_location(mindist=0,maxdist=60e-6,half_dist=30e-6,steep=-1)
Str_distr=dend_location(mindist=30e-6,maxdist=1000e-6,postsyn_fraction=1,half_dist=100e-6,steep=1)
STN_distr=dend_location(postsyn_fraction=0.5)
#post syn fraction: what fraction of synapse is contacted by time tables specified in pre 
ext1_neur1post=ext_connect(synapse='ampa',pre=tt_STN,post='ep', dend_loc=STN_distr)# need reference
ext2_neur1post=ext_connect(synapse='gaba',pre=tt_GPe,post='ep', dend_loc=GPe_distr)
ext3_neur1post=ext_connect(synapse='gaba',pre=tt_STR,post='ep', dend_loc=Str_distr)
#ext1_neur1post=ext_connect(synapse='ampa',pre=tt_STN,post='ep')# need reference

#Collect all connection information into dictionaries
#1st create one dictionary for each post-synaptic neuron class
ep={}
#connections further organized by synapse type
#the dictionary key for tt must have 'extern' in it
ep['gaba']={'extern2': ext2_neur1post, 'extern3':ext3_neur1post}
ep['ampa']={'extern1': ext1_neur1post}

#Then, collect the post-synaptic dictionaries into a single dictionary.
#for NetPyne correspondance: change connect_dict to connParams
connect_dict={}
connect_dict['ep']=ep

# m/sec - GABA and the Basal Ganglia by Tepper et al
cond_vel=0.8 #conduction velocity
mindelay=1e-3

