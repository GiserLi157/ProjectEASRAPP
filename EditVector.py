# -*- coding: utf-8 -*-
# Advanced zoom for images of various types from small to huge up to several GB
from tkinter import ttk, TclError, Scrollbar, Label, Tk, Entry, Button, filedialog, StringVar, Canvas, _flatten, messagebox
from PIL import Image, ImageTk
from math import ceil, log
from warnings import catch_warnings, simplefilter
from rasterio import open as rasterOpen
from rasterio.windows import Window
from cv2 import merge, drawContours
from numpy import uint8, append, zeros, array
from osgeo.gdal import Open, SetConfigOption, GDT_Byte, GDT_UInt16, GDT_CInt16, GDT_Float32, GDT_Float64, GetDriverByName as gdalGetDriverByName
from osgeo.osr import SpatialReference
from osgeo.ogr import UseExceptions, FieldDefn, Geometry, wkbLinearRing, OFTReal, Feature, wkbLineString
from osgeo.ogr import GetDriverByName as ogrGetDriverByName
from os import path as ospath


class inputImgVector:
    def __init__(self):
        width = 500
        height = 400
        self.flag = None
        self.root = Tk()
        size_align = '%dx%d+%d+%d' % (
            width, height, (self.root.winfo_screenwidth() - width) / 2, (self.root.winfo_screenheight() - height) / 2)
        self.root.geometry(size_align)
        self.root.title('Select the image and corresponding vector...')
        # Creates the first Label
        Label(self.root, text="image_path").place(x=100, y=100)
        # Creates the second Label
        Label(self.root, text="vector_path").place(x=100, y=200)
        self.e1_text = StringVar()
        self.e2_text = StringVar()
        Entry(self.root, width = 20, textvariable = self.e1_text).place(x = 180, y = 100)
        Entry(self.root, width = 20, textvariable = self.e2_text).place(x = 180, y = 200)

        Button(self.root, text = "...", command = self.select_image_path).place(x = 330, y = 96)
        Button(self.root, text = "...", command = self.select_vector_path).place(x = 330, y = 196)
        Button(self.root, text = "Ok", command = self.getpath, activebackground = "pink",
               activeforeground = "blue").place(x = 145, y = 300)
        Button(self.root, text = "Cancel", command = self.root.destroy, activebackground = "pink",
               activeforeground = "blue").place(x = 290, y = 300)
        self.root.mainloop()

    def select_image_path(self):
        imgPath = filedialog.askopenfilename(title = 'Select the image path...', initialdir = None,
                                             filetypes = [(
                                                 "image", ".tif"), ('All Files', ' *')], defaultextension = '.tif')
        self.e1_text.set(str(imgPath))

    def select_vector_path(self):
        maskPath = filedialog.askopenfilename(title = 'Select the mask path...', initialdir = None,
                                              filetypes = [(
                                                  "vector", ".shp"), ('All Files', ' *')], defaultextension = '.shp')
        self.e2_text.set(str(maskPath))

    def getpath(self):
        self.root.destroy()
        imagePath, maskPath = self.e1_text.get(), self.e2_text.get()
        self.flag = [imagePath, maskPath]

    def getCnts(self, vectorPath, imagePath):
        grid_ds = Open(imagePath)
        geotrans = grid_ds.GetGeoTransform()
        coors_draw, length, width, angle = [], [], [], []
        shp_driver = ogrGetDriverByName('Esri Shapefile')
        # The second argument is 0 (read-only), 1 (writable), default 0 (read-only)
        datasrc = shp_driver.Open(vectorPath)
        if datasrc == "None":
            messagebox.showerror("Error", "Failed to open the vector file!")
        layer = datasrc.GetLayer(0)  # obtain layer
        # Loop through all elements in the layer
        feat = layer.GetNextFeature()
        while feat:
            coors_geom_draw = []
            length.append(feat.GetField('length'))
            width.append(feat.GetField('width'))
            angle.append(feat.GetField('angle'))
            geom = feat.GetGeometryRef()
            for i in range(geom.GetPointCount()):
                x = geom.GetX(i)
                y = geom.GetY(i)
                draw_row, draw_col = self.geo2pixel(x, y, geotrans)
                coors_geom_draw.append([draw_col, draw_row])
            coors_draw.append(array(coors_geom_draw))
            feat = layer.GetNextFeature()
        layer.ResetReading()  # Traversal pointer recovers the original location
        del datasrc, layer
        return [coors_draw, length, width, angle]

    def geo2pixel(self, geox, geoy, geoTrans):
        #     Convert the given projection or geographic coordinates to the coordinates on the image map (
        #     column and column numbers) according to the six-parameter model of GDAL
        #     :param dataset: GDAL geographic data structure
        #     :param geox: Projection or geographic coordinate x
        #     :param geoy: Projection or geographic coordinate y
        #     return: Row, Column on image map corresponding to projection or geographic coordinates (geox, geoy)
        # method1.
        #     a = np.array([[geoTrans[1], geoTrans[2]], [geoTrans[4], geoTrans[5]]])
        #     b = np.array([geox - geoTrans[0],geoTrans[3] - geoy])
        #     col,row = np.linalg.solve(a, b) # Use Numpy's Linalg. solve function to solve the values of the unknowns of a binary first-order equation
        #     row = int(row + 0.5)
        #     col = int(col +0.5)
        # method2 is as follows.
        g0 = geoTrans[0]
        g1 = geoTrans[1]
        g2 = geoTrans[2]
        g3 = geoTrans[3]
        g4 = geoTrans[4]
        g5 = geoTrans[5]
        row = int(((geox - g0) * g4 - (geoy - g3) * g1) / (g2 * g4 - g1 * g5) + 0.5)
        col = int(((geox - g0) * g5 - (geoy - g3) * g2) / (g1 * g5 - g2 * g4) + 0.5)
        return [row, col]


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


