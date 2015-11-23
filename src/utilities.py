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
from auth import user
import maya.cmds as cmds

pc.mel.eval("source \"R:/Pipe_Repo/Users/Hussain/utilities/loader/command/mel/addInOutAttr.mel\";")

class CCounter(Counter):
    def update_count(self, c):
        for key, value in c.items():
            self[key] = value if self[key] < value else self[key]

server = None

def setServer(serv=None):
    errors = {}
    global server
    if serv: server = serv; return
    try:
        if user.user_registered():
            server = user.get_server()
        else:
            user.login('tactic', 'tactic123')
            server = user.get_server()
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
        if not seqAssets:
            errors['No Asset found in %s'%seq] = ''
        try:
            epAssets = server.query('vfx/asset_in_episode', filters=[('asset_code', seqAssets), ('episode_code', ep)])
        except Exception as ex:
            errors['Could not retrieve asset from TACTIC for %s'%ep] = str(ex)
        if not epAssets:
            errors['No published Assets found in %s'%ep] = ''
        for epAsset in epAssets:
            try:
                snapshot = server.get_snapshot(epAsset, context='rig', version=0, versionless=True, include_paths_dict=True)
                context = 'rig'
            except Exception as ex:
                errors['Could not get the Snapshot from TACTIC for %s'%epAsset['asset_code']] = str(ex)
            if not snapshot:
                snapshot = server.get_snapshot(epAsset, context='model', version=0, versionless=True, include_paths_dict=True)
                context = 'model'
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
                            assets[epAsset['asset_code']] = [context, symlinks.translatePath(getLatestFile(*newPaths), maps)]
                        else:
                            assets[epAsset['asset_code']] = [context, symlinks.translatePath(newPaths[0], maps)]
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
    assetCount = Counter(assets)
    errors = {}
    if server:
        try:
            sobjects = server.query('vfx/asset_in_shot')
            if sobjects:
                sks = []
                for asset, cnt in assetCount.items():
                    for _ in range(cnt):
                        for sobj in sobjects:
                            if sobj['asset_code'] == asset and sobj['shot_code'] == shot:
                                if sobj['__search_key__'] not in sks:
                                    sks.append(sobj['__search_key__'])
                                    break
                if sks:
                    for sk in sks:
                        server.delete_sobject(sk)
            else:
                errors['No Asset found on TACTIC for %s'%shot] = ''
        except Exception as ex:
            errors['Could not delete Assets from %s'%shot] = str(ex)
    else:
        errors['Could not find the TACTIC server'] = ""
    return errors

def getRefsCount():
    refCounts = Counter()
    refs = [osp.normpath(str(x.path)) for x in qutil.getReferences()]
    if refs:
        refCounts.update(refs)
    return refCounts

def getExistingCameraNames():
    names = []
    cams = pc.ls(type='camera')
    for cam in cams:
        names.append(qutil.getNiceName(cam.firstParent().name()).split('_')[-1])
    return names
    

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
    
def isModified():
    return cmds.file(modified=True, q=True)

def getExt():
    return cmds.file(q=True, type=True)[0]

def checkin(seq, context, desc):
    path = cmds.file(location=True, q=True)
    sk = server.query('vfx/sequence', filters=[('code', seq)])[0]['__search_key__']
    server.simple_checkin(sk, context=context, file_path=path, mode='copy', description=desc)