import sys
import cv2
from os import path
import numpy as np
from PyQt5 import uic
from PyQt5.QtGui import QImage, QPixmap, QImageReader
from PyQt5.QtWidgets import QMainWindow, QPushButton, QApplication, QLabel, QFileDialog, QGridLayout, QStatusBar, QInputDialog, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QDir, pyqtSlot


class UI(QMainWindow):
    def __init__(self):
        super(UI, self).__init__()
        uic.loadUi(path.join(path.dirname(__file__), 'gui.ui'), self)

        self.captureBtn = self.findChild(QPushButton, 'captureBtn')
        self.browseBtn = self.findChild(QPushButton, 'browseBtn')
        self.resetBtn = self.findChild(QPushButton, 'resetBtn')
        self.changeStreamBtn = self.findChild(QPushButton, 'changeStreamBtn')

        self.imageArea = self.findChild(QLabel, 'imageArea')
        self.outputBox = self.findChild(QGridLayout, 'outputBox')
        self.statusBar = self.findChild(QStatusBar, 'statusBar')
        self.cameraFeed = CameraFeed()

        self.handlers()
        self.currentImage = self.createBlankImage()

    def handlers(self):
        self.imageArea.mousePressEvent = self.onMouseClickOnImageArea
        self.cameraFeed.feedSignal.connect(self.imageUpdateSlot)
        self.cameraFeed.errorSignal.connect(
            lambda s: QMessageBox.about(self, "Error Occured", s))

        self.cameraFeed.start()

        self.captureBtn.clicked.connect(self.triggerCapture)
        self.changeStreamBtn.clicked.connect(self.changeStream)

        self.resetBtn.clicked.connect(self.reset)

        self.browseBtn.clicked.connect(self.uploadImagefromDisk)

    def imageUpdateSlot(self, image):
        if(self.cameraFeed.threadActive):
            # image = cv2.flip(image, 1)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            processedImage = self.processImage(image)
            self.currentImage = processedImage
            self.setImageArea(processedImage)

    @ pyqtSlot()
    def reset(self):
        self.resetBtn.setEnabled(False)
        self.currentImage = self.createBlankImage()
        if not self.cameraFeed.threadActive:
            self.cameraFeed.start()
        self.resetBtn.setEnabled(True)

    @ pyqtSlot()
    def changeStream(self):
        text, _ = QInputDialog.getText(self, 'Set Camera Stream/Index',
                                       'Enter Valid Url/Integer')
        if text:
            if(text.isdecimal()):
                text = int(text)
            self.cameraFeed.setCamIndex(text)

    @ pyqtSlot()
    def triggerCapture(self):
        self.cameraFeed.stop()
        self.captureImage(self.currentImage)

    def captureImage(self, image):
        self.setEnabled(False)
        self.currentImage = image
        self.imageArea.setText('Processing Image...')
        self.imageProcessorThread = SampleThread(
            self.processImageAfterCapture, image)

        def threadOnOutput(image):
            self.setImageArea(image)
            self.imageProcessorThread.stop()
            self.setEnabled(True)
        self.imageProcessorThread.output.connect(threadOnOutput)
        self.imageProcessorThread.start()

    def setImageArea(self, image):
        self.imageArea.setPixmap(self.convertToQPixmap(image))

    def uploadImagefromDisk(self):
        self.browseBtn.setEnabled(False)
        supportedFormats = QImageReader.supportedImageFormats()
        imageFilters = "Images ({})".format(
            " ".join(["*.{}".format(fo.data().decode()) for fo in supportedFormats]))
        fileName, _ = QFileDialog.getOpenFileName(
            self, 'Upload An Image', QDir.homePath(), imageFilters)
        if fileName:
            self.cameraFeed.stop()
            image = cv2.imread(fileName)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            self.captureImage(self.processImage(image))

        self.browseBtn.setEnabled(True)

    def convertToQPixmap(self, image):
        qtFormatConvertor = QImage(
            image.data, image.shape[1], image.shape[0], QImage.Format_RGB888)
        qtImage = qtFormatConvertor.scaled(
            640, 480, Qt.IgnoreAspectRatio)
        return QPixmap.fromImage(qtImage)

    def getImage(self):
        return self.currentImage

    def processImage(self, image):
        # Process the image in opencv before showing it in the imageArea (Use for non time consuming operations only)
        return image

    def processImageAfterCapture(self, image):
        # Process the image in opencv after capturing and show it in the imageArea
        return image

    def onMouseClickOnImageArea(self, event):
        # Event After mouse clicked in imageArea
        pass

    def createBlankImage(self):
        return np.zeros((640, 480, 3), np.uint8)


class SampleThread(QThread):
    # Sample Thread to perform time consuming operations
    output = pyqtSignal(object)

    def __init__(self, callback, *args, **kwargs):
        super(SampleThread, self).__init__()
        self.args = args
        self.cb = callback
        self.setObjectName("Sample Thread")

    def run(self):
        o = self.cb(*self.args)
        self.output.emit(o)

    def stop(self):
        self.quit()


class CameraFeed(QThread):
    feedSignal = pyqtSignal(np.ndarray)
    errorSignal = pyqtSignal(str)

    def __init__(self, index=0):
        super(CameraFeed, self).__init__()
        self.index = index
        self.setObjectName("Camera Thread")
        self.capture = cv2.VideoCapture(self.index)

    def run(self):
        self.threadActive = True

        while self.threadActive:
            if self.capture and self.capture.isOpened():
                ret, frame = self.capture.read()
                if ret:
                    self.feedSignal.emit(frame)

    def stop(self):
        self.threadActive = False
        self.quit()

    def setCamIndex(self, index):
        if(index == self.index):
            return
        cap = cv2.VideoCapture(index)
        if not cap or not cap.isOpened():
            self.errorSignal.emit(
                f'Error: unable to open video source: {index}')
            return
        self.capture = cap
        self.index = index


def main(args):
    app = QApplication(args)
    root = UI()
    root.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    sys.exit(main(sys.argv))
