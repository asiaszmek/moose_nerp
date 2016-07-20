"""\
Make a plasticity device in that compartment/synapse
"""
from __future__ import print_function, division
import os
import moose

from param_sim import printinfo, printMoreInfo
import param_cond as parcond

def plasticity(synchan,Thigh,Tlow,highfac,lowfac,caName):
    compname = os.path.dirname(synchan.path)
    calname = compname + '/' + caName
    cal=moose.element(calname)
    shname=synchan.path+'/SH'
    sh=moose.element(shname)
    if printinfo:
        print("PLAS",synchan.path,sh.synapse[0],cal.path)
    #
    plasname=compname+'/plas'
    plas=moose.Func(plasname)
    #FIRST: calculate the amount of plasticity
    #y is input plasticity trigger (e.g. Vm or Ca) 
    moose.connect(cal,'concOut',plas,'yIn')
    #x is the high threshold, z is the low threshold
    #This gives parabolic shape to plasticity between the low and high threshold
    #highfac and lowfac scale the weight change (set in SynParams.py)
    expression=highfac+"(y>x)*(y-x)+(y>z)*(x>y)*(y-z)*(x-y)"+lowfac
    plas.expr=expression
    #Must define plasticity expression first, else these next assignments do nothing
    plas.x=Thigh
    plas.z=Tlow
    #SECOND: accumulate all the changes, as percent increase or decrease
    plasCum=moose.Func(plasname+'Cum')
    #need input from the plasticity thresholding function to y 
    moose.connect(plas,'valueOut',plasCum,'xIn')
    moose.connect(plasCum,'valueOut',plasCum, 'yIn')
    plasCum.expr="(x+1.0)*y*z"
    plasCum.z=sh.synapse[0].weight
    plasCum.y=1.0
    moose.connect(plasCum,'valueOut',sh.synapse[0],'setWeight')
    
    return {'cum':plasCum,'plas':plas}

def addPlasticity(synPop,Thigh,Tlow,highfact,lowfact,cells,ca_name):
    plaslist=[]
    if printinfo:
        print("PLAS", cells)
    if not cells:
        for synchan in synPop:
            plaslist.append(plasticity(synchan,Thigh,Tlow,highfact,lowfact,ca_name))
    else:
        for cell in cells:
            for br in range(len(synPop)):
                p = synPop[br].path.split('/')
                compname = p[parcond.compNameNum] + '/' + p[parcond.chanNameNum]
                synchan=moose.element(cell+'/'+compname)
                if printMoreInfo:
                    print("ADDPLAS",cell,compname,synchan)
                plaslist.append(plasticity(synchan,Thigh,Tlow,highfact,lowfact,ca_name))
    return plaslist
