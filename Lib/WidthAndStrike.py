# -*- coding: utf-8 -*-
from osgeo.ogr import GetDriverByName as ogrGetDriverByName
from scipy.spatial import ConvexHull
from tkinter import ttk, filedialog, StringVar, Button, Label, Entry, Scrollbar, TclError, Canvas, Tk, messagebox
from math import sqrt, degrees, atan
from matplotlib.pyplot import figure, show, get_current_fig_manager, switch_backend, subplots_adjust, axes
from matplotlib.widgets import Slider as matSlider
from numpy import array, append, cross, arange, histogram, concatenate, deg2rad, linspace
from PIL import ImageGrab
from scipy.interpolate import make_interp_spline


class CreateScrollbar(Scrollbar):
    # set(first, last):The range of first and last values is decimal [0,1], and the range from first to
    # last specifies the range of visual content of the scrollable control bound to the scrollbar.
    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
            Scrollbar.set(self, lo, hi)

    def pack(self, **kw):
        raise TclError('The container cannot use pack with the widget ' + self.__class__.name)

    def place(self, **kw):
        raise TclError('The container cannot use place with the widget ' + self.__class__.name)


class InputImage:
    def __init__(self, root):
        width = 300
        height = 200
        size_align = '%dx%d+%d+%d' % (
            width, height, (root.winfo_screenwidth() - width) / 2, (root.winfo_screenheight() - height) / 2)
        self.root = root
        self.root.geometry(size_align)
        self.root.title('Input surface rupture vector file...')
        # Creates the Label
        Label(self.root, text="shp_path:").place(x=27, y=75)
        self.e_text = StringVar()
        Entry(self.root, width=20, textvariable=self.e_text).place(x=107, y=75)

        Button(self.root, text="...", command=self.select_vector_path).place(x=257, y=71)
        Button(self.root, text="Ok", command=self.output, activebackground="pink", activeforeground="blue").place(
            x=40, y=150)
        Button(self.root, text="Cancel", command=self.root.destroy, activebackground="pink",
               activeforeground="blue").place(x=230, y=150)

    def select_vector_path(self):
        image_path = filedialog.askopenfilename(title='Select the vector file of surface rupture...', initialdir=None,
                                                filetypes=[(
                                                    "vector", ".shp"), ('All Files', ' *')], defaultextension='.shp')
        self.e_text.set(str(image_path))

    def output(self):
        global path
        path = self.e_text.get()
        self.root.destroy()


