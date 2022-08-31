import os
from threading import Thread
# from multiprocessing import Process
from tkinter import Menu, Tk, Button, Label
from subprocess import run


class MainEntrance:
    def __init__(self, root):
        self.root = root
        # Create a menu item, similar to a navigation bar
        menubar = Menu(self.root)
        menu1 = Menu(self.root)
        for item in ['exit']:
            # If the menu is a top-level menu item, it adds a drop-down menu item.
            menu1.add_command(label=item, command=self.root.destroy)

        menu3 = Menu(self.root)
        for item in ["copyRight"]:
            menu3.add_command(label=item, command=self.copyRight)

        menu2 = Menu(self.root)
        menuItems = [self.merge, self.slidingcrop, self.mosaic]
        for i, item in enumerate(["Merge", 'SlidingCrop', "Mosaic"]):
            menu2.add_command(label=item, command=menuItems[i])
            # Add a separator bar to menu2 using the add_command method
            menu2.add_separator()
        sub_menu = Menu(menu2)
        menu2.add_cascade(label="Conversion", menu=sub_menu)
        commandItems = [self.raster_to_vector, self.vector_to_raster, self.lingRing_to_surface,
                        self.surface_to_lineRing]
        # Adding menu items to the sub_menu using a loop
        for index, menuItem in enumerate(
                ['raster to vector', 'vector to raster', 'lineRing to surface', 'surface to lineRing']):
            sub_menu.add_command(label=menuItem, command=commandItems[index])

        # An important property of the function add_cascade is the menu property, which specifies which menu to
        # cascade to the menu item；
        # The label property, which specifies the name of the menu
        menubar.add_cascade(label="File", menu=menu1)
        menubar.add_cascade(label="Tools", menu=menu2)
        menubar.add_cascade(label="About", menu=menu3)
        # Finally,using the menu property of the mainFrame to specify which one we use as its top-level menu
        self.root['menu'] = menubar
        # self.root.config(menu = menubar)

        # To Create the new button
        functionLabel = ['surfaceRupture']
        self.function = [self.customCrop, self.roughSeg_fineExt, self.editVector, self.widthAndstrike]
        i = 0
        for name in ['CustomCrop', 'RoughSeg_FineExt', 'EditVector', 'WidthAndStrike']:
            if i % 4 == 0:
                Label(self.root, text=(functionLabel[i // 4] + ':')).grid(row=i // 4, column=0)
            myfunc = self.function[i]
            Button(self.root, text=name, command=myfunc).grid(row=i // 4, column=i % 4 + 1)
            i += 1

        col_count, row_count = mainFrame.grid_size()
        for col in range(col_count):
            mainFrame.grid_columnconfigure(col, minsize=100)

        for row in range(row_count):
            mainFrame.grid_rowconfigure(row, minsize=40)
        self.root.geometry("520x{0}+700+{1}".format(40 * row_count, 540 - 50 * row_count))

    def raster_to_vector(self):
        def raster2vector():
            mainDir = r".\Lib\raster2vector.py"
            if os.path.exists(mainDir):
                run(['python', mainDir], shell=True)

        # Create a thread to execute the programs
        t = Thread(target=raster2vector)
        # t = multiprocessing.Process(target = func, args = args)
        # guard the thread
        t.daemon = False
        # start the thread
        t.start()

    def vector_to_raster(self):
        def vector2raster():
            mainDir = r".\Lib\vector2raster.py"
            if os.path.exists(mainDir):
                run(['python', mainDir], shell=True)

        # Create a thread to execute the programs
        t = Thread(target=vector2raster)
        # t = multiprocessing.Process(target = func, args = args)
        # guard the thread
        t.daemon = False
        # start the thread
        t.start()

    def lingRing_to_surface(self):
        def lingRing2surface():
            mainDir = r".\Lib\lineRing2surface.py"
            if os.path.exists(mainDir):
                run(['python', mainDir], shell=True)

        # Create a thread to execute the programs
        t = Thread(target=lingRing2surface)
        # t = multiprocessing.Process(target = func, args = args)
        # guard the thread
        t.daemon = False
        # start the thread
        t.start()

    def surface_to_lineRing(self):
        def surface2lineRing():
            mainDir = r".\Lib\surface2lineRing.py"
            if os.path.exists(mainDir):
                run(['python', mainDir], shell=True)

        # Create a thread to execute the programs
        t = Thread(target=surface2lineRing)
        # t = multiprocessing.Process(target = func, args = args)
        # guard the thread
        t.daemon = False
        # start the thread
        t.start()

    def merge(self):
        def mergeVector():
            mainDir = r".\Lib\Merge.py"
            if os.path.exists(mainDir):
                run(['python', mainDir], shell=True)

        # Create a thread to execute the programs
        t = Thread(target=mergeVector)
        # t = multiprocessing.Process(target = func, args = args)
        # guard the thread
        t.daemon = False
        # start the thread
        t.start()

    def slidingcrop(self):
        def cropImage():
            mainDir = r".\Lib\SlidingCrop.py"
            if os.path.exists(mainDir):
                run(['python', mainDir], shell=True)

        # Create a thread to execute the programs
        t = Thread(target=cropImage)
        # t = multiprocessing.Process(target = func, args = args)
        # guard the thread
        t.daemon = False
        # start the thread
        t.start()

    def mosaic(self):
        def mosaicImage():
            mainDir = r".\Lib\Mosaic.py"
            if os.path.exists(mainDir):
                run(['python', mainDir], shell=True)

        # Create a thread to execute the programs
        t = Thread(target=mosaicImage)
        # t = multiprocessing.Process(target = func, args = args)
        # guard the thread
        t.daemon = False
        # start the thread
        t.start()

    def copyRight(self):
        def myGIS():
            width = 780
            height = 50
            size_align = '%dx%d+%d+%d' % (
                width, height, (self.root.winfo_screenwidth() - width) / 2,
                (self.root.winfo_screenheight() - height) / 2)
            frame = Tk()
            frame.wm_title("CopyRight")
            frame.geometry(size_align)
            Label(frame,
                  text="EASRAPP is an open-source application for extracting and analysing surface ruptures by a postgradute named Li Dongchen ").pack()
            Label(frame, text="from NATIONAL INSTITUTE OF NATURAL HAZARDS, Ministry of Emergency Management of China").pack()
            frame.mainloop()

        # Create a thread to execute the programs
        t = Thread(target=myGIS)
        # t = multiprocessing.Process(target = func, args = args)
        # guard the thread
        t.daemon = False
        # start the thread
        t.start()

    def customCrop(self):
        def custom():
            mainDir = r".\Lib\CustomCrop.py"
            if os.path.exists(mainDir):
                run(['python', mainDir], shell=True)

        # Create a thread to execute the programs
        t = Thread(target=custom)
        # t = multiprocessing.Process(target = func, args = args)
        # guard the thread
        t.daemon = False
        # start the thread
        t.start()

    def roughSeg_fineExt(self):
        def roughSeg():
            mainDir = r".\Lib\RoughSeg_FineExt.py"
            if os.path.exists(mainDir):
                run(['python', mainDir], shell=True)

        t = Thread(target=roughSeg)
        # t = multiprocessing.Process(target = func, args = args)
        # guard the thread
        t.daemon = False
        # start the thread
        t.start()

    def editVector(self):
        def edit():
            mainDir = r".\Lib\EditVector.py"
            if os.path.exists(mainDir):
                run(['python', mainDir], shell=True)

        t = Thread(target=edit)
        # t = multiprocessing.Process(target = func, args = args)
        # guard the thread
        t.daemon = False
        # start the thread
        t.start()

    def widthAndstrike(self):
        def widthStrike():
            mainDir = r".\Lib\WidthAndStrike.py"
            if os.path.exists(mainDir):
                run(['python', mainDir], shell=True)

        t = Thread(target=widthStrike)
        # guard the thread
        t.daemon = False
        # start the thread
        t.start()


if __name__ == '__main__':
    mainFrame = Tk()
    mainFrame.wm_title("EASRAPP")
    main = MainEntrance(mainFrame)
    mainFrame.mainloop()
