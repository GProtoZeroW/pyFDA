# -*- coding: utf-8 -*-
"""
Widget for entering amplitude specifications

Author: Christian Münker
"""

# TODO: Check specs IIR / FIR A_PB <-> delta_PB

from __future__ import print_function, division, unicode_literals
import sys
import logging
logger = logging.getLogger(__name__)

from ..compat import QtGui, QtCore, QWidget
pyqtSignal, Qt, QEvent = QtCore.pyqtSignal, QtCore.Qt, QtCore.QEvent

import pyfda.filterbroker as fb
from pyfda.pyfda_lib import rt_label, lin2unit, unit2lin
from pyfda.pyfda_rc import params # FMT string for QLineEdit fields, e.g. '{:.3g}'
from pyfda.simpleeval import simple_eval

class AmplitudeSpecs(QWidget):
    """
    Build and update widget for entering the amplitude
    specifications like A_SB, A_PB etc.
    """

    sigUnitChanged = pyqtSignal() # emitted when amplitude unit has been changed
    sigSpecsChanged = pyqtSignal()

    def __init__(self, parent, title = "Amplitude Specs"):
        """
        Initialize
        """
        super(AmplitudeSpecs, self).__init__(parent)
        self.title = title

        self.qlabels = []   # list with references to QLabel widgets
        self.qlineedit = [] # list with references to QLineEdit widgets

        self.spec_edited = False # flag whether QLineEdit field has been edited
        self._construct_UI()

    def _construct_UI(self):
        """
        Construct User Interface
        """
        self.layVMain = QtGui.QVBoxLayout() # Widget vertical layout

        amp_units = ["dB", "V", "W"]

        bfont = QtGui.QFont()
        bfont.setBold(True)
#            bfont.setWeight(75)
        self.lblTitle = QtGui.QLabel(self) # field for widget title
        self.lblTitle.setText(str(self.title))
        self.lblTitle.setFont(bfont)
        self.lblTitle.setWordWrap(True)
        self.layVMain.addWidget(self.lblTitle)

        self.lblUnits = QtGui.QLabel(self)
        self.lblUnits.setText("Unit:")

        self.cmbUnitsA = QtGui.QComboBox(self)
        self.cmbUnitsA.addItems(amp_units)
        self.cmbUnitsA.setObjectName("cmbUnitsA")
        self.cmbUnitsA.setToolTip("Set unit for amplitude specifications:\n"
        "dB is attenuation (positive values)\nV and W are less than 1.")

        self.cmbUnitsA.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToContents)
        # fit size dynamically to largest element

        # find index for default unit from dictionary and set the unit
        amp_idx = self.cmbUnitsA.findData(fb.fil[0]['amp_specs_unit'])
        if amp_idx < 0:
            amp_idx = 0
        self.cmbUnitsA.setCurrentIndex(amp_idx) # initialize for dBsg

        self.layGSpecs = QtGui.QGridLayout() # sublayout for spec fields
        self.layGSpecs.addWidget(self.lblUnits,0,0)
        self.layGSpecs.addWidget(self.cmbUnitsA,0,1, Qt.AlignLeft)

        frmMain = QtGui.QFrame()
        frmMain.setFrameStyle(QtGui.QFrame.StyledPanel|QtGui.QFrame.Sunken)
        frmMain.setLayout(self.layGSpecs)

        self.layVMain.addWidget(frmMain)
        self.layVMain.setContentsMargins(1,1,1,1)

        self.setLayout(self.layVMain)

        # - Build a list from all entries in the fil_dict dictionary starting
        #   with "A" (= amplitude specifications of the current filter)
        # - Pass the list to setEntries which recreates the widget
        # ATTENTION: Entries need to be converted from QString to str for Py 2
        self.n_cur_labels = 0 # number of currently visible labels / qlineedits
        new_labels = [str(l) for l in fb.fil[0] if l[0] == 'A']
        self.update_UI(new_labels = new_labels)

        #----------------------------------------------------------------------
        # SIGNALS & SLOTs / EVENT MONITORING
        #----------------------------------------------------------------------
        self.cmbUnitsA.currentIndexChanged.connect(self._set_amp_unit)
        #       ^ this also triggers the initial load_entries
        # DYNAMIC EVENT MONITORING
        # Every time a field is edited, call self._store_entry and
        # self.load_entries. This is achieved by dynamically installing and
        # removing event filters when creating / deleting subwidgets.
        # The event filter monitors the focus of the input fields.