class editAndzoom(ttk.Frame):
    """ Display and zoom image """
    global del_index

    def __init__(self, root, path, cnts):
        super().__init__()
        """ Initialize the ImageFrame """
        self.path = path
        self.tile_height = 1024
        self.referencebox = []
        self.del_coor = []
        self.root = root
        self.imscale = 1.0  # the scale for the canvas image zoom
        self.delta = 1.1  # zoom magnitude
        self.previous_state = 0  # Initialize the keyboard state
        self.interpolation_function = Image.ANTIALIAS  # could be: NEAREST, BILINEAR, BICUBIC and ANTIALIAS
        self.grid(row = 0, column = 0, sticky = 'nswe')
        self.grid_rowconfigure(0, weight = 1)
        self.grid_columnconfigure(0, weight = 1)
        # Vertical and horizontal scrollbars for canvas
        hbar = CreateScrollbar(self, orient = 'horizontal')
        vbar = CreateScrollbar(self, orient = 'vertical')
        hbar.grid(row = 1, column = 0, sticky = 'we')
        vbar.grid(row = 0, column = 1, sticky = 'ns')
        # Create a message prompt label
        self.var_text = StringVar()
        Label(self.root, textvariable = self.var_text, fg = 'green', font = ("黑体", 30)).grid(row = 2, sticky = 'w')

        # Create canvas and bind it with scrollbars. Public for outer classes
        self.canvas = Canvas(self, highlightthickness = 0,
                             xscrollcommand = hbar.set, yscrollcommand = vbar.set)
        self.canvas.grid(row = 0, column = 0, sticky = 'nswe')
        self.update()
        hbar.configure(command = self.scroll_x)  # bind scrollbars to the canvas
        vbar.configure(command = self.scroll_y)

        with catch_warnings():
            simplefilter('ignore')
            ds = rasterOpen(self.path)
            gdal_ds = Open(self.path)
            self.geotrans, self.proj = gdal_ds.GetGeoTransform(), gdal_ds.GetProjection()
            del gdal_ds
            self.imheight, self.imwidth = ds.height, ds.width

        # Put image into container rectangle and use it to set proper coordinates to the image
        self.container = self.canvas.create_rectangle((0, 0, self.imwidth, self.imheight), width=0)

        # Bind events to the Canvas
        self.canvas.bind('<Configure>', lambda event: self.show())  # canvas is resized
        self.canvas.tag_bind('one', '<ButtonPress-3>', self.delete)
        self.canvas.bind('<ButtonPress-2>', self.move_start)  # remember canvas position
        self.canvas.bind('<B2-Motion>', self.move_to)  # move canvas to the new position
        self.canvas.bind("<Control-z>", self.undel)
        self.canvas.bind("<ButtonPress-1>", self.click)
        self.canvas.bind("<B1-Motion>", self.press_move)
        self.canvas.bind("<ButtonRelease-1>", self.left_release)
        self.canvas.bind('<MouseWheel>', self.zoom)  # zoom image
        self.canvas.bind('<KeyPress-q>', self.quit)
        # Handle keystrokes in idle mode, because program slows down on a weak computers,
        # when too many key stroke events in the same time
        self.canvas.bind('<Key>', lambda event: self.canvas.after_idle(self.keystroke, event))

        # Decide if this image huge or not
        self.huge = False  # huge or not
        self.huge_size = 10000  # define size of the huge image
        Image.MAX_IMAGE_PIXELS = 1000000000  # suppress DecompressionBombError for big image

        if self.imwidth * self.imheight > self.huge_size * self.huge_size:
            self.huge = True  # image is huge

        self.minlength = min(self.imwidth, self.imheight)  # get the fixed_size image side

        # Store images in fixed memory
        messagebox.showinfo("Prompt", "please wait a moment for creating the image pyramids!")
        if self.huge:
            self.pyramid = [self.fixed_size()]
        else:
            img = ds.read()
            r = img[0]
            g = img[1]
            b = img[2]
            img = merge([r, g, b])
            self.pyramid = [Image.fromarray(img)]
        del ds
        # Create image pyramid
        # Set ratio coefficient for image pyramid
        self.ratio = max(self.imwidth, self.imheight) / self.huge_size if self.huge else 1.0

        self.curr_img = 0  # current image from the pyramid

        self.scale = self.imscale * self.ratio  # image pyramide scale

        self.reduction = 2  # reduction degree of image pyramid

        (w, h), m, j = self.pyramid[-1].size, 512, 0

        n = ceil(log(min(w, h) / m, self.reduction)) + 1  # image pyramid length

        while w > m and h > m:  # top pyramid image is around 512 pixels in size
            j += 1
            w /= self.reduction  # divide on reduction degree
            h /= self.reduction  # divide on reduction degree
            self.pyramid.append(self.pyramid[-1].resize((int(w + 0.5), int(h + 0.5)), self.interpolation_function))
        self.var_text.set('Promt: Creating {0}-layer image pyramids successfully!'.format(n))
        # Redraw some figures before showing image on the screen
        for i in range(len(cnts)):
            contour = cnts[i]
            contour = append(contour, [list(contour[0])], axis = 0)
            self.canvas.create_line(list((contour.flatten())), fill = 'red', activefill = 'gray75', tag = (i, 'one'))

        self.canvas.lower(self.container)
        self.show()  # show image on the canvas
        # Sets focus for the canvas in response to keyboard keystroke events
        self.canvas.focus_set()

    def fixed_size(self):
        """ Resize image proportionally and return fixed_size image """
        w1, h1 = float(self.imwidth), float(self.imheight)
        w2, h2 = float(self.huge_size), float(self.huge_size)
        width_height_ratio1 = w1 / h1
        width_height_ratio2 = 1
        if width_height_ratio1 == width_height_ratio2:
            image = Image.new('RGB', (int(w2), int(h2)))
            k = h2 / h1
            w = int(w2)  # The width of the image occupying fixed memory
        elif width_height_ratio1 > width_height_ratio2:
            image = Image.new('RGB', (int(w2), int(w2 / width_height_ratio1)))
            w = int(w2)
            k = h2 / w1
        else:
            image = Image.new('RGB', (int(h2 * width_height_ratio1), int(h2)))
            w = int(h2 * width_height_ratio1 + 0.5)
            k = h2 / h1

        tile_h, i, j, n = 0, 0, 0, ceil(self.imheight / self.tile_height)
        while i < self.imheight:
            j += 1
            band = min(self.tile_height, self.imheight - i)  # height of the tile
            ds = rasterOpen(self.path)
            img = ds.read(window = Window(0, i, self.imwidth, band))
            del ds
            r = img[0]
            g = img[1]
            b = img[2]
            img = merge([r, g, b])
            rawimage = Image.fromarray(img)  # acquire image 
            del img
            image.paste(rawimage.resize((w, int(band * k) + 1), self.interpolation_function), (0, int(i * k)))
            i += band

        return image

    def quit(self, event):
        self.root.destroy()

    def scroll_x(self, *args, **kwargs):
        """ Scroll canvas horizontally and redraw the image """
        self.canvas.xview(*args)  # scroll horizontally
        self.show()  # redraw the image

    def scroll_y(self, *args, **kwargs):
        """ Scroll canvas vertically and redraw the image """
        self.canvas.yview(*args)  # scroll vertically
        self.show()  # redraw the image

    def show(self):
        """ Show image on the Canvas. Implements correct image zoom almost like in Google Maps """
        self.box_image = self.canvas.coords(self.container)  # get image area
        # acquire the screen range corresponding to the visible area of the canvas
        box_canvas = (self.canvas.canvasx(0),
                      self.canvas.canvasy(0),
                      self.canvas.canvasx(self.canvas.winfo_width()),
                      self.canvas.canvasy(self.canvas.winfo_height()))

        # Get scroll region box
        box_scroll = [min(self.box_image[0], box_canvas[0]), min(self.box_image[1], box_canvas[1]),
                      max(self.box_image[2], box_canvas[2]), max(self.box_image[3], box_canvas[3])]

        # convert to integer or it will not work properly  
        self.canvas.configure(scrollregion = tuple(map(int, box_scroll)))  # set scroll region

        # calculate the coordinate range of visible area
        x1 = max(box_canvas[0] - self.box_image[0], 0)
        y1 = max(box_canvas[1] - self.box_image[1], 0)
        x2 = min(box_canvas[2], self.box_image[2]) - self.box_image[0]
        y2 = min(box_canvas[3], self.box_image[3]) - self.box_image[1]

        if self.huge and self.curr_img < 0:  # show huge image, which does not fit in RAM
            h = int((y2 - y1) / self.imscale)  # height of the tile band
            w = int((x2 - x1) / self.imscale)  # width of the tile band
            ds = rasterOpen(self.path)
            img = ds.read(window = Window(int(x1 / self.imscale + 0.5), int(y1 / self.imscale + 0.5),
                                        int(w + 0.5), int(h + 0.5)))
            del ds
            r = img[0]
            g = img[1]
            b = img[2]
            img = merge([r, g, b])
            image = Image.fromarray(img)  # acquire the image
            del img
        else:
            # crop current img from pyramid
            image = self.pyramid[max(0, self.curr_img)].crop((int(x1 / self.scale + 0.5), int(y1 / self.scale + 0.5),
                                                              int(x2 / self.scale + 0.5), int(y2 / self.scale + 0.5)))

        imagetk = ImageTk.PhotoImage(
            image.resize((int(x2 - x1 + 0.5), int(y2 - y1 + 0.5)), self.interpolation_function))

        self.bg_id = self.canvas.create_image(max(box_canvas[0], self.box_image[0]),
                                              max(box_canvas[1], self.box_image[1]), anchor='nw', image=imagetk)

        self.canvas.lower(self.bg_id)  # set image into background
        self.canvas.imagetk = imagetk  # keep an extra reference to prevent garbage-collection

    def move_start(self, event):
        """ Remember previous coordinates for scrolling with the mouse """
        x, y = self.getcanvasxy(event)
        self.canvas.scan_mark(int(x + 0.5), int(y + 0.5))

    def move_to(self, event):
        """ Drag (move) canvas to the new position """
        x, y = self.getcanvasxy(event)
        self.canvas.scan_dragto(int(x + 0.5), int(y + 0.5), gain=1)
        self.show()  # zoom tile and show it on the canvas

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
        if self.outside(x, y): return  # zoom only inside image area
        scale = 1.0
        # Respond to Windows (event.delta) wheel event
        if event.delta < 0:  # scroll down, zoom out, smaller
            if round(
                    self.minlength * self.imscale) < 30: return  # The minimum side length of the image is less than 30 pixels
            self.imscale /= self.delta
            scale /= self.delta
        if event.delta > 0:  # scroll up, zoom in, bigger
            i = float(min(self.canvas.winfo_width(), self.canvas.winfo_height()) >> 1)
            if i < self.imscale: return  # 1 pixel is bigger than the visible area
            self.imscale *= self.delta
            scale *= self.delta
        # Take appropriate image from the pyramid
        k = self.imscale * self.ratio  # temporary coefficient

        self.curr_img = min((-1) * int(log(k, self.reduction)), len(self.pyramid) - 1)
        self.scale = k * pow(self.reduction, max(0, self.curr_img))
        self.canvas.scale('all', x, y, scale, scale)  # zoom all object
        self.show()

    def keystroke(self, event):
        """ Scrolling with the keyboard.
            Independent from the language of the keyboard, CapsLock, <Ctrl>+<key>, etc. """
        if event.state - self.previous_state == 4:  # means that the Control key is pressed
            pass  # do nothing if Control key is pressed
        else:
            self.previous_state = event.state  # remember the last keystroke state
            # Up, Down, Left, Right keystrokes
            if event.keycode in [68, 39, 102]:  # scroll right, keys 'd' or 'Right'
                self.scroll_x('scroll', 1, 'unit', event=event)
            elif event.keycode in [65, 37, 100]:  # scroll left, keys 'a' or 'Left'
                self.scroll_x('scroll', -1, 'unit', event=event)
            elif event.keycode in [87, 38, 104]:  # scroll up, keys 'w' or 'Up'
                self.scroll_y('scroll', -1, 'unit', event=event)
            elif event.keycode in [83, 40, 98]:  # scroll down, keys 's' or 'Down'
                self.scroll_y('scroll', 1, 'unit', event=event)

    def click(self, event):
        # Save the beginning position of the mouse dragged
        self.start_x, self.start_y = self.getcanvasxy(event)
        # Create a rectangle if it does not exist
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x + 1, self.start_y + 1,
                                                 outline='gray75', fill='')

    # Draws a dynamic rectangle
    def press_move(self, event):
        curX, curY = self.getcanvasxy(event)
        # Drag the mouse to expand the rectangle
        self.canvas.coords(self.rect, self.start_x, self.start_y, curX, curY)

    def left_release(self, event):
        global del_index
        self.canvas.delete(self.rect)
        x, y = self.getcanvasxy(event)
        self.selection = [self.start_x, self.start_y, x, y]
        #  print(self.selection[0],self.selection[1], self.selection[2], self.selection[3])
        # Return the ID of all canvas objects that overlap the qualified rectangle (including, of course, canvas objects within the qualified rectangle)
        # -- If no canvas object specified by item exists, no error is raised
        # -- Item can be the ID of a single canvas object or a Tag
        allid = self.canvas.find_overlapping(self.selection[0], self.selection[1], self.selection[2], self.selection[3])
        temp_coors = []
        temp_tags = []
        allid = list(allid)
        # If the background image is selected, extract the ID to prevent the background image from being deleted by mistake
        try:
            allid.remove(self.bg_id)
        except:
            pass
        # If the container rectangle is selected, extract the ID to prevent the container rectangle from being deleted by mistake
        try:
            allid.remove(self.container)
        except:
            pass
        for singleid in allid:
            if self.canvas.gettags(singleid):
                temp_tags.append(int(self.canvas.gettags(singleid)[0]))
                temp_coors.append(self.canvas.coords(singleid))
            self.canvas.delete(singleid)
        self.referencebox.append(self.box_image)
        del_index.append(temp_tags)
        self.del_coor.append(temp_coors)

    def undel(self, event):
        global del_index
        box_image_startx = self.box_image[0]
        box_image_starty = self.box_image[1]
        box_image_w = self.box_image[2] - self.box_image[0]
        box_image_h = self.box_image[3] - self.box_image[1]
        if del_index == []:
            self.var_text.set('Nothing need to be Undo!')
        else:
            index, coor = del_index.pop(), self.del_coor.pop()
            box = self.referencebox.pop()
            reference_startx = box[0]
            reference_starty = box[1]
            reference_w = box[2] - box[0]
            reference_h = box[3] - box[1]
            # Retrieves the coordinates and labels of an object that was last deleted，and redraw it onto the canvas
            for singletag, item in zip(index, coor):
                # Recalculate and redraw the coordinates on the canvas
                new_item = []
                coors_x = [item[i] for i in range(len(item)) if i % 2 == 0]
                coors_y = [item[i] for i in range(len(item)) if i % 2 != 0]
                for coorx, coory in zip(coors_x, coors_y):
                    x = (coorx - reference_startx) / reference_w * box_image_w + box_image_startx
                    y = (coory - reference_starty) / reference_h * box_image_h + box_image_starty
                    new_item.append(x)
                    new_item.append(y)
                self.canvas.create_line(new_item, fill = 'red', activefill = 'gray75', tag = (singletag, 'one'))

    def delete(self, event):
        global del_index
        temp_coors = []
        temp_tags = []
        temp_coors.append(self.canvas.coords('current'))  # Gets the coordinates of the currently active item
        temp_tags.append(int(self.canvas.gettags('current')[0]))
        self.del_coor.append(temp_coors)
        self.referencebox.append(self.box_image)
        del_index.append(temp_tags)
        self.canvas.delete('current')  # Deletes the currently active object


