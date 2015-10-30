'''
Created on Jul 2, 2015

@author: qurban.ali
'''
from uiContainer import uic
from PyQt4.QtGui import QMessageBox, qApp
import os
import cui
import os.path as osp
import qtify_maya_window as qtfy
import appUsageApp
import qutil
import utilities as utils

reload(utils)
reload(qutil)
reload(cui)

root_path = osp.dirname(osp.dirname(__file__))
ui_path = osp.join(root_path, 'ui')
__title__ = 'Create Layout Scene'

Form, Base = uic.loadUiType(osp.join(ui_path, 'main.ui'))
class LayoutCreator(Form, Base):
    def __init__(self, parent=qtfy.getMayaWindow()):
        super(LayoutCreator, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle(__title__)
        
        self.setServer()
        self.populateProjects()
        
        self.shots = {}

        self.projectBox.currentIndexChanged[str].connect(self.setProject)
        self.epBox.currentIndexChanged[str].connect(self.populateSequences)
        self.seqBox.currentIndexChanged[str].connect(self.populateShots)
        self.createButton.clicked.connect(self.create)
        self.addAssetsButton.clicked.connect(self.showAddAssetsWindow)
        
        self.shotBox = cui.MultiSelectComboBox(self, '--Select Shots--')
        self.shotBox.setToolTip('Select Shots to create camera for. To create all, leave all unselected')
        self.seqLayout.addWidget(self.shotBox)
        appUsageApp.updateDatabase('createLayout')
        
    def setServer(self):
        errors = utils.setServer()
        if errors:
            self.showMessage(msg=errors.keys()[0], icon=QMessageBox.Critical,
                             details=errors.values()[0])
        
    def populateProjects(self):
        self.projectBox.clear()
        self.projectBox.addItem('--Select Project--')
        projects, errors = utils.getProjects()
        if errors:
            self.showMessage(msg='Error occurred while retrieving the list of projects from TACTIC',
                             icon=QMessageBox.Critical,
                             details=qutil.dictionaryToDetails(errors))
        if projects:
            self.projectBox.addItems(projects)
            
    def setProject(self, project):
        self.epBox.clear()
        self.epBox.addItem('--Select Episode--')
        if project != '--Select Project--':
            errors = utils.setProject(project)
            if errors:
                self.showMessage(msg='Error occurred while setting the project on TACTIC',
                                 icon=QMessageBox.Critical,
                                 details=qutil.dictionaryToDetails(errors))
            self.populateEpisodes()
    
    def populateEpisodes(self):
        episodes, errors = utils.getEpisodes()
        if errors:
            self.showMessage(msg='Error occurred while retrieving the Episodes',
                             icon=QMessageBox.Critical,
                             details=qutil.dictionaryToDetails(errors))
        self.epBox.addItems(episodes)
    
    def populateSequences(self, ep):
        self.seqBox.clear()
        self.seqBox.addItem('--Select Sequence--')
        if ep != '--Select Episode--':
            seqs, errors = utils.getSequences(ep)
            if errors:
                self.showMessage(msg='Error occurred while retrieving the Sequences',
                                 icon=QMessageBox.Critical,
                                 details=qutil.dictionaryToDetails(errors))
            self.seqBox.addItems(seqs)
        
    def showAddAssetsWindow(self):
        import addAssets
        reload(addAssets)
        addAssets.Window(self).show()
        
    def populateShots(self, seq):
        self.shots.clear()
        self.shotBox.clearItems()
        if seq == '--Select Sequence--': return
        shots, errors = utils.getShots(seq)
        self.shots.update(shots)
        if errors:
            self.showMessage(msg='Error occurred while retrieving shots',
                             details=qutil.dictionaryToDetails(errors),
                             icon=QMessageBox.Critical)
        if not shots: return
        shots = [shot.split('_')[-1] for shot in shots.keys()]
        self.shotBox.addItems(shots)
        
    def showMessage(self, **kwargs):
        return cui.showMessage(self, __title__, **kwargs)
        
    def closeEvent(self, event):
        self.deleteLater()
        
    def appendStatus(self, msg):
        if 'Warning' in msg:
            msg = '<span style="color: orange">'+msg+'<span>'
        self.statusBox.append(msg)
        qApp.processEvents()
    
    def clearStatusBox(self):
        self.statusBox.clear()
        
    def getSeq(self):
        return self.seqBox.currentText()
    
    def getProject(self):
        pro = self.projectBox.currentText()
        if pro == '--Select Project--':
            pro = ''
        return pro
    
    def getEpisode(self):
        ep = self.epBox.currentText()
        if ep == '--Select Episode--':
            ep = ''
        return ep
    
    def getSequence(self):
        seq = self.seqBox.currentText()
        if seq == '--Select Sequence--':
            seq = ''
        return seq
        
    def create(self):
        self.clearStatusBox()
        self.appendStatus('Starting...')
        shots = self.shotBox.getSelectedItems()
        if not shots:
            shots = self.shotBox.getItems()
        if not shots:
            self.showMessage(msg='No Shots selected to create camera for',
                             icon=QMessageBox.Warning)
            return
        seq = self.getSeq()
        if seq == '--Select Sequence--': return
        self.appendStatus(str(len(shots)) +' shots found')
        self.appendStatus('Creating Cameras')
        for shot in shots:
            start, end = self.shots['_'.join([seq, shot])]
            self.appendStatus('Creating '+ shot + '  (Range: %s - %s)'%(start, end))
            utils.addCamera('_'.join([seq.split('_')[-1], shot]), start, end)
        self.appendStatus('DONE')