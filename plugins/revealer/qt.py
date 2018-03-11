'''
Revealer
secret backup solution

features:
    - Analog multi-factor backup solution
    - Safety - One time pad security
    - Redundancy - Trustless printing & distribution
    - Multiple wallets seeds can be encrypted for the same revealer*
    - Encrypt any secret you want for your revealer
    - Based on crypto by legendary cryptographers Naor and Shamir  

Tiago Romagnani Silveira, 2017

'''
import sys
import os
import qrcode
from functools import partial 

from electrum import mnemonic 
from electrum.plugins import BasePlugin, hook
from electrum_gui.qt.qrwindow import MONOSPACE_FONT
from electrum.i18n import _
from electrum_gui.qt.util import *
from electrum import util
from electrum_gui.qt.qrtextedit import ScanQRTextEdit

from .revealer import RevealerPlugin

from PyQt5.QtGui import *
from PyQt5.QtCore import *


class Plugin(RevealerPlugin):

    def __init__(self, parent, config, name):
        RevealerPlugin.__init__(self, parent, config, name)

    @hook
    def set_seed(self, seed, mpk):
        self.cseed = seed.upper()
        self.mpk = mpk

    @hook
    def show_cseed(self, parent):
        parent.addButton(':icons/revealer.png', partial(self.cypherseed_dialog, parent), _("Revealer secret backup utility"))    

    def requires_settings(self):
        return True

    def settings_widget(self, window):
        return EnterButton(_('Calibration'), partial(self.calibration_dialog, window))
    
    def calibration_dialog(self, window):
        d = WindowModalDialog(window, _("// revealer //"))
        
        d.setMinimumSize(100, 200)

        vbox = QVBoxLayout(d)
        self.calibration_h = self.config.get('calibration_h')
        self.calibration_v = self.config.get('calibration_v')
        cprint = QPushButton("Print calibration pdf")
        cprint.clicked.connect(self.demo)
        vbox.addWidget(cprint)
        
        vbox.addWidget(QLabel(_('Calibration values:')))
        grid = QGridLayout()
        vbox.addLayout(grid)
        grid.addWidget(QLabel('Horizontal'), 0, 0)
        horizontal = QLineEdit()
        horizontal.setText(str(self.calibration_h))
        grid.addWidget(horizontal, 0, 1)

        grid.addWidget(QLabel('Vertical'), 1, 0)
        vertical = QLineEdit()
        vertical.setText(str(self.calibration_v))
        grid.addWidget(vertical, 1, 1)

        vbox.addStretch()
        vbox.addLayout(Buttons(CloseButton(d), OkButton(d)))

        if not d.exec_():
            return

        calibration_h = str(horizontal.text())
        self.config.set_key('calibration_h', calibration_h)
        
        calibration_v = str(vertical.text())
        self.config.set_key('calibration_v', calibration_v)
    
    def print_cal(self):
        QDesktopServices.openUrl (QUrl.fromLocalFile(os.path.abspath('plugins/revealer/calibration.pdf')))

    def setup_dialog(self, window):
        self.update_wallet_name(window.parent().parent().wallet)
        
        self.d = WindowModalDialog(window, _("// revealer setup // "))
        self.d.setMinimumSize(500, 200)
        vbox = QVBoxLayout(self.d)
        
        bcreate = QPushButton("create a digital revealer")
        bcreate.clicked.connect(partial(self.make_digital, self.d))

        self.load_noise = ScanQRTextEdit()
        self.load_noise.setTabChangesFocus(True)
        self.load_noise.textChanged.connect(self.on_edit)
        self.load_noise.setMaximumHeight(32)
        
        vbox.addWidget(QLabel(_('')))
        vbox.addWidget(bcreate)
        vbox.addSpacing(14)
        vbox.addWidget(QLabel(_("OR ") + ''))
        vbox.addSpacing(3)
        vbox.addWidget(QLabel(_('')))
        vbox.addWidget(WWLabel(_("enter your Analog revealer code:")))
        vbox.addWidget(self.load_noise)
        vbox.addSpacing(10)
        vbox.addStretch()
        
        self.next_button = QPushButton(_("Next"), self.d)
        self.next_button.setDefault(True)
        self.next_button.setEnabled(False)

        vbox.addLayout(Buttons(self.next_button))        
        self.next_button.clicked.connect(self.d.close)

        return bool(self.d.exec_())
        if not self.d.exec_():
            return

    def get_noise(self):
        text = self.load_noise.text()
        return ''.join(text.split())

    def on_edit(self):
        s = self.get_noise()
        b = self.is_noise(s)
        if b:
            self.noise_seed = s
        self.next_button.setEnabled(b)        

    def is_noise(self, txt):
        if (len(txt) == 32 and int(txt, 16)):
            return True
        else:
            return False

    def make_digital(self, dialog):
        self.make_rawnoise()
        self.bdone(dialog)
        self.next_button.setEnabled(1)
        self.d.close()   
        #self.demo()
        return 
        
    def bloaded(self, dialog):
        dialog.show_message(_("seed backup file stored at "+self.base_dir))

    def bdone(self, dialog):
        dialog.show_message(_("digital revealer file saved at "+self.base_name+'_revealer.png '))
        
    def t(self):
        self.txt = self.text.text()
        self.seed_img(is_seed = False)

        
    def cypherseed_dialog(self, window):
        self.update_wallet_name(window.parent().parent().wallet)

        self.setup_dialog(window)
        #self.seed_img()
        
        d = WindowModalDialog(window, _("// revealer // "))
        d.setMinimumSize(100,200)
        
        self.vbox = QVBoxLayout(d)
        self.vbox.addSpacing(10)
        grid = QGridLayout()
        self.vbox.addLayout(grid)

        cprint = QPushButton("create encrypted seed pdf")
        cprint.clicked.connect(partial (self.seed_img, True))
        self.vbox.addWidget(cprint)
        self.vbox.addSpacing(14)

        self.text = ScanQRTextEdit()
        self.text.setTabChangesFocus(True)
        #self.text.textChanged.connect(self.chk_size)
        self.text.setMaximumHeight(160)
        self.vbox.addWidget(self.text)

        ctext = QPushButton("encrypt custom text")
        ctext.clicked.connect(self.t)
        self.vbox.addSpacing(21)
        self.vbox.addWidget(ctext)

        calibrate = QPushButton("calibrate printer")
        calibrate.clicked.connect(partial(self.calibration_dialog, window))
        self.vbox.addWidget(calibrate)
        
        self.vbox.addLayout(Buttons(CloseButton(d)))
        
        
        return bool(d.exec_())
        if not d.exec_():
            return


        '''
        show cypherseed image and allow digital decryption with file / code input

        #advanced options for paperwallet generation:
            Master public key: (as secret?)
            Wallet_name:
            Date:
            Balance:
            Notes:
            creta PDF with random seeds? how many?
                        
        '''
        