class Rupture(ttk.Frame):
    """ Display and zoom image """

    def __init__(self, root, path):
        super().__init__()
        """ Initialize the ImageFrame """
        self.root = root
        self.path = path
        self.screenShot = False
        self.old_x, self.old_y, self.new_x, self.new_y = None, None, None, None
        self.textid = []
        self.fault_pts = []
        self.convexIndex_add = []
        self.index_mixture = []
        self.id_pts = None
        self.create = False
        self.drawfault = False
        self.length, self.width, self.angle = [], [], []
        self.scale = 1.0
        self.delta = 1.1  # zoom magnitude
        self.grid(row=0, column=0, sticky='nswe')
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        # Vertical and horizontal scrollbars for canvas
        hbar = CreateScrollbar(self, orient='horizontal')
        vbar = CreateScrollbar(self, orient='vertical')
        hbar.grid(row=1, column=0, sticky='we')
        vbar.grid(row=0, column=1, sticky='ns')
        # Create canvas and bind it with scrollbars. Public for outer classes
        self.canvas = Canvas(self, highlightthickness=0, xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        self.canvas.grid(row=0, column=0, sticky='nswe')

        Label(self.root,
              text='The zonal interval of the surface rupture zone along the fault direction(Unit:meter) : ').grid(
            row=2, sticky='w')
        self.e_interval = StringVar()
        Entry(self.root, width=20, textvariable=self.e_interval).grid(row=2)

        Label(self.root,
              text=('The index position to be inserted of the point to be added in the convex contour;Please ' +
                    'enter the serial number in the text box on the right: ')).grid(
            row=3, sticky='w')
        self.e_text = StringVar()
        Entry(self.root, width=40, textvariable=self.e_text).grid(row=3)
        Button(self, text="create", command=self.createImage, activebackground="pink", activeforeground="blue").grid(
            row=4, sticky='w')
        Button(self, text="Cancel", command=self.root.destroy, activebackground="pink",
               activeforeground="blue").grid(
            row=4, sticky='e')

        # Create a message prompt label
        self.text = StringVar()
        Label(self.root, textvariable=self.text, fg='green', font=("黑体", 20)).grid(row=5, sticky='w')

        self.update()
        self.text.set("Prompt: No hint at present!")
        self.translateh = self.winfo_screenheight()
        self.translatew = self.winfo_screenwidth()
        coors, coors_draw = [], []
        shp_driver = ogrGetDriverByName('Esri Shapefile')
        # The second argument is 0 (read-only), 1 (writable), default 0 (read-only)
        datasrc = shp_driver.Open(self.path)
        if datasrc == "None":
            self.text.set("Failed to open the vector file!")
        layer = datasrc.GetLayer(0)  # obtain layer
        x_left, x_right, y_bottom, y_up = layer.GetExtent()
        # Loop through all elements in the layer
        feat = layer.GetNextFeature()
        while feat:
            coors_geom = []
            coors_geom_draw = []
            self.length.append(feat.GetField('length'))
            self.width.append(feat.GetField('width'))
            self.angle.append(feat.GetField('angle'))
            geom = feat.GetGeometryRef()
            for i in range(geom.GetPointCount()):
                x = geom.GetX(i)
                y = geom.GetY(i)
                draw_y = self.translateh - (y - y_bottom) - int(self.translateh / 2)
                draw_x = x - x_left + int(self.translatew / 2)
                coors_geom.append([x, y])
                coors_geom_draw.append([draw_x, draw_y])
            coors.append(array(coors_geom))
            coors_draw.append(array(coors_geom_draw))
            feat = layer.GetNextFeature()
        layer.ResetReading()  # Traversal pointer recovers the original location
        del datasrc, layer
        ##########First, calculate SciPy convex hull.################
        points = []
        for cnt in coors_draw:
            cnt = cnt.flatten()
            ptsx = [cnt[i] for i in range(len(cnt)) if (i % 2 == 0)]
            ptsy = [cnt[i] for i in range(len(cnt)) if (i % 2 != 0)]
            for ptx, pty in zip(ptsx, ptsy):
                points.append([ptx, pty])
        points = array(points)
        hull = ConvexHull(points)
        # hull.vertices: Get the index value of the convex polygon coordinates, counterclockwise
        hull1 = hull.vertices.tolist()
        hull1.append(hull1[0])
        self.convex = list(points[hull1].flatten())
        self.new_convex = list(self.convex)
        # Put feature into container rectangle and use it to set proper coordinates to the image
        self.container = self.canvas.create_rectangle((int(self.translatew / 2), int(self.translateh / 2) - (
                y_up - y_bottom), x_right - x_left + int(self.translatew / 2), int(self.translateh / 2)), width=0)
        self.minlength = int(min(x_right - x_left, y_up - y_bottom) + 0.5)
        hbar.configure(command=self.scroll_x)  # bind scrollbars to the canvas
        vbar.configure(command=self.scroll_y)
        # Bind events to the Canvas
        self.canvas.bind('<Configure>', lambda event: self.show())  # canvas is resized
        self.canvas.bind('<ButtonPress-2>', self.move_start)  # remember canvas position
        self.canvas.bind('<B2-Motion>', self.move_to)  # move canvas to the new position
        self.canvas.bind('<MouseWheel>', self.zoom)  # zoom image
        self.canvas.bind("<ButtonPress-3>", self.right_click)
        self.canvas.bind("<ButtonRelease-3>", self.right_release)
        self.canvas.bind('<KeyPress-q>', self.quit)
        self.canvas.bind("<ButtonPress-1>", self.left_click)
        self.canvas.bind("<B1-Motion>", self.press_move)
        self.canvas.bind("<ButtonRelease-1>", self.left_release)
        self.canvas.bind("<Control-ButtonPress-1>", self.fault_endpoint)
        # self.canvas.bind("<Control-ButtonRelease-1>", self.fault_draw)
        self.root.bind_all("<Control-Alt-z>", self.del_fault_endpoint)
        self.root.bind_all("<Control-z>", self.undo)
        self.root.bind_all("<Control-s>", self.exportImage)

        # draw some elements
        for i in range(len(coors_draw)):
            contour = coors_draw[i]
            contour = append(contour, [list(contour[0])], axis=0)
            self.canvas.create_line(list((contour.flatten())), fill='green', tag=('contour',))

        self.convex_id = self.canvas.create_line(self.convex, fill='red', tag=('convex',))
        self.textsize = 10
        for i in range(int(len(self.convex) / 2 - 1)):
            self.canvas.create_text(self.convex[i * 2], self.convex[i * 2 + 1], text=str(i + 1), font=(
                'Times', self.textsize), tags=('text',), fill='')

        self.canvas.lower(self.container)
        self.show()
        # Sets focus for the canvas in response to keyboard keystroke events
        self.canvas.focus_set()

    def right_click(self, event):
        # Gets the position coordinates of the added convex angular point
        distance = []
        x, y = self.getcanvasxy(event)
        closetid = self.canvas.find_overlapping(x - 3, y - 3, x + 3, y + 3)
        closetid = list(closetid)
        try:
            closetid = [singleid for singleid in closetid if singleid not in self.canvas.find_withtag('text')]
            closetid.remove(self.container)
        except:
            pass
        if closetid:
            closetid = closetid[0]
            coors = self.canvas.coords(closetid)
            for i in range(int(len(coors) / 2)):
                dist = (coors[i * 2] - x) * (coors[i * 2] - x) + (coors[i * 2 + 1] - y) * (coors[i * 2 + 1] - y)
                distance.append(dist)
            index = distance.index(min(distance))
            self.xy_hull = [coors[index * 2], coors[index * 2 + 1]]
            text = self.e_text.get()
            if text:
                text = int(text)
                self.new_convex.insert((text - 1) * 2, self.xy_hull[0])
                self.new_convex.insert((text - 1) * 2 + 1, self.xy_hull[1])
                self.convexIndex_add.append((text - 1) * 2)
                self.convexIndex_add.append((text - 1) * 2 + 1)
            else:
                self.text.set("Please enter the position of the add point in the original outsourcing contour!")
        else:
            self.text.set(
                "Mouse capture distance is only three pixels before and after so the capture distance is small, " +
                "please close to the object!")

    def right_release(self, event):
        self.canvas.delete(self.convex_id)
        self.convex_id = self.canvas.create_line(self.new_convex, fill='red', tag=('convex',))
        self.canvas.delete('text')
        for i in range(int(len(self.new_convex) / 2 - 1)):
            self.canvas.create_text(self.new_convex[i * 2], self.new_convex[i * 2 + 1], text=str(
                i + 1), font=('Times', int(self.textsize)), tags=('text',), fill='')
        self.canvas.lower('text')

    def left_click(self, event):
        if self.drawfault:
            self.drawfault = False
        else:
            # Save the beginning position of the mouse drag
            if self.screenShot:
                x0, y0 = self.canvas.winfo_rootx(), self.canvas.winfo_rooty()
                self.old_x, self.old_y = event.x + x0, event.y + y0
            self.start_x, self.start_y = self.getcanvasxy(event)
            # Create a rectangle if it does not exist
            self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x + 1, self.start_y + 1,
                                                     outline='gray75', fill='')

    # draw the rectangle dynamically
    def press_move(self, event):
        try:
            curX, curY = self.getcanvasxy(event)
            # Drag the mouse to expand the rectangle
            self.canvas.coords(self.rect, self.start_x, self.start_y, curX, curY)
            if self.screenShot:
                pass
            else:
                self.selection = [self.start_x, self.start_y, curX, curY]

                allid = self.canvas.find_overlapping(self.selection[0], self.selection[1], self.selection[2],
                                                     self.selection[3])
                allid = list(allid)
                try:
                    allid.remove(self.convex_id)
                except:
                    pass
                for singleid in allid:
                    flag = None
                    coors = self.canvas.coords(singleid)
                    if len(coors) != 2:
                        pass
                    else:
                        for i in range(int(len(self.new_convex) / 2 - 1)):
                            if coors == [self.new_convex[i * 2], self.new_convex[i * 2 + 1]]:
                                self.textid.append(singleid)
                                self.canvas.itemconfig(singleid, fill='black')
        except:
            pass

    def left_release(self, event):
        if self.drawfault:
            self.drawfault = False
        else:
            self.canvas.delete(self.rect)
            self.canvas.update()
            # Because the other command is tied to the key:control-left release, preventing a conflicting interrupt routine
            if self.screenShot:
                x0, y0 = self.canvas.winfo_rootx(), self.canvas.winfo_rooty()
                self.new_x, self.new_y = event.x + x0, event.y + y0
                self.printScreen()
                self.text.set("Screenshots have been completed. At the same time, the screenshot status ends!")
            else:
                try:
                    if self.textid:
                        for singleid in self.textid:
                            self.canvas.itemconfig(singleid, fill='')
                    self.textid = []
                except:
                    pass

    def printScreen(self):
        image = ImageGrab.grab((self.old_x, self.old_y, self.new_x, self.new_y))
        self.screenShot = False
        image.show()

    def del_fault_endpoint(self, event):
        if len(self.fault_pts) < 2:
            self.text.set('There are no dots on the image. It can not be undone！')
        elif len(self.fault_pts) < 4:
            self.fault_pts.pop()
            self.fault_pts.pop()
            allid = list(self.canvas.find_withtag('fault'))
            if allid:
                for singleid in allid:
                    self.canvas.delete(singleid)
        else:
            self.fault_pts.pop()
            self.fault_pts.pop()
            if len(self.fault_pts) < 4:
                allid = list(self.canvas.find_withtag('fault'))
                if allid:
                    for singleid in allid:
                        self.canvas.delete(singleid)
                self.id_pts = self.canvas.create_oval(self.fault_pts[0], self.fault_pts[1], self.fault_pts[0],
                                                      self.fault_pts[1], fill='black', tags=('fault',))
            else:
                # avoid deleting the range indicating container and the background image
                allid = list(self.canvas.find_withtag('fault'))
                if allid:
                    for singleid in allid:
                        self.canvas.delete(singleid)
                self.id_pts = self.canvas.create_line(self.fault_pts, fill='black', tags=('fault',))

    def undo(self, event):
        if self.convexIndex_add:
            self.new_convex = [self.new_convex[index] for index in range(len(self.new_convex)) if
                               index not in self.convexIndex_add[-2:]]
            self.canvas.delete(self.convex_id)
            self.convex_id = self.canvas.create_line(self.new_convex, fill='red', tag=('convex',))
            self.convexIndex_add = self.convexIndex_add[:-2]
            self.canvas.delete('text')
            for i in range(int(len(self.new_convex) / 2 - 1)):
                self.canvas.create_text(self.new_convex[i * 2], self.new_convex[i * 2 + 1], text=str(
                    i + 1), font=('Times', int(self.textsize)), tags=('text',), fill='')
            self.canvas.lower('text')
        else:
            self.text.set("No points have been added to the outsource polygon so no points can be deleted!")

    def fault_endpoint(self, event):
        self.drawfault = True
        if self.create:
            self.canvas.delete("axis")
            self.canvas.delete("o")
            self.canvas.delete("width")
            self.canvas.delete("base")
            self.canvas.delete("fault")
            self.create = False
            if len(self.fault_pts) == 4:
                self.fault_pts = []
                x, y = self.getcanvasxy(event)
                self.fault_pts.append(x)
                self.fault_pts.append(y)
                self.fault_draw()
        else:
            x, y = self.getcanvasxy(event)
            self.fault_pts.append(x)
            self.fault_pts.append(y)
            self.fault_draw()

    def fault_draw(self):
        if len(self.fault_pts) < 2:
            if self.id_pts:
                self.canvas.delete(self.id_pts)
            else:
                pass
        elif len(self.fault_pts) < 4:
            self.id_pts = self.canvas.create_oval(self.fault_pts[0], self.fault_pts[1], self.fault_pts[0],
                                                  self.fault_pts[1], fill='black', tags=('fault',))
        else:
            allid = list(self.canvas.find_withtag('fault'))
            if allid:
                for singleid in allid:
                    self.canvas.delete(singleid)
            self.id_pts = self.canvas.create_line(self.fault_pts, fill='black', tags=('fault',))

    def createImage(self):
        self.coordinate_axis = []
        self.index_mixture = []
        try:
            self.canvas.delete("axis")
            self.canvas.delete("o")
            self.canvas.delete("width")
            self.canvas.delete("base")
            self.canvas.delete("fault")
        except:
            pass
        if self.e_interval.get():
            interval = float(self.e_interval.get())
            interval *= self.scale
            if len(self.fault_pts) == 4:
                if self.fault_pts[0] == self.fault_pts[2]:
                    tan_faultAngle = None
                    faultAngle = 90
                    tan_theta = 0
                    self.new_convex_y = [self.new_convex[i] for i in range(1, len(self.new_convex), 2)]
                    y_index = self.new_convex_y.index(min(self.new_convex_y))
                    y0 = self.new_convex_y[y_index]
                    x0 = self.new_convex[y_index * 2]
                    y_bottom_index = self.new_convex_y.index(max(self.new_convex_y))
                    x_right_index = self.new_convex.index(max(self.new_convex_x))
                    y_bottom = self.new_convex_y[y_bottom_index]
                    x_bottom = self.new_convex[x_right_index * 2]
                    height = y_bottom - y0
                    # Find the coordinates of points 100 meters away from known points along the vertical direction of the fault line
                    x_width = 100
                    x1, y1, x2, y2 = x0 - x_width, y0, x0 + x_width, y0
                    x_bottom1, y_bottom1, x_bottom2, y_bottom2 = x_bottom - x_width, y_bottom, x_bottom + x_width, y_bottom
                    oval1 = self.canvas.create_oval([x0 - 2, y0 - 2, x0 + 2, y0 + 2], fill='blue', tags=('o',))
                    self.canvas.lower(oval1)
                    self.canvas.create_line([x1, y1, x2, y2], fill='blue', tags=('axis',))
                    oval2 = self.canvas.create_oval([x_bottom1 - 2, y_bottom1 - 2, x_bottom2 + 2, y_bottom2 + 2],
                                                    fill='blue',
                                                    tags=('o',))
                    self.canvas.lower(oval2)
                    self.coordinate_axis.append(x0)
                    self.coordinate_axis.append(y0)
                    # Calculate the position of the fault line after 100 meters of movement
                    dist = 0
                    allWidth_move = height
                    while dist < allWidth_move:
                        move_height = min(allWidth_move - dist, interval)
                        x0, y0, x1, y1, x2, y2 = x0, y0 + move_height, x1, y1 + move_height, x2, y2 + move_height
                        if move_height == interval and x0 != x_bottom:
                            oval = self.canvas.create_oval([x0 - 2, y0 - 2, x0 + 2, y0 + 2], fill='blue', tags=('o',))
                            self.canvas.lower(oval)
                            self.canvas.create_line([x1, y1, x2, y2], fill='blue', tags=('axis',))
                            self.coordinate_axis.append(x0)
                            self.coordinate_axis.append(y0)
                        dist += interval
                    self.canvas.create_line(self.coordinate_axis, fill='black', tags=('w',))
                else:
                    x2 = max(self.fault_pts[0], self.fault_pts[2])
                    x1 = min(self.fault_pts[0], self.fault_pts[2])
                    x2_index = self.fault_pts.index(x2)
                    y2 = self.fault_pts[x2_index + 1]
                    y1 = self.fault_pts[self.fault_pts.index(x1) + 1]
                    tan_faultAngle = (y2 - y1) / (x2 - x1)
                    faultAngle = degrees(atan(-1 * tan_faultAngle))
                    tan_theta = -1 / tan_faultAngle
                    self.new_convex_x = [self.new_convex[i] for i in range(0, len(self.new_convex), 2)]
                    x_index = self.new_convex_x.index(min(self.new_convex_x))
                    x0 = self.new_convex_x[x_index]
                    y0 = self.new_convex[x_index * 2 + 1]
                    x_right_index = self.new_convex_x.index(max(self.new_convex_x))
                    x_right = self.new_convex_x[x_right_index]
                    # y_right = self.new_convex[x_right_index * 2 + 1]
                    width = x_right - x0
                    x_width = sqrt(100 ** 2 * 1.0 / (tan_theta ** 2 + 1))
                    y_height = sqrt(100 ** 2 * 1.0 / ((1 / tan_theta) ** 2 + 1))
                    if tan_theta > 0:
                        x1, y1, x2, y2 = x0 - x_width, y0 - y_height, x0 + x_width, y0 + y_height
                        # x_right1,y_right1,x_right2,y_right2 = x_right - x_width, y_right - y_height,x_right + x_width,y_right + y_height
                    else:
                        x1, y1, x2, y2 = x0 + x_width, y0 - y_height, x0 - x_width, y0 + y_height
                        # x_right1,y_right1,x_right2,y_right2 = x_right + x_width, y_right - y_height,x_right - x_width,y_right + y_height

                    oval1 = self.canvas.create_oval([x0 - 2, y0 - 2, x0 + 2, y0 + 2], fill='blue', tags=('o',))
                    self.canvas.lower(oval1)
                    self.canvas.create_line([x1, y1, x2, y2], fill='blue', tags=('axis',))
                    # (x0, y0) i.e. the point through which the line must pass if the interval is to be used to calculate the width
                    self.coordinate_axis.append(x0)
                    self.coordinate_axis.append(y0)
                    # The position of the fault line after 100 meters of movement along the fault line
                    dist = 0
                    allWidth_move = sqrt((1 + tan_faultAngle ** 2) * width ** 2)
                    while dist < allWidth_move:
                        move_dist = min(allWidth_move - dist, interval)
                        move_width = sqrt(move_dist ** 2 * 1.0 / (tan_faultAngle ** 2 + 1))
                        move_height = sqrt(move_dist ** 2 * 1.0 / ((1 / tan_faultAngle) ** 2 + 1))
                        if tan_faultAngle > 0:
                            x0, y0, x1, y1, x2, y2 = x0 + move_width, y0 + move_height, x1 + move_width, y1 + move_height, x2 + move_width, y2 + move_height
                        else:
                            x0, y0, x1, y1, x2, y2 = x0 + move_width, y0 - move_height, x1 + move_width, y1 - move_height, x2 + move_width, y2 - move_height
                        if move_dist == interval and x0 != x_right:
                            oval = self.canvas.create_oval([x0 - 2, y0 - 2, x0 + 2, y0 + 2], fill='blue', tags=('o',))
                            self.canvas.lower(oval)
                            self.canvas.create_line([x1, y1, x2, y2], fill='blue', tags=('axis',))
                            self.coordinate_axis.append(x0)
                            self.coordinate_axis.append(y0)
                        dist += interval
                    self.canvas.create_line(self.coordinate_axis, fill='black', tags=('base',))

                convexPts_count = len(self.new_convex)  # the numbers of points in new convex
                k0 = tan_theta  # Obtain the slope value of the line perpendicular to the direction of the fault
                dir_vector = array(
                    [1, k0])  # Obtain the direction vector of a line perpendicular to the direction of the fault
                for j in range(2, len(self.coordinate_axis), 2):
                    coors_cal = []
                    x, y = self.coordinate_axis[j], self.coordinate_axis[
                        j + 1]  # Take the point through which the line of this distance interval passes
                    c = array([x, y])
                    b0 = y - k0 * x  # Calculate the intercept
                    for i in range(0, convexPts_count, 2):
                        if i < (convexPts_count - 2):
                            a = array([self.new_convex[i], self.new_convex[i + 1]])
                            b = array([self.new_convex[i + 2], self.new_convex[i + 3]])
                            if cross(a - c, dir_vector) * cross(b - c, dir_vector) <= 0:
                                if self.new_convex[i] > self.new_convex[i + 2]:
                                    x2 = self.new_convex[i]
                                    y2 = self.new_convex[i + 1]
                                    x1 = self.new_convex[i + 2]
                                    y1 = self.new_convex[i + 3]
                                else:
                                    x1 = self.new_convex[i]
                                    y1 = self.new_convex[i + 1]
                                    x2 = self.new_convex[i + 2]
                                    y2 = self.new_convex[i + 3]

                                if x2 == x1:
                                    k1 = None
                                    b1 = 0
                                    x_cal = x1
                                    y_cal = k0 * x_cal + b0
                                else:
                                    k1 = (y2 - y1) * 1.0 / (x2 - x1)
                                    b1 = y1 - k1 * x1
                                    x_cal = (b0 - b1) * 1.0 / (k1 - k0)
                                    y_cal = k0 * x_cal + b0
                                coors_cal.append([x_cal, y_cal])
                    if coors_cal:
                        distance = sqrt((coors_cal[0][0] - coors_cal[1][0]) ** 2 + (
                                coors_cal[0][1] - coors_cal[1][1]) ** 2) / self.scale
                        self.index_mixture.append([j, distance])

                # Labeled coordinate axes
                if self.index_mixture:
                    for index_dist in self.index_mixture:
                        self.canvas.create_text(self.coordinate_axis[index_dist[0]],
                                                self.coordinate_axis[index_dist[0] + 1], text=(str(
                                round(index_dist[1], 1)) + ' m'), font=('Times', int(self.textsize)),
                                                tags=('width',), fill='black')

                    list_interval = [i * float(self.e_interval.get()) for i in range(1, len(self.index_mixture) + 1)]
                    data = array(sorted(self.index_mixture, key=(lambda x: x[0])))[:, 1]
                    fig = figure()
                    # bar diagram
                    ax2 = fig.add_subplot(121)
                    ax2.bar(list_interval, data, color='lightblue', tick_label=list_interval)

                    # list_interval1 = list_interval[1:]
                    xnew = linspace(int(min(list_interval)), int(max(list_interval)),
                                    (int(max(list_interval)) - int(min(list_interval))) * 2)
                    # interpolation
                    spl = make_interp_spline(list_interval, data, k=3)
                    smooth = spl(xnew)
                    # plotting
                    ax2.plot(xnew, smooth)
                    ax2.set_ylabel("Width/m")
                    ax2.set_xlabel("Distance/m")
                    ax2.set_title("Width of surface rupture zone", fontsize=15)

                    # rose diagram
                    ax = fig.add_subplot(122, projection='polar')
                    subplots_adjust(bottom=0.1)
                    minVal = min(self.length)
                    maxVal = max(self.length)
                    axcolor = 'lightgoldenrodyellow'
                    axleng = axes([0.2, 0.017, 0.6, 0.03], facecolor=axcolor)
                    slength = matSlider(axleng, 'length', minVal, maxVal, valinit = minVal, valfmt = '%.5f', valstep = 0.01, color = 'lightgray')
                    def update(val):
                        anglelist = []
                        thresLength = slength.val
                        for length,new_angle in zip(self.length,self.angle):
                            if length >= thresLength:
                                anglelist.append(new_angle)
                        ax.clear()
                        angle = [angle - faultAngle if angle >= faultAngle else 180 + angle - faultAngle for angle in
                                 anglelist]

                        bins = arange(-5, 186, 10)
                        numbers_of_angles, bins = histogram(angle, bins)
                        numbers_of_angles[0] += numbers_of_angles[-1]
                        numbers_of_angles = concatenate([numbers_of_angles[:-1], numbers_of_angles[:-1]])
                        ax.bar(deg2rad(arange(0, 360, 10)), numbers_of_angles, width=deg2rad(10), bottom=0.0,
                               color='0.8', edgecolor='k')
                        ax.set_theta_zero_location('E')

                        # By default,angles are marked counterclockwise.
                        # If this parameter is set to -1, angles are marked clockwise
                        # ax.set_theta_direction(-1)

                        ax.set_thetagrids(arange(0, 360, 10), labels=arange(0, 360, 10))
                        ax.set_rgrids(arange(0, numbers_of_angles.max() + 1, 10), angle=0, weight='black')
                        ax.set_title('Rose diagram of angles between surface ruptures and fault trace', fontsize=15)
                        fig.canvas.draw_idle()
                    slength.on_changed(update)
                    slength.reset()
                    slength.set_val(minVal)

                    mng = get_current_fig_manager()
                    mng.window.state("zoomed")
                    self.text.set("The bar chart and angle rose diagram have been created successfully!")
                    self.create = True
                    show()
            else:
                self.text.set("Please select the fault trace correctly!")
        else:
            self.text.set("Please enter the partition interval of surface rupture zone correctly!")

    def exportImage(self, event):
        self.text.set("You have entered the screenshot state. You can capture the image by pulling down the mouse!")
        self.screenShot = True

    def quit(self, event):
        self.root.destroy()

    def scroll_x(self, *args, **kwargs):
        """ Scroll canvas horizontally and redraw the image """
        self.canvas.xview(*args)  # scroll horizontally
        self.show()

    def scroll_y(self, *args, **kwargs):
        """ Scroll canvas vertically and redraw the image """
        self.canvas.yview(*args)  # scroll vertically
        self.show()

    def show(self):
        """ Show image on the Canvas. Implements correct image zoom almost like in Google Maps """
        box_image = self.canvas.coords(self.container)  # get image area
        # acquire the screen range corresponding to the visible area of the canvas
        box_canvas = (self.canvas.canvasx(0),
                      self.canvas.canvasy(0),
                      self.canvas.canvasx(self.canvas.winfo_width()),
                      self.canvas.canvasy(self.canvas.winfo_height()))

        # Get scroll region box
        box_scroll = [min(box_image[0], box_canvas[0]), min(box_image[1], box_canvas[1]),
                      max(box_image[2], box_canvas[2]), max(box_image[3], box_canvas[3])]

        # convert to integer or it will not work properly
        self.canvas.configure(scrollregion=tuple(map(int, box_scroll)))  # set scroll region

    def move_start(self, event):
        """ Remember previous coordinates for scrolling with the mouse """
        x, y = self.getcanvasxy(event)
        self.canvas.scan_mark(int(x + 0.5), int(y + 0.5))

    def move_to(self, event):
        """ Drag (move) canvas to the new position """
        x, y = self.getcanvasxy(event)
        self.canvas.scan_dragto(int(x + 0.5), int(y + 0.5), gain=1)
        self.show()

    def outside(self, x, y):
        """ Checks if the point (x,y) is outside the image area """
        bbox = self.canvas.coords(self.container)  # get image area
        if bbox[0] < x < bbox[2] and bbox[1] < y < bbox[3]:
            return False  # point (x,y) is inside the image area
        else:
            return True  # point (x,y) is outside the image area

    # get coordinates of the event on the canvas
    def getcanvasxy(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        return x, y

    def zoom(self, event):
        """ Zoom with mouse wheel """
        x, y = self.getcanvasxy(event)
        if self.outside(x, y): return  # zoom only inside elements area
        scale = 1.0
        # Respond to Windows (event.delta) wheel event
        if event.delta < 0:  # scroll down, zoom out, smaller
            if round(
                    self.minlength * self.scale) < 30: return  # The minimum side length of the image is less than 30 pixels
            self.scale /= self.delta
            scale /= self.delta
            if self.textsize >= 10:
                self.textsize /= self.delta
        if event.delta > 0:  # scroll up, zoom in, bigger
            i = float(min(self.canvas.winfo_width(), self.canvas.winfo_height()) >> 1)
            if i < self.scale: return  # 1 pixel is bigger than the visible area
            self.scale *= self.delta
            scale *= self.delta
            if self.textsize <= 30:
                self.textsize *= self.delta

        self.canvas.scale('all', x, y, scale, scale)  # zoom all object
        self.canvas.delete('text')
        self.new_convex = self.canvas.coords('convex')
        for i in range(int(len(self.new_convex) / 2 - 1)):
            text = self.canvas.create_text(self.new_convex[i * 2], self.new_convex[i * 2 + 1], text=str(
                i + 1), font=('Times', int(self.textsize)), tags=('text',), fill='')
        self.canvas.lower('text')
        try:
            self.canvas.delete('distance')
            self.coordinate_axis = self.canvas.coords('w')
            if self.index_mixture:
                # Labeled coordinate axes
                for index_dist in self.index_mixture:
                    self.canvas.create_text(self.coordinate_axis[index_dist[0]],
                                            self.coordinate_axis[index_dist[0] + 1], text=(str(
                            round(index_dist[1], 1)) + ' m'), font=('Times', int(self.textsize)), tags=('distance',),
                                            fill='black')
        except:
            pass

        self.show()


if __name__ == "__main__":
    switch_backend('TkAgg')
    path = None
    root = Tk()
    app = InputImage(root)
    root.mainloop()
    if path == None:
        root = Tk()
        root.withdraw()
        messagebox.showerror("Error", "Please input the path of vector file correctly!")
        root.destroy()
        root.mainloop()
    else:
        path_shp = path
        mainWindow = Tk()
        mainWindow.state('zoomed')
        mainWindow.title('widthAndstrike')
        frame = Rupture(mainWindow, path_shp)
        mainWindow.columnconfigure(0, weight=1)
        mainWindow.rowconfigure(0, weight=1)
        mainWindow.mainloop()
