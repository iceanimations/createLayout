'''
Created on Jul 2, 2015

@author: qurban.ali
'''
from uiContainer import uic
from PyQt4.QtGui import QMessageBox, QListWidget, QAbstractItemView, QListWidgetItem, qApp
from PyQt4.QtCore import QPropertyAnimation, QEasingCurve, QRect, Qt
import cui
import os.path as osp
import qtify_maya_window as qtfy
import appUsageApp
import qutil
import utilities as utils
from pprint import pprint

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
        
        self.animation = QPropertyAnimation(self, 'geometry')
        self.animation.setEasingCurve(QEasingCurve.Linear)
        self.animation.setDuration(500)
        
        self.setServer()
        self.populateProjects()
        self.tabWidget.hide()
        self.progressBar.hide()
        self.addButton.hide()
        self.removeButton.hide()
        
        self.shots = {}

        self.projectBox.currentIndexChanged[str].connect(self.setProject)
        self.epBox.currentIndexChanged[str].connect(self.populateSequences)
        self.seqBox.currentIndexChanged[str].connect(self.populateShots)
        self.createButton.clicked.connect(self.create)
        self.addAssetsButton.clicked.connect(self.showAddAssetsWindow)
        self.shotPlannerButton.clicked.connect(self.showShotPlanner)
        self.addButton.clicked.connect(self.addShotAssets)
        self.removeButton.clicked.connect(self.removeShotAssets)
        
        self.shotBox = cui.MultiSelectComboBox(self, '--Select Shots--')
        self.shotBox.setMinimumWidth(75)
        self.shotBox.setToolTip('Select Shots to create camera for. To create all, leave all unselected')
        self.btnsLayout.insertWidget(2, self.shotBox)
        self.tabWidget.removeTab(0)
        self.tabWidget.removeTab(0)
        appUsageApp.updateDatabase('createLayout')
        
    def setStatus(self, msg):
        self.statusLabel.setText(msg)
        qApp.processEvents()
    
    def addShotAssets(self):
        #TODO: add security
        if not utils.isSelection():
            self.showMessage(msg='No object found in the selection',
                             icon=QMessageBox.Information)
            return
        self.setStatus('Creating names for selected Assets')
        assets = utils.getSelectedAssets()
        if not assets:
            self.showMessage(msg='Could not create the names for the selected assets',
                             icon=QMessageBox.Critical)
            self.setStatus('')
            return
        shotCode = '_'.join([self.getEpisode(), utils.getCameraName()]).upper()
        shotName = shotCode.split('_')[-1]
        tab = None
        self.setStatus('Finding the Shot for the current camera')
        for i in range(self.tabWidget.count()):
            if self.tabWidget.tabText(i) == shotName:
                self.tabWidget.setCurrentIndex(i)
                tab = self.tabWidget.currentWidget()
                break
        if tab is None:
            self.showMessage(msg='Could not find the Shot for current camera',
                             icon=QMessageBox.Critical)
            self.setStatus('')
            return
        self.setStatus('Finding Assets for selected Sequence')
        seq = self.getSequence()
        if not seq:
            self.showMessage(msg='No Sequence selected to retrieve the assets for',
                             icon=QMessageBox.Warning)
            self.setStatus('')
            return
        seqAssets, errors = utils.getAssetsInSeq(seq)
        if errors:
            self.showMessage(msg='Error occurred while retrieving assets',
                             icon=QMessageBox.Critical,
                             details=qutil.dictionaryToDetails(errors))
        if not seqAssets:
            self.showMessage(msg='Could not find the Assets for selected Sequence on TACTIC',
                             icon=QMessageBox.Critical)
            self.setStatus('')
            return
        if assets:
            self.setStatus('Adding Assets to the Shot')
            assets = list(assets)
            if not set(assets).issubset(set(seqAssets)):
                details = '%s doesn\'t contain the following selected Assets\n'%seq
                for ast in set(assets).difference(set(seqAssets)):
                    details += '\n%s'%ast
                btn = self.showMessage(msg='Not all selected Assets found in the selected Sequence',
                                       ques='Add only the Assets matching to the Assets in the selected Sequence?',
                                       icon=QMessageBox.Warning,
                                       details=details,
                                       btns=QMessageBox.Yes|QMessageBox.No)
                if btn == QMessageBox.Yes:
                    assets = set(assets).intersection(set(seqAssets))
                else:
                    self.setStatus('')
                    return
            errors = utils.addAssetsToShot(assets, shotCode)
            if errors:
                self.showMessage(msg='Error occurred while adding Assets to TACTIC',
                                 icon=QMessageBox.Critical,
                                 details=qutil.dictionaryToDetails(errors))
                self.setStatus('')
                return
            tab.clearSelection()
            for asset in assets:
                item = QListWidgetItem(asset, tab)
                item.setSelected(True)
        self.setStatus('')
    
    def removeShotAssets(self):
        print self.tabWidget.currentWidget()
        
    def showShotPlanner(self):
        pos = self.pos()
        height = self.height()
        if self.shotPlannerButton.isChecked() and self.getSequence():
            if height < 451:
                self.animation.setStartValue(QRect(pos.x()+8, pos.y()+30, self.width(), height))
                self.animation.setEndValue(QRect(pos.x()+8, pos.y()+30, self.width(), 450))
                self.animation.start()
            self.tabWidget.show()
            self.addButton.show()
            #self.removeButton.show()
            self.populateShotPlanner()
        else:
            self.tabWidget.hide()
            self.addButton.hide()
            self.removeButton.hide()
            if self.height > 122:
                self.animation.setStartValue(QRect(pos.x()+8, pos.y()+30, self.width(), height))
                self.animation.setEndValue(QRect(pos.x()+8, pos.y()+30, self.width(), 100))
                self.animation.start()
            
    def populateShotPlanner(self):
        try:
            self.tabWidget.clear()
            shots = ['_'.join([self.getSequence(), shot]) for shot in self.shotBox.getItems()]
            self.setStatus('Retrieving assets from TACTIC')
            assets, errors = utils.getAssetsInShot(shots)
            if errors:
                self.showMessage(msg='Error occurred while retrieving assets for shots',
                                 icon=QMessageBox.Critical,
                                 details=qutil.dictionaryToDetails(errors))
            shots = [shot.split('_')[-1] for shot in shots]
            self.progressBar.setMaximum(len(shots))
            self.progressBar.show()
            for i, shot in enumerate(shots):
                listWidget = QListWidget(self)
                listWidget.setFocusPolicy(Qt.NoFocus)
                listWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
                if assets:
                    listWidget.addItems([asset.get('asset_code') for asset in assets if asset.get('shot_code').endswith(shot)])
                self.tabWidget.addTab(listWidget, shot)
                self.progressBar.setValue(i+1)
        except Exception as ex:
            self.showMessage(msg=str(ex), icon=QMessageBox.Critical)
        finally:
            self.setStatus('')
            self.progressBar.hide()
        
    def setServer(self):
        self.server, errors = utils.setServer()
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
        self.showShotPlanner()
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
        self.showShotPlanner()
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
        addAssets.Window(self, self.server).show()
        
    def populateShots(self, seq):
        self.shots.clear()
        self.shotBox.clearItems()
        if seq == '--Select Sequence--': self.showShotPlanner(); return
        shots, errors = utils.getShots(seq)
        self.shots.update(shots)
        if errors:
            self.showMessage(msg='Error occurred while retrieving shots',
                             details=qutil.dictionaryToDetails(errors),
                             icon=QMessageBox.Critical)
        if not shots: return
        shots = [shot.split('_')[-1] for shot in shots.keys()]
        self.shotBox.addItems(shots)
        self.showShotPlanner()
        
    def showMessage(self, **kwargs):
        return cui.showMessage(self, __title__, **kwargs)
        
    def closeEvent(self, event):
        self.deleteLater()
        
    def getSequence(self):
        seq = self.seqBox.currentText()
        if seq == '--Select Sequence--':
            seq = ''
        return seq
    
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
        
    def create(self):
        shots = self.shotBox.getSelectedItems()
        if not shots:
            shots = self.shotBox.getItems()
        if not shots:
            self.showMessage(msg='No Shots selected to create camera for',
                             icon=QMessageBox.Warning)
            return
        seq = self.getSequence()
        if not seq: return
        try:
            self.progressBar.setMaximum(len(shots))
            self.progressBar.show()
            for i, shot in enumerate(shots):
                start, end = self.shots['_'.join([seq, shot])]
                self.progressBar.setValue(i+1)
        except Exception as ex:
            self.showMessage(msg=str(ex), icon=QMessageBox.Critical)
        finally:
            self.progressBar.hide()
            utils.addCamera('_'.join([seq.split('_')[-1], shot]), start, end)