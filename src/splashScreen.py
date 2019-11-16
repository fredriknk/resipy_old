""" splashScreen

"""
from PyQt5.QtWidgets import QSplashScreen, QApplication, QProgressBar
from PyQt5.QtGui import QPixmap, QIcon, QMovie
from PyQt5.QtCore import Qt
from zipfile import ZipFile, ZipInfo
from subprocess import Popen, call
import os, sys, shutil, platform, time 
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True) # for high dpi display
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


OS = platform.system()           

frozen = 'not'
if getattr(sys, 'frozen', False):
        # we are running in a bundle
        frozen = 'ever so'
        bundle_dir = sys._MEIPASS
else:
        # we are running in a normal Python environment
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
print( 'we are',frozen,'frozen')
print( 'bundle dir is', bundle_dir )

#workaround to deal with removing old _MEI folders on windows 
if OS == 'Windows':
    active_MEI = bundle_dir.split('\\')[-1]
    usrname = os.getlogin()
    temp_path = os.path.join('C:\\Users',usrname,'AppData\\Local\\Temp')
    files = sorted(os.listdir(temp_path))
    print('Checking for old _MEI directories in %s'%temp_path)
    for f in files:
        if f.find('_MEI')==0 and f!=active_MEI:
            print('removing %s ...'%f,end='')
            try:
                cmd = "RMDIR {:s} /q /s".format(os.path.join(temp_path,f))
                os.popen(cmd)
                print('done.')
            except:# (PermissionError, FileNotFoundError):
                print('ERROR')


""" PERMISSION ISSUE WITH ZIPFILE MODULE
https://stackoverflow.com/questions/39296101/python-zipfile-removes-execute-permissions-from-binaries
by default zipfile does not umpack any binary bit to say executable or not
Below is a way to do it
"""

class MySplashScreen(QSplashScreen):
    def __init__(self, animation, flags):
        # run event dispatching in another thread
        QSplashScreen.__init__(self, QPixmap(), flags)
        self.movie = QMovie(animation)
        self.movie.frameChanged.connect(self.onNextFrame)
        #self.connect(self.movie, SIGNAL('frameChanged(int)'), SLOT('onNextFrame()'))
        self.movie.start()

    def onNextFrame(self):
        pixmap = self.movie.currentPixmap()
        self.setPixmap(pixmap)
        self.setMask(pixmap.mask())
        
        
class MyZipFile(ZipFile):
    def extract(self, member, path=None, pwd=None):
        if not isinstance(member, ZipInfo):
            member = self.getinfo(member)

        if path is None:
            path = os.getcwd()

        ret_val = self._extract_member(member, path, pwd)
        attr = member.external_attr >> 16
        #os.chmod(ret_val, attr) # IMPORTANT this line needs to be commented otherwise we got the _MEIxxxxx issue
        # changing the permission of somes files makes them unremovable by the splascreen bootloader when the program finished
        # this leads to accumulation of _MEIxxxxx temporary files in C:\Users\User\AppData\Local\Temp\
        # this issue is windows specific, on Linux, the temporary folder in /tmp is removed even when we uncomment this line
        return ret_val


if __name__ == "__main__":

    app = QApplication(sys.argv)
    app.setStyle('Fusion')
#    app.setWindowIcon(QIcon(os.path.join(bundle_dir, 'logo.png')))

    splash_pix = QPixmap(os.path.join(bundle_dir, 'loadingLogo.png'))
    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
#    splash = MySplashScreen('chicken.gif', Qt.WindowStaysOnTopHint)
    splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
    splash.setEnabled(False)
    # splash = QSplashScreen(splash_pix)
    # adding progress bar
    progressBar = QProgressBar(splash)
#    progressBar.setMaximum(10)
    progressBar.setGeometry(100, splash_pix.height() - 50, splash_pix.width() - 200, 20)
#    progressBar.setGeometry(150, 320, 200, 18)
    # splash.setMask(splash_pix.mask())

    splash.show()
    splash.showMessage("Expanding app", Qt.AlignBottom | Qt.AlignCenter, Qt.black)
    app.processEvents()
    
#    initLoop = Qt.QEventLoop()
#    pool = Pool(processes=1)
#    pool.apply_async(longInitialization, [2], callback=lambda exitCode: initLoop.exit(exitCode))
#    initLoop.exec_()
    
#    app.processEvents()    
#    progressBar.setValue(1)
#    app.processEvents()
#    app.processEvents()
#    app.processEvents()
#    time.sleep(4)
##    progressBar.setValue(8)
#    app.processEvents()
#    time.sleep(4) # here insert the code to unzip the file
#    progressBar.setValue(10)
#    app.processEvents()
    
#    for i in range(1, 11):
#        progressBar.setValue(i)
#        t = time.time()
#        app.processEvents()
#    t = time.time()
#    while time.time() < t + 4:
#       app.processEvents()

    zf = MyZipFile(os.path.join(bundle_dir, 'ui.zip'),'r')
    extractDir = os.path.join(bundle_dir, 'ui')
    if os.path.exists(extractDir):
#        print('overwritting ResIPy dir')
        shutil.rmtree(extractDir)
    os.mkdir(extractDir)
    uncompress_size = sum((file.file_size for file in zf.infolist()))
    extracted_size = 0

    for file in zf.infolist():
        extracted_size += file.file_size
        percentage = extracted_size/uncompress_size*100
        progressBar.setValue(percentage)
        if percentage > 50 and percentage < 70:
            splash.showMessage("Copying temp files", Qt.AlignBottom | Qt.AlignCenter, Qt.black)
        if percentage >= 70 and percentage < 80:
            splash.showMessage("Checking files", Qt.AlignBottom | Qt.AlignCenter, Qt.black)
        if percentage >= 80 and percentage < 90:
            splash.showMessage("Loading PyQt", Qt.AlignBottom | Qt.AlignCenter, Qt.black)
        if percentage >= 90 and percentage < 98:
            splash.showMessage("Loading App", Qt.AlignBottom | Qt.AlignCenter, Qt.black)
        if percentage >= 98:
            splash.showMessage("Almost there!", Qt.AlignBottom | Qt.AlignCenter, Qt.black)
        app.processEvents()
        zf.extract(file, extractDir)
    zf.close()
    print('finished unzipping')
    
    splash.hide()
    splash.close()
    appDir = os.path.join(bundle_dir, 'ui', 'ui') # zip always putting a double dir ... don't know why
    print('Main app will be run in appDir = ', appDir)
    os.chdir(appDir)
#    os.system(['python3', 'ui.py']) # this work fine
    #if OS == 'Linux':
    print('running the main app')
    os.system(os.path.join(appDir, 'ResIPy.exe'))
    #else:
    #    Popen(os.path.join(appDir, 'ResIPy.exe'), shell=False, stdout=None, stdin=None)

    print('splashScreen is exiting')
    sys.exit(0) # send the SIGTERM signal -> works
#    sys.exit(app.exec_()) # doesn't work
    
""" NOTE
This approach increase significantly the size of the package from 150 to 210 MB
Another approach would be to load all modules in this script and just unzip the
sources and run `python ui.py`.
"""
