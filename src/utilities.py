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
    return errors
        
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

def addCamera(name, start, end):
    cam = qutil.addCamera(name)
    pc.mel.eval('addInOutAttr;')
    cam.attr('in').set(start); cam.out.set(end)
    addKeys.add([cam], start, end)