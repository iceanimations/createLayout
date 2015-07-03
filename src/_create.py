'''
Created on Jul 2, 2015

@author: qurban.ali
'''
from uiContainer import uic
from PyQt4.QtGui import QMessageBox, QFileDialog, qApp, QPushButton
import os
import re
import os.path as osp
import qtify_maya_window as qtfy
import pymel.core as pc
import appUsageApp
import msgBox
import qutil
reload(qutil)
import re

root_path = osp.dirname(osp.dirname(__file__))
ui_path = osp.join(root_path, 'ui')
__title__ = 'Create Layout'

Form, Base = uic.loadUiType(osp.join(ui_path, 'main.ui'))
class LayoutCreator(Form, Base):
    def __init__(self, parent=qtfy.getMayaWindow()):
        super(LayoutCreator, self).__init__(parent)
        self.setupUi(self)
        
        self.envPathKey = 'envPathCreateLayout'
        self.seqPathKey = 'seqPathCreateLayout'
        
        self.progressBar.hide()
        self.stopButton.hide()
        
        self.browseButton1.clicked.connect(self.setEnvPath)
        self.browseButton2.clicked.connect(self.setSeqPath)
        self.createButton.clicked.connect(self.create)
        self.envFilePathBox.textChanged.connect(lambda text: self.setEnvOptionVar(text))
        self.seqFilePathBox.textChanged.connect(lambda text: self.setSeqOptionVar(text))
        
        envPath = qutil.getOptionVar(self.envPathKey)
        if envPath: self.envFilePathBox.setText(envPath)
        seqPath = qutil.getOptionVar(self.seqPathKey)
        if seqPath: self.seqFilePathBox.setText(seqPath)
        
    def setEnvOptionVar(self, text):
        qutil.addOptionVar(self.envPathKey, text)
    
    def setSeqOptionVar(self, text):
        qutil.addOptionVar(self.seqPathKey, text)
        
    def showMessage(self, **kwargs):
        return msgBox.showMessage(self, __title__, **kwargs)
        
    def setEnvPath(self):
        path = ''
        try:
            path = self.envFilePathBox.text().split(',')[-1]
            if path:
                if osp.exists(path):
                    path = osp.normpath(path)
                    path = osp.dirname(path)
                else:
                    path = ''
        except IndexError:
            pass
        filenames = QFileDialog.getOpenFileNames(self, 'Select Files', path, '*.ma *.mb')
        if filenames:
            names = self.envFilePathBox.text()
            names = ','.join(set(names.split(',') + filenames))
            # make them unique
            if names.startswith(','):
                names = names[1:]
            self.envFilePathBox.setText(names)
            
    def setSeqPath(self):
        path = self.seqFilePathBox.text()
        if path:
            if osp.exists(path):
                path = osp.normpath(path)
            else:
                path = ''
                
        dirname = QFileDialog.getExistingDirectory(self, 'Select Directory', path, QFileDialog.ShowDirsOnly)
        if dirname:
            self.seqFilePathBox.setText(dirname)
            
    def getEnvPaths(self):
        paths = self.envFilePathBox.text().split(',')
        badPaths = []
        goodPaths = []
        if paths:
            for path in paths:
                if path:
                    if not osp.exists(path):
                        badPaths.append(path)
                    else:
                        goodPaths.append(path)
        if badPaths:
            btn = self.showMessage(msg='Could not find some environments',
                                   ques='Do you want to ignore these environments and continue?',
                                   icon=QMessageBox.Question,
                                   details='\n'.join(badPaths),
                                   btns=QMessageBox.Yes|QMessageBox.No)
            if btn == QMessageBox.No:
                return
        return goodPaths
    
    def getSeqPath(self):
        path = self.seqFilePathBox.text()
        if not path or not osp.exists(path):
            self.showMessage(msg='Sequence path does not exist',
                             icon=QMessageBox.Information)
            path = ''
        return path
        
    def closeEvent(self, event):
        self.setEnvOptionVar(self.envFilePathBox.text())
        self.setSeqOptionVar(self.seqFilePathBox.text())
        self.deleteLater()
        
    def appendStatus(self, msg):
        self.statusBox.append(msg)
        qApp.processEvents()
    
    def clearStatusBox(self):
        self.statusBox.clear()
        
    def isShotNameValid(self, name):
        parts = name.split('_')
        if len(parts) == 2:
            if re.match('SQ\\d{3}', parts[0]) and re.match('SH\\d{3}', parts[1]):
                return True
            
    def cameraOnly(self):
        return self.cameraButton.isChecked()
        
    def create(self):
        self.clearStatusBox()
        self.appendStatus('Starting...')
        seqPath = self.getSeqPath()
        if seqPath:
            if not self.cameraOnly():
                envPaths = self.getEnvPaths()
                if not envPaths:
                    if not self.cameraOnly():
                        self.showMessage(msg='Environment path not specified',
                                         icon=QMessageBox.Information)
                        self.clearStatusBox()
                        return
                self.appendStatus('Adding environments')
                for envPath in envPaths:
                    self.appendStatus(envPath)
                    qutil.addRef(envPath)
            self.appendStatus('Reading sequence directory')
            shots = os.listdir(seqPath)
            shots = [shot for shot in shots if osp.isdir(osp.join(seqPath, shot))]
            badShots = []
            goodShots = []
            for shot in shots:
                if self.isShotNameValid(shot):
                    goodShots.append(shot)
                else:
                    badShots.append(shot)
            self.appendStatus(str(len(goodShots)) +' shots found')
            if badShots:
                ignoreButton = QPushButton('Ignore', self)
                includeButton = QPushButton('Include', self)
                btn = self.showMessage(msg='Some bad directory names found in the specified sequence',
                                       ques='What do you want to do with the bad directories?',
                                       icon=QMessageBox.Question,
                                       btns=QMessageBox.Cancel,
                                       customButtons=[ignoreButton, includeButton],
                                       details='\n'.join(badShots))
                if btn == QMessageBox.Cancel:
                    return
                if btn == includeButton:
                    goodShots.extend(badShots)
            self.appendStatus('Creating Camera')
            for shot in goodShots:
                start, end = self.getStartEnd(seqPath, shot)
                self.appendStatus('Creating '+ shot + '  (Range: %s - %s)'%(start, end))
                self.addCamera(shot, start, end)
            self.appendStatus('DONE')
        else:
            self.appendStatus('Sequence path not found')

    def getStartEnd(self, seqPath, shot):
        path = osp.join(seqPath, shot, 'animatic')
        files = os.listdir(path)
        if files:
            rng = self.getRange(files)
            if rng:
                return min(rng), max(rng)
        return 0, 0
    
    def getRange(self, files):
        rng = []
        for phile in files:
            try:
                rng.append(int(phile.split('.')[-2]))
            except:
                pass
        return rng

    def addCamera(self, name, start, end):
        cam = qutil.addCamera(name)
        pc.mel.eval('addInOutAttr;')
        cam.attr('in').set(start); cam.out.set(end)