class output:
    def __init__(self, root, path, cnts, lengths, widths, angles):
        width = 500
        height = 400
        size_align = '%dx%d+%d+%d' % (
            width, height, (root.winfo_screenwidth() - width) / 2, (root.winfo_screenheight() - height) / 2)
        self.root = root
        ds = rasterOpen(path)
        self.image = ds.read()
        r = self.image[0]
        g = self.image[1]
        b = self.image[2]
        self.image = merge([r, g, b])
        del r, g, b
        gdal_ds = Open(path)
        self.geotrans, self.proj = gdal_ds.GetGeoTransform(), gdal_ds.GetProjection()
        self.imheight, self.imwidth = ds.height, ds.width
        del gdal_ds, ds
        self.cnts, self.resolution, self.length, self.width, self.angle = cnts, self.geotrans[
            1], lengths, widths, angles
        self.root.geometry(size_align)
        self.root.title('Save the result...')
        # Creates the first Label Label
        Label(self.root, text = "raster_path").place(x = 100, y = 100)
        # Creates the second Label Label
        Label(self.root, text = "vector_path").place(x = 100, y = 200)
        self.e1_text = StringVar()
        self.e2_text = StringVar()
        Entry(self.root, width = 20, textvariable = self.e1_text).place(x = 180, y = 100)
        Entry(self.root, width = 20, textvariable = self.e2_text).place(x = 180, y = 200)

        Button(self.root, text = "...", command = self.select_raster_path).place(x = 330, y = 96)
        Button(self.root, text = "...", command = self.select_vector_path).place(x = 330, y = 196)
        Button(self.root, text = "Save", command = self.output, activebackground = "pink",
                           activeforeground = "blue").place(x = 145, y = 300)
        Button(self.root, text = "Cancel", command = self.root.destroy, activebackground = "pink",
                             activeforeground = "blue").place(x = 290, y = 300)

    def select_raster_path(self):
        save_file = filedialog.asksaveasfilename(title = 'Select the raster file storage path...', initialdir = None,
                                                 filetypes = [(
                                                     "raster", ".tif"), ('All Files', ' *')], defaultextension = '.tif')
        self.e1_text.set(str(save_file))

    def select_vector_path(self):
        save_file = filedialog.asksaveasfilename(title = 'Select the vector file storage path...', initialdir = None,
                                                 filetypes = [(
                                                     "vector", ".shp"), ('All Files', ' *')], defaultextension = '.shp')
        self.e2_text.set(str(save_file))

    def pixel2geo(self, row, col, geoTrans):
        geox = geoTrans[0] + geoTrans[1] * col + geoTrans[2] * row
        geoy = geoTrans[3] + geoTrans[4] * col + geoTrans[5] * row
        return geox, geoy

    def writeTif(self, path, img, im_geotrans, im_proj, nodata = None):
        data_type = img.dtype.name
        if 'uint8' in data_type:
            dtype = GDT_Byte
        elif 'uint16' in data_type:
            dtype = GDT_UInt16
        elif 'int16' in data_type:
            dtype = GDT_CInt16
        elif 'float32' in data_type:
            dtype = GDT_Float32
        else:
            dtype = GDT_Float64

        im_bands = 1
        if len(img.shape) == 3:
            im_height, im_width, im_bands = img.shape
        else:
            im_height, im_width = img.shape
        # Create output TIF file
        gTiffDriver = gdalGetDriverByName("GTiff")
        ds = gTiffDriver.Create(path, im_width, im_height, im_bands, dtype, options=["COMPRESS=LZW", "BIGTIFF=YES"])
        ds.SetGeoTransform(im_geotrans)  # Writes affine transformation parameters for the image
        ds.SetProjection(im_proj)  # Write the projection for the image
        if im_bands != 1:
            for i in range(im_bands):
                band = ds.GetRasterBand(i + 1)
                band.WriteArray(img[:, :, i])
                if nodata != None:
                    band.SetNoDataValue(nodata)  # Nodata value is optional
        else:
            band = ds.GetRasterBand(1)
            band.WriteArray(img)
            if nodata != None:
                band.SetNoDataValue(nodata)  # Nodata value is optional

        del gTiffDriver
        del ds

    def output(self):
        raster_path = self.e1_text.get()
        vector_path = self.e2_text.get()
        print(raster_path)
        maskout = zeros((self.image.shape[0], self.image.shape[1], 3), uint8)
        if vector_path:
            UseExceptions()
            SetConfigOption("GDAL_FILENAME_IS_UTF8", "NO")  # In order to support the Chinese path
            SetConfigOption("SHAPE_ENCODING", "CP936")  # in order to enable property sheet fields to support Chinese
            [outfilepath, outfilename] = ospath.split(vector_path)
            name = ospath.splitext(outfilename)[0]

            # To create data. Here,create an ESRI SHP file
            driver = ogrGetDriverByName("ESRI Shapefile")
            if driver == None:
                messagebox.showerror("Error", "The driver ({0}) is not available!\n".format("ESRI Shapefile"))

            if ospath.exists(vector_path):
                driver.DeleteDataSource(vector_path)

            ds = driver.CreateDataSource(outfilepath)  # To create Datasource

            if ds is None:
                messagebox.showerror("Error", "Failed to create SHP data source({0}) failed!".format(outfilepath))

            in_srs = SpatialReference()  # Creating a space reference
            in_srs.ImportFromWkt(self.proj)  # Import projection coordinate system

            # Create a layer:creating a polyline layer. name==>SHP name
            layer = ds.CreateLayer(name, in_srs, geom_type = wkbLineString)

            if layer is None:
                messagebox.showerror("Error", "Failed to create the vector layer!\n")

            '''Add vector data: property sheet data, vector data coordinates'''
            FieldLEN = FieldDefn("length", OFTReal)  # Creating a floating property field: length
            layer.CreateField(FieldLEN)
            FieldWID = FieldDefn("width", OFTReal)  # Creating a floating property field: width
            layer.CreateField(FieldWID)
            FieldANG = FieldDefn("angle", OFTReal)  # Create a floating property field：angle
            layer.CreateField(FieldANG)
            Defn = layer.GetLayerDefn()  # Get layer definition information
            features = []
            for cnt, length, width, angle in zip(self.cnts, self.length, self.width, self.angle):
                box = Geometry(wkbLinearRing)
                for point in cnt:
                    row = point[1]
                    col = point[0]
                    geox, geoy = self.pixel2geo(row, col, self.geotrans)
                    box.AddPoint(geox, geoy)  # Place the contour coordinates in a single polygon line ring
                box.CloseRings()  # Closed loop

                feature = Feature(Defn)
                length = length * self.resolution
                feature.SetField(0, length)
                width = width * self.resolution
                feature.SetField(1, width)
                feature.SetField(2, angle)
                feature.SetGeometry(box)
                features.append(feature)  # Add all features to the list

            for feature in features:
                layer.CreateFeature(feature)
            ds.Destroy()
            del feature
            messagebox.showinfo("Message", "The contour vector has been created！\n")

        if raster_path:
            drawContours(maskout, self.cnts, -1, (255, 255, 255), -1)
            self.writeTif(raster_path, maskout, self.geotrans, self.proj)
            messagebox.showinfo("Message", 'The Mask grid has been created!')

        self.root.destroy()


