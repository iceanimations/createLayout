'''
Created on Oct 30, 2015

@author: qurban.ali
'''
import pymel.core as pc
import imaya
from collections import Counter
import maya.cmds as cmds

projectKey = 'createLayoutProjectKey'
episodeKey = 'createLayoutEpisodeKey'
sequenceKey = 'createLayoutSequenceKey'

def createCacheNamesOnGeoSets():
    geosets = [gs for gs in pc.ls(exactType=pc.nt.ObjectSet)
               if gs.name().lower().endswith('_geo_set')]
    counts = Counter([imaya.getNiceName(geoset.name()).replace('_geo_set', '') for geoset in geosets])
    counts = {key: list(reversed(range(1, val + 1))) for key, val in counts.items()}
    for geoset in geosets:
        niceName = imaya.getNiceName(geoset.name()).replace('_geo_set', '')
        if not geoset.hasAttr('cacheName'):
            pc.addAttr(geoset, sn='cname', ln='cacheName', dt='string', h=True)
        niceName += '_%s'%str(counts[niceName].pop()).zfill(2)
        geoset.cacheName.set(niceName)
        
def createProjectContext(project, episode, sequence):
    imaya.addFileInfo(projectKey, project)
    imaya.addFileInfo(episodeKey, episode)
    imaya.addFileInfo(sequenceKey, sequence)
    
def saveScene():
    cmds.file(save=True, f=True)