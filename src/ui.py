'''
Created on Jul 2, 2015

@author: qurban.ali
'''
from uiContainer import uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import cui
import os.path as osp
import qtify_maya_window as qtfy
import appUsageApp
import qutil
import utilities as utils
import traceback

reload(utils)
reload(qutil)
reload(cui)

root_path = osp.dirname(osp.dirname(__file__))
ui_path = osp.join(root_path, 'ui')
icon_path = osp.join(root_path, 'icon')
__title__ = 'Create Layout Scene'

Form, Base = uic.loadUiType(osp.join(ui_path, 'main_dockable.ui'))
class LayoutCreator(Form, Base):
    def __init__(self, parent=qtfy.getMayaWindow()):
        super(LayoutCreator, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle(__title__)
        borderColor = '#252525'
        self.setStyleSheet('QComboBox {\nborder-style: solid;\nborder-color: '+borderColor+';\nborder-width: 1px;\nborder-radius: 0px;\n}'+
                           'QPushButton {\nborder-style: solid;\nborder-color: '+borderColor+';\nborder-width: 1px;\nborder-radius: 0px;'+
                           '\nheight: 23;\nwidth: 75;\n}\nQPushButton:hover, QToolButton:hover {\nbackground-color: #303030;\n}'+
                           'QLineEdit {height: 23;\nborder-style: solid;\nborder-width: 1px;\nborder-color: '+borderColor+';\nborder-radius: 0px;\npadding-left: 15px;\npadding-bottom: 1px;}'+
                           'QToolButton {\nborder-style: solid;\nborder-color: '+borderColor+';\nborder-width: 1px;\nborder-radius: 0px;\n}')
        
        self.flowLayout = cui.FlowLayout()
        self.flowLayout.setSpacing(2)
        self.mainLayout.insertLayout(0, self.flowLayout)
        
        self.projectBox = QComboBox(); self.projectBox.addItem('--Select Project--')
        self.epBox = QComboBox(); self.epBox.addItem('--Select Episode--')
        self.seqBox = QComboBox(); self.seqBox.addItem('--Select Sequence--')
        self.projectBox.setMinimumSize(125, 25)
        self.epBox.setMinimumSize(125, 25)
        self.seqBox.setMinimumSize(125, 25)
        
        self.setServer()
        self.populateProjects()
        
        self.shots = {}
        self.shotItems = []
        self.assetPaths = {}
        self.collapsed = True
        
        self.flowLayout.addWidget(self.projectBox)
        self.flowLayout.addWidget(self.epBox)
        self.flowLayout.addWidget(self.seqBox)

        self.projectBox.currentIndexChanged[str].connect(self.setProject)
        self.epBox.currentIndexChanged[str].connect(self.populateSequences)
        self.seqBox.currentIndexChanged[str].connect(self.populateShots)
        self.createButton.clicked.connect(self.create)
        self.toggleCollapseButton.clicked.connect(self.toggleItems)
        self.searchBox.textChanged.connect(self.searchItems)
        
        self.shotBox = cui.MultiSelectComboBox(self, '--Shots--')
        self.shotBox.setStyleSheet('QPushButton{min-width: 100px;}')
        self.shotBox.selectionDone.connect(self.toggleShotPlanner)
        self.searchLayout.insertWidget(0, self.shotBox)
        parent.addDockWidget(0x1, self)
        self.toggleCollapseButton.setIcon(QIcon(osp.join(icon_path, 'ic_toggle_collapse')))
        search_ic_path = osp.join(icon_path, 'ic_search.png').replace('\\','/')
        style_sheet = ('\nbackground-image: url(%s);'+
                       '\nbackground-repeat: no-repeat;'+
                       '\nbackground-position: center left;')%search_ic_path
        style_sheet = self.searchBox.styleSheet() + style_sheet
        self.searchBox.setStyleSheet(style_sheet)
        self.splitter_2.setSizes([(self.height() * 30) / 100, (self.height() * 50) / 100])
        appUsageApp.updateDatabase('createLayout')
        
    def toggleItems(self):
        self.collapsed = not self.collapsed
        for item in self.shotItems:
            item.toggleCollapse(self.collapsed)
    
    def getSelectedAssets(self):
        return [item.text() for item in self.rigBox.selectedItems()]
        
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
        if project != '--Select Project--':
            errors = utils.setProject(project)
            if errors:
                self.showMessage(msg='Error occurred while setting the project on TACTIC',
                                 icon=QMessageBox.Critical,
                                 details=qutil.dictionaryToDetails(errors))
            self.populateEpisodes()
    
    def populateEpisodes(self):
        qApp.setOverrideCursor(Qt.WaitCursor)
        try:
            episodes, errors = utils.getEpisodes()
            if errors:
                self.showMessage(msg='Error occurred while retrieving the Episodes',
                                 icon=QMessageBox.Critical,
                                 details=qutil.dictionaryToDetails(errors))
            self.epBox.addItems(episodes)
        except Exception as ex:
            qApp.restoreOverrideCursor()
            self.showMessage(msg=str(ex), icon=QMessageBox.Critical)
        finally:
            qApp.restoreOverrideCursor()
    
    def populateSequences(self, ep):
        qApp.setOverrideCursor(Qt.WaitCursor)
        try:
            self.seqBox.clear()
            self.seqBox.addItem('--Select Sequence--')
            if ep != '--Select Episode--':
                seqs, errors = utils.getSequences(ep)
                if errors:
                    self.showMessage(msg='Error occurred while retrieving the Sequences',
                                     icon=QMessageBox.Critical,
                                     details=qutil.dictionaryToDetails(errors))
                self.seqBox.addItems(seqs)
        except Exception as ex:
            qApp.restoreOverrideCursor()
            self.showMessage(msg=str(ex), icon=QMessageBox.Critical)
        finally:
            qApp.restoreOverrideCursor()

    def populateShots(self, seq):
        errors = {}
        qApp.setOverrideCursor(Qt.WaitCursor)
        try:
            self.shots.clear()
            for item in self.shotItems:
                item.deleteLater()
            del self.shotItems[:]
            self.shotBox.clearItems()
            self.assetPaths.clear()
            self.rigBox.clear()
            self.modelBox.clear()
            if seq == '--Select Sequence--' or not seq: return
            shots, err = utils.getShots(seq)
            errors.update(self.populateSequenceAssets(seq))
            self.shots.update(shots)
            errors.update(self.populateShotPlanner())
            errors.update(err)
            if not shots: return
            shots = [shot.split('_')[-1] for shot in shots.keys()]
            self.shotBox.addItems(shots)
        except Exception as ex:
            traceback.print_exc()
            qApp.restoreOverrideCursor()
            self.showMessage(msg=str(ex), icon=QMessageBox.Critical)
        finally:
            qApp.restoreOverrideCursor()
        if errors:
            self.showMessage(msg='Error occurred while retrieving Assets for selected Sequence',
                             icon=QMessageBox.Critical,
                             details=qutil.dictionaryToDetails(errors))
        
    def populateSequenceAssets(self, seq):
        assets, errors = utils.getAssetsInSeq(self.getEpisode(), seq)
        if assets:
            for asset, values in assets.items():
                context, path = values
                if context == 'rig':
                    self.rigBox.addItem(asset)
                else:
                    self.modelBox.addItem(asset)
                self.assetPaths[asset] = path
        return errors
        
    def populateShotPlanner(self):
        shots = sorted(self.shots.keys())
        assets, errors = utils.getAssetsInShot(shots)
        for shot in shots:
            item = Item(self, title=shot.split('_')[-1], name=shot)
            if assets:
                item.addItems([asset['asset_code'] for asset in assets if asset['shot_code'] == shot])
            self.shotItems.append(item)
            self.itemsLayout.addWidget(item)
            item.hide()
        return errors
        
    def toggleShotPlanner(self, shots):
        for item in self.shotItems:
            if item.getTitle() in shots:
                item.show()
            else: item.hide()
            self.searchItems()
            
        
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
    
    def searchItems(self, text=''):
        if not text:
            text = self.searchBox.text()
        if text:
            for item in self.shotItems:
                if text.lower() in item.getTitle().lower() and item.getTitle() in self.shotBox.getSelectedItems():
                    item.show()
                else: item.hide()
        else:
            for item in self.shotItems:
                if item.getTitle() in self.shotBox.getSelectedItems():
                    item.show()
                else:
                    item.hide()
                
    def getModels(self):
        return [item.text() for item in self.modelBox.selectedItems()]
        
    def create(self):
        try:
            shots = self.shotBox.getSelectedItems()
            if not (shots or self.getModels()):
                self.showMessage(msg='No Shot selected to create camera for',
                                 icon=QMessageBox.Warning)
                return
            goodAssets = utils.CCounter()
            for item in [x for x in self.shotItems if x.getTitle() in shots]:
                assets = item.getItems()
                assets = [osp.normpath(self.assetPaths[asset]) for asset in assets] 
                if assets:
                    goodAssets.update_count(utils.CCounter(assets))
                else:
                    if not item.isEmpty():
                        self.showMessage(msg='%s selected but not Asset added'%item.getTitle(),
                                         icon=QMessageBox.Information)
                        return
            goodAssets.update([osp.normpath(self.assetPaths[asset]) for asset in self.getModels()])
            extraRefs = {}
            if goodAssets:
                goodAssets.subtract(utils.getRefsCount())
                flag = True
                for asset, num in goodAssets.items():
                    if num > 0:
                        flag = False
                        for _ in range(num):
                            qutil.addRef(asset)
                    elif num == 0:
                        pass
                    else:
                        flag = False
                        extraRefs[asset] = num * -1
                if flag:
                    self.showMessage(msg='No new updates found for the Assets',
                                     icon=QMessageBox.Information)
            if shots:
                seq = self.getSequence()
                try:
                    for cam in utils.getExistingCameraNames():
                        try:
                            shots.remove(cam)
                        except ValueError:
                            pass
                    for shot in shots:
                        start, end = self.shots['_'.join([seq, shot])]
                        utils.addCamera('_'.join([seq.split('_')[-1], shot]), start, end)
                except Exception as ex:
                    self.showMessage(msg=str(ex), icon=QMessageBox.Critical)
            if extraRefs:
                details = ''
                for key, val in extraRefs.items():
                    details += ': '.join([key, str(val)]) + '\n\n'
                self.showMessage(msg='There are some extra References in this scene',
                                 details=details, icon=QMessageBox.Information)
        except Exception as ex:
            self.showMessage(msg=str(ex), icon=QMessageBox.Critical)
            
            
Form2, Base2 = uic.loadUiType(osp.join(ui_path, 'shot_item.ui'))
class Item(Form2, Base2):
    def __init__(self, parent=None, title='', name=''):
        super(Item, self).__init__(parent)
        self.setupUi(self)
        self.parentWin = parent
        self.collapsed = False
        self.name = name
        self.assets = {}
        if title: self.setTitle(title)
        self.style = ('background-image: url(%s);\n'+
                      'background-repeat: no-repeat;\n'+
                      'background-position: center right')

        if not self.userAllowed():
            self.removeButton.setEnabled(False);
            self.addButton.setEnabled(False)
            self.emptyButton.setEnabled(False)
        
        self.iconLabel.setStyleSheet(self.style%osp.join(icon_path,
                                                         'ic_collapse.png').replace('\\', '/'))
        self.removeButton.setIcon(QIcon(osp.join(icon_path, 'ic_remove_char.png')))
        self.addButton.setIcon(QIcon(osp.join(icon_path, 'ic_add_char.png')))

        self.titleFrame.mouseReleaseEvent = self.collapse
        self.addButton.clicked.connect(self.addSelectedItems)
        self.removeButton.clicked.connect(self.removeItems)
        self.emptyButton.toggled.connect(self.checkAssets)
        
    def userAllowed(self):
        if qutil.getUsername() in ['qurban.ali', 'talha.ahmed', 'mohammad.bilal', 'umair.shahid', 'sarmad.mushtaq']:
            return True
        
    def checkAssets(self, val):
        if val and self.getItems():
            self.parentWin.showMessage(msg='Could not mark as Empty Shot, remove the Assets',
                                       icon=QMessageBox.Warning)
            self.emptyButton.setChecked(False)

    def collapse(self, event=None):
        if self.collapsed:
            self.listBox.show()
            self.collapsed = False
            path = osp.join(icon_path, 'ic_collapse.png')
        else:
            self.listBox.hide()
            self.collapsed = True
            path = osp.join(icon_path, 'ic_expand.png')
        path = path.replace('\\', '/')
        self.iconLabel.setStyleSheet(self.style%path)
        
    def isEmpty(self):
        return self.emptyButton.isChecked()

    def toggleCollapse(self, state):
        self.collapsed = state
        self.collapse()

    def getTitle(self):
        return str(self.nameLabel.text())
    
    def setTitle(self, title):
        self.nameLabel.setText(title)
        
    def updateNum(self):
        self.numLabel.setText('('+ str(self.listBox.count()) +')')
        
    def addAssetsToTactic(self, assets):
        flag = False
        qApp.setOverrideCursor(Qt.WaitCursor)
        try:
            errors = utils.addAssetsToShot(assets, self.name)
            if errors:
                self.parentWin.showMessage(msg='Error occurred while adding Assets to %s'%self.name,
                                           icon=QMessageBox.Critical,
                                           details=qutil.dictionaryToDetails(errors))
            else:
                flag = True
        except Exception as ex:
            qApp.restoreOverrideCursor()
            self.parentWin.showMessage(msg=str(ex), icon=QMessageBox.Critical)
        finally:
            qApp.restoreOverrideCursor()
        return flag
        
    def addItems(self, items):
        self.listBox.addItems(items)
        self.updateNum()
        
    def addSelectedItems(self):
        assets = self.parentWin.getSelectedAssets()
        if not assets: return
        if self.addAssetsToTactic(assets):
            self.listBox.addItems(assets)
        self.updateNum()
    
    def removeItems(self):
        qApp.setOverrideCursor(Qt.WaitCursor)
        try:
            assets = self.listBox.selectedItems()
            if assets:
                errors = utils.removeAssetFromShot([item.text() for item in assets], self.name)
                if errors:
                    self.parentWin.showMessage(msg='Error occurred while Removing Assets from %s'%self.name,
                                               icon=QMessageBox.Critical,
                                               details=qutil.dictionaryToDetails(errors))
                    return
                for item in assets:
                    self.listBox.takeItem(self.listBox.row(item))
        except Exception as ex:
            qApp.restoreOverrideCursor()
            self.parentWin.showMessage(msg=str(ex), icon=QMessageBox.Critical)
        finally:
            qApp.restoreOverrideCursor()
        self.updateNum()
            
    def getItems(self):
        items = []
        for i in range(self.listBox.count()):
            items.append(self.listBox.item(i).text())
        return items