if __name__ == '__main__':
    input = inputImgVector()
    if input.flag:
        imgPath, vectorPath = input.flag
        contours, lengthlist, widthlist, anglelist = input.getCnts(vectorPath, imgPath)
        del_index = []
        mainWindow = Tk()
        mainWindow.state('zoomed')
        mainWindow.title('Edit and Zoom')
        frame = editAndzoom(mainWindow, imgPath, contours)
        mainWindow.columnconfigure(0, weight = 1)
        mainWindow.rowconfigure(0, weight = 1)
        mainWindow.mainloop()
        number = len(contours)
        if del_index:
            # Indirectly removes elements from a list based on the index without changing the original list index
            new_contours = [contours[i] for i in range(number) if (i not in _flatten(del_index))]
            new_lengthlist = [lengthlist[i] for i in range(number) if (i not in _flatten(del_index))]
            new_widthlist = [widthlist[i] for i in range(number) if (i not in _flatten(del_index))]
            new_anglelist = [anglelist[i] for i in range(number) if (i not in _flatten(del_index))]
        else:
            new_contours = contours
            new_lengthlist = lengthlist
            new_widthlist = widthlist
            new_anglelist = anglelist

        root = Tk()
        app = output(root, imgPath, new_contours, new_lengthlist, new_widthlist, new_anglelist)
        root.mainloop()
    else:
        root = Tk()
        root.withdraw()
        messagebox.showerror("Error", "Please enter the correct path!")

