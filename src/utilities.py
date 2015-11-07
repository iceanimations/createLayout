'''
Created on Oct 30, 2015

@author: qurban.ali
'''
import sys
import pymel.core as pc
sys.path.append("R:/Pipe_Repo/Projects/TACTIC")
import tactic_client_lib as tcl
import qutil
import addKeys
import os.path as osp
from shot_subm.src import backend as ss_be
reload(ss_be)
import re

pc.mel.eval("source \"R:/Pipe_Repo/Users/Hussain/utilities/loader/command/mel/addInOutAttr.mel\";")

server = None

def setServer():
    errors = {}
    global server
    try:
        server = tcl.TacticServerStub(server='dbserver', login='tactic',
                                      password='tactic123',
                                      project='test_mansour_ep')
    except Exception as ex:
        errors['Could not connect to TACTIC'] = str(ex)
    return server, errors
        
def getProjects():
    errors = {}
    projects = []
    if server:
        try:
            projects = server.eval("@GET(sthpw/project.code)")
        except Exception as ex:
            errors['Could not get the list of projects'] = str(ex)
    else:
        errors['Could not find the TACTIC server'] = ''
    return projects, errors
    
        
def setProject(project):
    errors = {}
    if project:
        if server:
            try:
                server.set_project(project)
            except Exception as ex:
                errors['Could not set the project'] = str(ex)
        else:
            errors['Could not find the TACTIC server'] = ''
    return errors
        
def getEpisodes():
    eps = []
    errors = {}
    if server:
        try:
            eps = server.eval("@GET(vfx/episode.code)")
        except Exception as ex:
            errors['Could not get the list of episodes from TACTIC'] = str(ex)
    else:
        errors['Could not find the TACTIC server'] = ""
    return eps, errors
    
def getSequences(ep):
    seqs = []
    errors = {}
    if server:
        if ep:
            try:
                seqs = server.eval("@GET(vfx/sequence['episode_code', '%s'].code)"%ep)
            except Exception as ex:
                errors['Could not get the list of sequences from TACTIC'] = str(ex)
    else:
        errors['Could not find the TACTIC server'] = ""
    return seqs, errors

def getShots(seq):
    shots = {}
    errors = {}
    if server:
        if seq:
            try:
                shots = server.eval("@SOBJECT(vfx/shot['sequence_code', '%s'])"%seq)
                shots = {shot['code']: [shot['frame_in'], shot['frame_out']] for shot in shots}
            except Exception as ex:
                errors['Could not get the list of Shots from TACTIC'] = str(ex)
    else:
        errors['Could not find the TACTIC server'] = ""
    return shots, errors

def getAssetsInSeq(seq):
    assets = []
    errors = {}
    if server:
        try:
            assets[:] = server.eval("@GET(vfx/asset_in_sequence['sequence_code', '%s'].asset_code)"%seq)
        except Exception as ex:
            errors['Could not retrieve assets from TACTIC for %s'%seq] = str(ex)
    else:
        errors['Could not find the TACTIC server'] = ""
    return assets, errors

def getAssetsInShot(shots):
    assets = []
    errors = {}
    if server:
        try:
            assets[:] = server.query('vfx/asset_in_shot', filters=[('shot_code', shots)])
        except Exception as ex:
            errors['Could get the list assets in shots'] = str(ex)
    else:
        errors['Could not find the TACTIC server'] = ""
    return assets, errors

def addAssetsToShot(assets, shot):
    errors = {}
    if server:
        data = [{'asset_code': asset, 'shot_code': shot} for asset in assets]
        try:
            server.insert_multiple('vfx/asset_in_shot', data)
        except Exception as ex:
            errors['Could not add Assets to TACTIC'] = str(ex)
    else:
        errors['Could not find the TACTIC server'] = ""
    return errors

def removeAssetFromShot(assets, shot):
    pass

def getCameraName():
    return qutil.getNiceName(pc.lookThru(q=True))

def getSelectedAssets():
    geosets = ss_be.findAllConnectedGeosets()
    for _set in geosets:
        yield osp.splitext(osp.basename(str(qutil.getRefFromSet(_set).path)))[0].replace('_rig', '').replace('_shaded', '').replace('_model', '').replace('_combined', '')
        
def isSelection():
    return pc.ls(sl=True)

def addCamera(name, start, end):
    cam = qutil.addCamera(name)
    pc.mel.eval('addInOutAttr;')
    cam.attr('in').set(start); cam.out.set(end)
    addKeys.add([cam], start, end)