'''
Created on Jul 2, 2015

@author: qurban.ali
'''
from uiContainer import uic
from PyQt4.QtGui import QMessageBox, QFileDialog, qApp, QPushButton, QRadioButton
import os
import re
import cui
reload(cui)
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
        self.charPathKey = 'charPathCreateLayout'
        self.seqMenu = cui.MultiSelectComboBox(self, '--Select Shots--')
        self.seqMenu.setToolTip('Select Camera to create them. To create all, leave all cameras unselected')
        self.charMenu = cui.MultiSelectComboBox(self, '--Select Characters--')
        self.charMenu.setToolTip('Select characters to create them. To create all, leave all characters unselected')
        
        self.progressBar.hide()
        self.stopButton.hide()
        self.charLabel.hide()
        self.envLabel.hide()
        self.envFilePathBox.hide()
        self.charFilePathBox.hide()
        self.browseButton1.hide()
        self.browseButton3.hide()
        self.charMenu.hide()
        
        self.browseButton1.clicked.connect(self.setEnvPath)
        self.browseButton2.clicked.connect(self.setSeqPath)
        self.createButton.clicked.connect(self.create)
        self.envFilePathBox.textChanged.connect(lambda text: self.setEnvOptionVar(text))
        self.seqFilePathBox.textChanged.connect(lambda text: self.setSeqOptionVar(text))
        self.charFilePathBox.textChanged.connect(lambda text: self.setCharOptionVar(text))
        self.characterButton.toggled.connect(lambda state: self.charMenu.setVisible(state))
        self.browseButton3.clicked.connect(self.setCharPath)
        self.charFilePathBox.textChanged.connect(self.populateChars)
        self.seqFilePathBox.textChanged.connect(self.populateShots)
        
        
        envPath = qutil.getOptionVar(self.envPathKey)
        if envPath: self.envFilePathBox.setText(envPath)
        seqPath = qutil.getOptionVar(self.seqPathKey)
        if seqPath: self.seqFilePathBox.setText(seqPath)
        charPath = qutil.getOptionVar(self.charPathKey)
        if charPath: self.charFilePathBox.setText(charPath)
        
        self.seqLayout.addWidget(self.seqMenu)
        self.charLayout.addWidget(self.charMenu)
        self.populateShots(self.seqFilePathBox.text())
        
        pc.mel.eval("source \"R:/Pipe_Repo/Users/Hussain/utilities/loader/command/mel/addInOutAttr.mel\";")
        
        
        appUsageApp.updateDatabase('createLayout')
        
    def populateShots(self, path):
        if path:
            if osp.exists(path):
                files = os.listdir(path)
                if files:
                    files = sorted(files)
                    self.seqMenu.addItems([item for item in files if osp.isdir(osp.join(path, item))])
                    return
        self.seqMenu.clearItems()
    
    def populateChars(self, path):
        if path:
            if osp.exists(path):
                files = os.listdir(path)
                if files:
                    files = sorted(files)
                    self.charMenu.addItems([item for item in files if osp.isdir(osp.join(path, item))])
                    return
        self.charMenu.clearItems()
    
    def setCharOptionVar(self, text):
        qutil.addOptionVar(self.charPathKey, text)
        
    def setEnvOptionVar(self, text):
        qutil.addOptionVar(self.envPathKey, text)
    
    def setSeqOptionVar(self, text):
        qutil.addOptionVar(self.seqPathKey, text)
        
    def showMessage(self, **kwargs):
        return msgBox.showMessage(self, __title__, **kwargs)
    
    def setCharPath(self):
        path = self.charFilePathBox.text()
        if path:
            if osp.exists(path):
                path = osp.normpath(path)
            else:
                path = ''
        dirname = QFileDialog.getExistingDirectory(self, 'Select Directory', path, QFileDialog.ShowDirsOnly)
        if dirname:
            self.charFilePathBox.setText(dirname)
        
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
            
    def getCharPath(self):
        path = self.charFilePathBox.text()
        if not path or not osp.exists(path):
            self.showMessage(msg='Character path does not exist',
                             icon=QMessageBox.Information)
            path = ''
        return path
            
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
        self.setCharOptionVar(self.charFilePathBox.text())
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
            
    def isCharacters(self):
        return self.characterButton.isChecked()
            
    def isEnvironment(self):
        return self.environmentButton.isChecked()
        
    def create(self):
        self.clearStatusBox()
        self.appendStatus('Starting...')
        seqPath = self.getSeqPath()
        if seqPath:
            if self.isEnvironment():
                envPaths = self.getEnvPaths()
                if not envPaths:
                    self.showMessage(msg='Environment path not specified',
                                     icon=QMessageBox.Information)
                    envPaths = []
                self.appendStatus('Adding environments')
                for envPath in envPaths:
                    self.appendStatus(envPath)
                    qutil.addRef(envPath)
            if self.isCharacters():
                charPath = self.getCharPath()
                if charPath:
                    items = self.charMenu.getSelectedItems()
                    if not items:
                        items = self.charMenu.getItems()
                    print 'items:', items
                    if items:
                        for item in items:
                            charFilePath = osp.join(charPath, item, 'rig')
                            if osp.exists(charFilePath):
                                files = os.listdir(charFilePath)
                                if files:
                                    mayaFiles = []
                                    for mayaFile in files:
                                        mayaFilePath = osp.join(charFilePath, mayaFile)
                                        if osp.isfile(mayaFilePath) and (mayaFile.endswith('.ma') or mayaFile.endswith('.mb')):
                                            mayaFiles.append(mayaFile)
                                    if mayaFiles:
                                        if len(mayaFiles) > 1:
                                            box = cui.SelectionBox(self,
                                                                   [QRadioButton(name) for name in mayaFiles],
                                                                   'More than one files found, please select one in:\n%s'%charFilePath)
                                            box.exec_()
                                            selectedItems = box.getSelectedItems()
                                            if not selectedItems:
                                                continue
                                            else:
                                                filePath = osp.join(charFilePath, selectedItems[0])
                                                if osp.exists(filePath):
                                                    self.appendStatus('Adding character %s'%filePath)
                                                    qutil.addRef(filePath)
                                                else:
                                                    self.appendStatus('<b>Warning: </b> file does not exist %s'%filePath)
                                    else:
                                        self.appendStatus('<b>Warning: </b> No maya file found in %s'%charFilePath)
                                else:
                                    self.appendStatus('<b>Warning: </b> No files found in %s'%charFilePath)
                            else:
                                self.appendStatus('<b>Warning: </b> Character does not exist %s'%charFilePath)
            self.appendStatus('Reading sequence directory')
            shots = self.seqMenu.getSelectedItems()
            if not shots:
                shots = self.seqMenu.getItems()
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
                cam = self.addCamera(shot, start, end)
                if self.isImagePlane():
                    self.addImagePlane(cam, osp.join(seqPath, shot, 'animatic'))
            self.appendStatus('DONE')
        else:
            self.appendStatus('Sequence path not found')
            
    def isImagePlane(self):
        return self.imagePlaneButton.isChecked()

    def getStartEnd(self, seqPath, shot):
        path = osp.join(seqPath, shot, 'animatic')
        files = os.listdir(path)
        if files:
            rng = self.getRange(files)
            if rng:
                return min(rng), max(rng)
        else:
            self.appendStatus('<b>Warning: </b>No files found in %s'%path)
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
        return cam
        
    def addImagePlane(self, camera, path):
        self.appendStatus('Creating image plane for %s'%camera.name())
        files = os.listdir(path)
        if not files:
            self.appendStatus('<b>Warning: </b> Could not create imagePlane for %s'%camera.name())
            return
        try:
            filePath = [osp.join(path, phile) for phile in files if osp.isfile(osp.join(path, phile))][0]
        except IndexError:
            self.appendStatus('<b>Warning: </b> No files found create imagePlane for %s'%camera.name())
            return
        node = pc.PyNode(pc.mel.createImagePlane(camera)[0])
        node.imageName.set(filePath)
        node.useFrameExtension.set(1)