#------------------------------------------------------------------------------

    def eventFilter(self, source, event):
        """
        Filter all events generated by the QLineEdit widgets. Source and type
        of all events generated by monitored objects are passed to this eventFilter,
        evaluated and passed on to the next hierarchy level.

        - When a QLineEdit widget gains input focus (QEvent.FocusIn`), display
          the stored value from filter dict with full precision
        - When a key is pressed inside the text field, set the `spec_edited` flag
          to True.
        - When a QLineEdit widget loses input focus (QEvent.FocusOut`), store
          current value in linear format with full precision (only if
          `spec_edited`== True) and display the stored value in selected format
        """
        if isinstance(source, QtGui.QLineEdit): # could be extended for other widgets
            if event.type() == QEvent.FocusIn:
                self.spec_edited = False
                self.load_entries()
            elif event.type() == QEvent.KeyPress:
                self.spec_edited = True # entry has been changed
                key = event.key()
                if key in {QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter}: # store entry
                    self._store_entry(source)
                elif key == QtCore.Qt.Key_Escape: # revert changes
                    self.spec_edited = False                    
                    self.load_entries()

            elif event.type() == QEvent.FocusOut:
                self._store_entry(source)
        # Call base class method to continue normal event processing:
        return super(AmplitudeSpecs, self).eventFilter(source, event)


#-------------------------------------------------------------
    def update_UI(self, new_labels = []):
        """
        Set labels and get corresponding values from filter dictionary.
        When number of entries has changed, the layout of subwidget is rebuilt,
        using

        - `self.qlabels`, a list with references to existing QLabel widgets,
        - `new_labels`, a list of strings from the filter_dict for the current
          filter design
        - 'num_new_labels`, their number
        - `self.n_cur_labels`, the number of currently visible labels / qlineedit
          fields
        """

        num_new_labels = len(new_labels)
        if num_new_labels < self.n_cur_labels: # less new labels/qlineedit fields than before
            self._hide_entries(num_new_labels)

        elif num_new_labels > self.n_cur_labels: # more new labels, create / show new ones
            self._show_entries(num_new_labels)

        for i in range(num_new_labels):
            # Update ALL labels and corresponding values 
            self.qlabels[i].setText(rt_label(new_labels[i]))

            self.qlineedit[i].setText(str(fb.fil[0][new_labels[i]]))
            self.qlineedit[i].setObjectName(new_labels[i])  # update ID

        self.n_cur_labels = num_new_labels # update number of currently visible labels
        self.load_entries() # display rounded filter dict entries in selected unit


#------------------------------------------------------------------------------
    def load_entries(self):
        """
        Reload and reformat the amplitude textfields from filter dict when a new filter
        design algorithm is selected or when the user has changed the unit  (V / W / dB):

        - Reload amplitude entries from filter dictionary and convert to selected to reflect changed settings
          unit.
        - Update the lineedit fields, rounded to specified format.
        """
        unit = fb.fil[0]['amp_specs_unit']

        filt_type = fb.fil[0]['ft']

        for i in range(len(self.qlineedit)):
            amp_label = str(self.qlineedit[i].objectName())
            amp_value = lin2unit(fb.fil[0][amp_label], filt_type, amp_label, unit = unit)

            if not self.qlineedit[i].hasFocus():
                # widget has no focus, round the display
                self.qlineedit[i].setText(params['FMT'].format(amp_value))
            else:
                # widget has focus, show full precision
                self.qlineedit[i].setText(str(amp_value))

