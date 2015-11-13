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
import iutil.symlinks as symlinks
import os
from collections import Counter

pc.mel.eval("source \"R:/Pipe_Repo/Users/Hussain/utilities/loader/command/mel/addInOutAttr.mel\";")

class CCounter(Counter):
    def update_count(self, c):
        for key, value in c.items():
            self[key] = value if self[key] < value else self[key]

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

def getLatestFile(file1, file2):
    latest = file1
    if os.path.getmtime(file2) > os.path.getmtime(file1):
        latest = file2
    return latest

def getAssetsInSeq(ep, seq):
    assets = {}
    errors = {}
    if server:
        try:
            maps = symlinks.getSymlinks(server.get_base_dirs()['win32_client_repo_dir'])
        except Exception as ex:
            errors['Could not retrieve the maps from TACTIC'] = str(ex)
        try:
            seqAssets = server.eval("@GET(vfx/asset_in_sequence['sequence_code', '%s'].asset_code)"%seq)
        except Exception as ex:
            errors['Could not retrieve assets from TACTIC for %s'%seq] = str(ex)
        try:
            epAssets = server.query('vfx/asset_in_episode', filters=[('asset_code', seqAssets), ('episode_code', ep)])
        except Exception as ex:
            errors['Could not retrieve asset from TACTIC for %s'%ep] = str(ex)
        if not epAssets:
            errors['No published Assets found in %s'%ep]
        for epAsset in epAssets:
            try:
                snapshot = server.get_snapshot(epAsset, context='rig', version=0, versionless=True, include_paths_dict=True)
            except Exception as ex:
                errors['Could not get the Snapshot from TACTIC for %s'%epAsset['asset_code']] = str(ex)
            #if not snapshot: snapshot = server.get_snapshot(ep_asset, context='shaded', version=0, versionless=True, include_paths_dict=True)
            if snapshot:
                paths = snapshot['__paths_dict__']
                if paths:
                    newPaths = None
                    if paths.has_key('maya'):
                        newPaths = paths['maya']
                    elif paths.has_key('main'):
                        newPaths = paths['main']
                    else:
                        errors['Could not find a Maya file for %s'%epAsset['asset_code']] = 'No Maya or Main key found'
                    if newPaths:
                        if len(newPaths) > 1:
                            assets[epAsset['asset_code']] = symlinks.translatePath(getLatestFile(*newPaths), maps)
                        else:
                            assets[epAsset['asset_code']] = symlinks.translatePath(newPaths[0], maps)
                    else:
                        errors[epAsset['asset_code']] = 'No Maya file found'
                else:
                    errors[epAsset['asset_code']] = 'No Paths found to a file'
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
    errors = {}
    if server:
        try:
            sobjects = server.query('vfx/asset_in_shot', filters=[('asset_code', assets), ('shot_code', shot)])
            if sobjects:
                for sobj in sobjects:
                    server.delete_sobject(sobj['__search_key__'])
            else:
                errors['No Asset found on TACTIC for %s'%shot] = ''
        except Exception as ex:
            errors['Could not delete Assets from %s'%shot] = str(ex)
    else:
        errors['Could not find the TACTIC server'] = ""
    return errors

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