#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 10 11:34:56 2019

@author: jkl

RUN ALL SECTION ON THE TEST AND CHECK THE GRAPH PRODUCED
"""

import numpy as np
import os
import time
import matplotlib.pyplot as plt
import api.meshTools as mt
from api.Survey import Survey
from api.R2 import R2

tstart = time.time()

#%% testing the R2 class
plt.close('all')
print('-------------Testing simple 2D inversion ------------')
t0 = time.time()
k = R2()
k.createSurvey('./api/test/syscalFileTopo.csv', ftype='Syscal')
k.pseudo(contour=True)
k.importElec('./api/test/elecTopo.csv')
k.createMesh(typ='quad',elemx=4)
k.showMesh()
k.createMesh(typ='trian',cl=0.1, cl_factor=5)
k.showMesh()
#k.linfit()
#k.pwlfit()

#k.lmefit(iplot=True)
k.write2in()
#k.write2protocol(err=True, errTot=True)
k.invert()
k.showResults(attr='Conductivity(mS/m)')
#k.showInParaview()
print('elapsed: {:.4}s'.format(time.time() - t0))


#%% test for borehole
plt.close('all')
print('-------------Testing borehole------------')
t0 = time.time()
k = R2()
k.createSurvey('./api/test/protocolXbh.dat', ftype='forwardProtocolDC')
x = np.genfromtxt('./api/test/elecXbh.csv', delimiter=',')
k.elec[:,[0,2]] = x[:,:2]
buried = x[:,2].astype(bool)
k.createMesh('trian', buried=buried, cl=0.5, cl_factor=20)
k.showMesh()
k.createMesh('quad', buried=buried, elemx=12)
k.showMesh()
k.invert()
k.showIter(index=0)
k.showIter(index=1)
k.showResults(sens=False)
print('elapsed: {:.4}s'.format(time.time() - t0))


#%% test for IP
plt.close('all')
print('-------------Testing IP ------------')
t0 = time.time()
k = R2(typ='cR2')
#k.createSurvey('api/test/IP/rifleday8.csv', ftype='Syscal')
#k.createSurvey('api/test/IP/syscalFileIP.csv')
k.createSurvey('api/test/IP/protocolIP2D.dat', ftype='ProtocolIP')
k.createMesh('quad')
#k.pwlfit()
#k.plotIPFit()
k.err=True # there is already error inside the protocol.dat imported
k.invert()
k.showResults(attr='Magnitude(Ohm-m)', sens=False)
k.showResults(attr='Phase(mrad)', sens=False)
k.pseudoError()
print('elapsed: {:.4}s'.format(time.time() - t0))


#%% test for timelapse inversion
plt.close('all')
print('-------------Testing Time-lapse in // ------------')
t0 = time.time()
k = R2()
k.createTimeLapseSurvey('api/test/testTimelapse')
k.linfit()
k.pwlfit()
k.err = True
k.invert(iplot=False, parallel=True, ncores=3)
k.saveInvPlots(attr='difference(percent)')
k.showResults(index=1)
k.showResults(index=2)
k.showResults(index=3)
print('elapsed: {:.4}s'.format(time.time() - t0))


#%% test for batch inversion with moving electrodes
plt.close('all')
print('-------------Testing Batch Inversion ------------')
t0 = time.time()
k = R2()
k.createBatchSurvey('api/test/testTimelapse')
for s in k.surveys:
    s.elec[3,0] = np.random.normal(s.elec[3,0], s.elec[3,0]*0.05)
k.createMesh('trian')
k.pwlfit()
k.err = True
k.invert(parallel=True, iMoveElec=True)
k.showResults(index=0)
k.showResults(index=1)
k.showResults(index=2)
k.showResults(index=3)
print('elapsed: {:.4}s'.format(time.time() - t0))


#%% test mesh with buried electrodes
#
#print('-------------Testing Buried electrodes Inversion ------------')
#k = R2()
#k.createSurvey('api/test/syscalFile.csv')
#elec = k.elec
#elec[:,2] = -0.5 # let's bury them all
##elec[0,2] = 0
#k.setElec(elec)
#buried = np.ones(elec.shape[0], dtype=bool)
##buried[[0,-1]] = False # comment it and it will work
#surface = np.array([[0,0],[7,0]])
#k.createMesh(typ='quad', buried=buried, surface=surface)
#k.showMesh()

#k = R2()
#k.createSurvey('api/test/syscalFile.csv', ftype='Syscal')
#k.elec[:,2] = np.tile(np.arange(0,-12,-1),2)
#k.elec[:,0] = np.repeat([0,8], 12)
#k.elec[1:11,:2] = np.c_[np.ones(10)*2, np.linspace(0,-4,10)]
#buried = np.ones(k.elec.shape[0], dtype=bool)
#buried[[0,12]] = False
#surface = np.array([[-2,0],[10,0]])
#k.createMesh(typ='quad')
#k.showMesh()
#k.createMesh(typ='trian', buried=buried, cl=0.5, cl_factor=5) # works well
#k.showMesh()
#k.invert()
#k.showResults()
#
##%%
#k = R2()
#k.createSurvey('./api/test/syscalFile.csv')
#k.elec[3,1] = -1
#buried = np.zeros(k.elec.shape[0], dtype=bool)
#buried[3] = True
#k.createMesh('quad', buried=buried)
#k.invert()

#%% forward modelling
plt.close('all')
print('-------------Testing Forward DC Modelling ------------')
t0 = time.time()
k = R2(typ='R2')
k.setElec(np.c_[np.linspace(0,5.75, 24), np.zeros((24, 2))])
k.createMesh(typ='trian')

#k.createSequence(params=[('wenner_alpha',1), # uncomment for wenner array
#                         ('wenner_alpha',2),
#                         ('wenner_alpha',3),
#                         ('wenner_alpha',4),
#                         ('wenner_alpha',5),
#                         ('wenner_alpha',6),
#                         ('wenner_alpha',7),
#                         ('wenner_alpha',8),
#                         ('wenner_alpha',9),
#                         ('wenner_alpha',10)])

## full API function
k.addRegion(np.array([[1,0],[2,0],[2,-0.5],[1,-0.5],[1,0]]), 10, -3)
k.addRegion(np.array([[3,-0.5],[3.5,-0.5],[3.5,-1],[3,-1],[3,-0.5]]), 20, blocky=True, fixed=True)
k.addRegion(np.array([[4,0],[5,0],[5,-0.5],[4,-0.5],[4,0]]), 30, blocky=True, fixed=False)

## full GUI function
#k.createModel() # manually define 3 regions
#k.assignRes0({1:500, 2:20, 3:30}, {1:1, 2:2, 3:1}, {1:False, 2:False, 3:True})

# creating sequence
k.createSequence([('dpdp1', 1, 8),
                  ('wenner_alpha', 1),
                  ('wenner_alpha', 2)])
    

k.forward(iplot=True, noise=0.05)
k.invert(iplot=True)

# the forward initial model
#k.showResults(index=0, attr='Resistivity(Ohm-m)', sens=False) # not for cR2
#k.showResults(index=0, attr='Phase(mrad)')
#k.showResults(index=0, attr='Magnitude(Ohm-m)')

# the inverted
k.showResults(index=1, attr='Resistivity(Ohm-m)', sens=True, vmin=10, vmax=120) # not for cR2
#k.showResults(index=1, attr='Phase(mrad)')
#k.showResults(index=1, attr='Magnitude(Ohm-m)')
print('elapsed: {:.4}s'.format(time.time() - t0))


#%% test forward IP modelling
plt.close('all')
print('-------------Testing Forward IP Modelling ------------')
t0 = time.time()
k = R2(typ='cR2')
k.elec = np.c_[np.linspace(0,5.75, 24), np.zeros((24, 2))]
k.createMesh(typ='trian')
#
## full API function
k.addRegion(np.array([[1,0],[2,0],[2,-0.5],[1,-0.5],[1,0]]), 10, -3)

k.forward(iplot=True, noise=0.05)
k.invert(iplot=True)

# the forward initial model
k.showResults(index=0, attr='Phase(mrad)')
k.showResults(index=0, attr='Magnitude(Ohm-m)')

# the inverted
k.showResults(index=1, attr='Phase(mrad)')
k.showResults(index=1, attr='Magnitude(Ohm-m)')
print('elapsed: {:.4}s'.format(time.time() - t0))


#%% test Paul River
plt.close('all')
print('-------------Testing Buried Electrodes in Fixed River ------------')
t0 = time.time()
k = R2()
k.createSurvey('./api/test/primeFile.dat', ftype='BGS Prime')
x = np.genfromtxt('./api/test/primePosBuried.csv', delimiter=',')
k.elec[:,[0,2]] = x[:,:2]
surface = np.array([[0.7, 92.30],[10.3, 92.30]])
buried = x[:,2].astype(bool)
k.createMesh(typ='trian', buried=buried, surface=surface, cl=0.2, cl_factor=10)
k.createMesh(typ='quad',buried=buried)
k.showMesh()
xy = k.elec[1:21,[0,2]]
k.addRegion(xy, res0=18, blocky=True, fixed=False)
k.param['b_wgt'] = 0.04 # doesn't work
k.invert()
k.showResults(sens=False)
print('elapsed: {:.4}s'.format(time.time() - t0))


#%% 3D testing
from api.R2 import R2
plt.close('all')
print('-------------Testing 3D inversion ------------')
t0 = time.time()
k = R2(typ='R3t')
k.createSurvey('api/test/protocol3D.dat', ftype='Protocol')
elec = np.genfromtxt('api/test/electrodes3D.csv',delimiter=',')
k.setElec(elec)
k.createMesh(cl=2)
#k.mesh.write_vtk('api/test/mesh3D.vtk',title='3D mesh with flat surface')
k.invert()
k.showResults() 
k.showSlice(axis='z')
k.showSlice(axis='x')
k.showSlice(axis='y')
k.pseudoError()
k.showInversionErrors()
print('elapsed: {:.4}s'.format(time.time() - t0))


#%% 3D testing importing a mesh
plt.close('all')
print('-------------Testing 3D inversion ------------')
t0 = time.time()
k = R2(typ='R3t')
k.createSurvey('api/test/protocol3D.dat', ftype='Protocol')
elec = np.genfromtxt('api/test/electrodes3D.csv',delimiter=',')
k.setElec(elec)
k.importMesh('api/test/mesh3D.vtk')
#k.write2in()
#k.param = param
k.invert()
k.showResults() 
k.showSlice(axis='z')
k.showSlice(axis='x')
k.showSlice(axis='y')
print('elapsed: {:.4}s'.format(time.time() - t0))


#%% 3D ip testing
plt.close('all')
print('-------------Testing 3D IP inversion ------------')
t0 = time.time()
k = R2(typ='cR3t')
k.createSurvey('api/test/IP/protocol3Dip.dat', ftype='Protocol')
elec = np.genfromtxt('api/test/electrodes3Dip.csv', delimiter=',')
k.setElec(elec)
k.createMesh(cl=3)
k.showMesh()
k.invert()
k.showResults()
k.showSlice(index=0)
k.showSlice(axis='z')
k.showSlice(axis='x')
k.showSlice(axis='y')
k.showInParaview()
print('elapsed: {:.4}s'.format(time.time() - t0))


#%% 3D with moving electrodes (specialy dedicated to Jimmy ;)
plt.close('all')
print('-------------Testing 3D inversion ------------')
t0 = time.time()
k = R2(typ='R3t')
#k.createBatchSurvey('api/test/3d/data/', ftype='Protocol')
k.createTimeLapseSurvey('api/test/3d/data/', ftype='Protocol')
elecList = [np.genfromtxt('api/test/3d/elec/' + f, delimiter=',') for f in os.listdir('api/test/3d/elec/')]
k.setElec(elec=None, elecList=elecList)
k.createMesh(cl=2)
k.param['reg_mode'] = 1 # background regularization
k.invert(parallel=True, iMoveElec=True)
k.showInParaview()
print('elapsed: {:.4}s'.format(time.time() - t0))



print('total time running the test = {:.4f}s'.format(time.time() - tstart))