#------------------------------------------------------------------------------
    def _set_amp_unit(self, source):
        """
        Store unit for amplitude in filter dictionary, reload amplitude spec 
        entries via load_entries and fire a sigUnitChanged signal
        """
        fb.fil[0]['amp_specs_unit'] = str(self.cmbUnitsA.currentText())
        self.load_entries()

        self.sigUnitChanged.emit() # -> input_widgets

#------------------------------------------------------------------------------
    def _store_entry(self, source):
        """
        When the textfield of `source` has been edited (flag `self.spec_edited` =  True),
        transform the amplitude spec back to linear unit setting and store it
        in filter dict.
        This is triggered by `QEvent.focusOut`

        Spec entries are *always* stored in linear units; only the
        displayed values are adapted to the amplitude unit, not the dictionary!
        """
        if self.spec_edited:
            unit = str(self.cmbUnitsA.currentText())
            filt_type = fb.fil[0]['ft']
            amp_label = str(source.objectName())
            amp_value = simple_eval(source.text())
            fb.fil[0].update({amp_label:unit2lin(amp_value, filt_type, amp_label, unit)})
            self.sigSpecsChanged.emit() # -> input_specs
            self.spec_edited = False # reset flag
        self.load_entries()

#-------------------------------------------------------------
    def _hide_entries(self, num_new_labels):
        """
        Hide subwidgets so that only `num_new_labels` subwidgets are visible
        """
        for i in range (num_new_labels, len(self.qlabels)):
            self.qlabels[i].hide()
            self.qlineedit[i].hide()
# 
#------------------------------------------------------------------------
    def _show_entries(self, num_new_labels):
        """
        - check whether enough subwidgets (QLabel und QLineEdit) exist for the 
          the required number of `num_new_labels`: 
              - create new ones if required 
              - initialize them with dummy information
              - install eventFilter for new QLineEdit widgets so that the filter 
                  dict is updated automatically when a QLineEdit field has been 
                  edited.
        - if enough subwidgets exist already, make enough of them visible to
          show all spec fields
        """
        num_tot_labels = len(self.qlabels) # number of existing labels (vis. + invis.)

        if num_tot_labels < num_new_labels: # new widgets need to be generated
            for i in range(num_tot_labels, num_new_labels):                   
                self.qlabels.append(QtGui.QLabel(self))
                self.qlabels[i].setText(rt_label("dummy"))
    
                self.qlineedit.append(QtGui.QLineEdit(""))
                self.qlineedit[i].setObjectName("dummy")
                self.qlineedit[i].installEventFilter(self)  # filter events
    
                self.layGSpecs.addWidget(self.qlabels[i],(i+2),0)
                self.layGSpecs.addWidget(self.qlineedit[i],(i+2),1)

        else: # make the right number of widgets visible
            for i in range(self.n_cur_labels, num_new_labels):
                self.qlabels[i].show()
                self.qlineedit[i].show()

#==============================================================================
#         # start with Nmax + 1, last element Nmax + num +1
#         for i in range(Nmax+1, Nmax+num+1, 1):
#             self.qlabels.append(QtGui.QLabel(self))
#             self.qlabels[i].setText(rt_label("dummy"))
# 
#             self.qlineedit.append(QtGui.QLineEdit(""))
#             self.qlineedit[i].setObjectName("dummy")
#             self.qlineedit[i].installEventFilter(self)  # filter events
# 
#             self.layGSpecs.addWidget(self.qlabels[i],(i+2),0)
#             self.layGSpecs.addWidget(self.qlineedit[i],(i+2),1)
# 
#==============================================================================

#------------------------------------------------------------------------------

if __name__ == '__main__':

    app = QtGui.QApplication(sys.argv)
    mainw = AmplitudeSpecs(None)

    mainw.update_UI(new_labels = ['A_SB','A_SB2','A_PB','A_PB2'])
    mainw.update_UI(new_labels = ['A_PB','A_SB'])

    app.setActiveWindow(mainw)
    mainw.show()
    sys.exit(app.exec_())