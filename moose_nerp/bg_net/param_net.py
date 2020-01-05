#param_net.py

from moose_nerp.prototypes.ttables import TableSet
from moose_nerp.prototypes.syn_proto import ShortTermPlasParams,SpikePlasParams
from moose_nerp.prototypes.util import NamedList

#need to put these Namedlists somewhere in prototypes
from moose_nerp.gp_net.param_net import dend_location, connect

netname='/bg'
confile='bg_connect'
outfile='bg_out'

###############
#three types of distributions
even_distr=dend_location(postsyn_fraction=0.5)
proximal_distr= dend_location(mindist=0e-6,maxdist=80e-6,postsyn_fraction=1)
distal_distr=dend_location(mindist=50e-6,maxdist=400e-6,postsyn_fraction=.1)#,half_dist=50e-6,steep=1)

##connections between regions
#Inputs to ep/SNr from Striatum/D1 and GPe/proto
connect_dict={'ep':{'gaba':{}}}
connect_dict['ep']['gaba']['proto']=connect(synapse='gaba', pre='proto', post='ep', probability=0.5)
connect_dict['ep']['gaba']['Lhx6']=connect(synapse='gaba', pre='Lhx6', post='ep', probability=0.5)
connect_dict['ep']={'gaba':{}}
connect_dict['ep']['gaba']['D1']=connect(synapse='gaba', pre='D1', post='ep', probability=0.5)

#Inputs from striatum to GPe
connect_dict['Npas']={'gaba':{}}
connect_dict['Npas']['gaba']['D2']=connect(synapse='gaba', pre='D2', post='Npas', probability=0.5)
connect_dict['Lhx6']={'gaba':{}}
connect_dict['Lhx6']['gaba']['D2']=connect(synapse='gaba', pre='D2', post='Lhx6', probability=0.5)
connect_dict['proto']={'gaba':{}}
connect_dict['proto']['gaba']['D2']=connect(synapse='gaba', pre='D2', post='proto', probability=0.5)

#Inputs from GPe back to Striatum
connect_dict['D2']={'gaba':{}}
connect_dict['D2']['gaba']['Npas']=connect(synapse='gaba', pre='Npas', post='D2', probability=0.5)
connect_dict['D1']={'gaba':{}}
connect_dict['D1']['gaba']['Npas']=connect(synapse='gaba', pre='Npas', post='D1', probability=0.5)
connect_dict['FSI']={'gaba':{}}
connect_dict['FSI']['gaba']['Lhx6']=connect(synapse='gaba', pre='Lhx6', post='FSI', probability=0.5)

#
#these are not used because not imported in init and not part of connect_dict
#ADD these when connect to striatal network

mindelay={}
cond_vel={}
############## All of these inputs get created
#tables of extrinsic inputs 
#first string is name of the table in moose, and 2nd string is name of external file
#tt_STN = TableSet('tt_STN', 'gp_net/STN_lognorm_freq18.0',syn_per_tt=2)
tt_Ctx_SPN = TableSet('CtxSPN', 'spn1_net/Ctx_exp_freq10.0',syn_per_tt=2)

 
