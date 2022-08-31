# -*- coding: utf-8 -*-
# Input Image
import time
from math import ceil, log
from warnings import catch_warnings, simplefilter
from tkinter import ttk, filedialog, StringVar, Label, Entry, Button, Canvas, Scrollbar, TclError, Tk, Label, messagebox
from PIL import Image, ImageTk
from osgeo.gdal import Open, GDT_Byte, GDT_UInt16, GDT_CInt16, GDT_Float32, GDT_Float64, GetDriverByName
from cv2 import merge, fillPoly
from numpy import array, zeros, uint8
from rasterio import open as rasterOpen
from rasterio.windows import Window
import threading


class InputImage:
    def __init__(self, root):
        width = 300
        height = 200
        size_align = '%dx%d+%d+%d' % (
        width, height, (root.winfo_screenwidth() - width) / 2, (root.winfo_screenheight() - height) / 2)
        self.root = root
        self.root.geometry(size_align)
        self.root.title('Input remote sensing image...')
        # Creates the Label
        Label(self.root, text="image_path:").place(x = 27, y = 75)
        self.e_text = StringVar()
        Entry(self.root, width = 20, textvariable = self.e_text).place(x = 107, y = 75)

        Button(self.root, text = "...", command = self.select_image_path).place(x = 257, y = 71)
        Button(self.root, text = "Ok", command = self.output, activebackground = "pink", activeforeground = "blue").place(x = 40,
                                                                                                                  y = 150)
        Button(self.root, text = "Cancel", command = self.root.destroy, activebackground = "pink",
               activeforeground = "blue").place(x = 230, y = 150)

    def select_image_path(self):
        image_path = filedialog.askopenfilename(title='Select the remote sensing image...', initialdir=None,
                                                filetypes=[(
                                                    "image", ".tif"), ('All Files', ' *')], defaultextension='.tif')
        self.e_text.set(str(image_path))

    def output(self):
        global path
        path = self.e_text.get()
        self.root.destroy()


# Smart scroll bar: the scroll bar is displayed and available only when required
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


# custom_Clip function
class custom_Clip(ttk.Frame):
    """ Display and zoom image """

    def __init__(self, root, path):
        super().__init__()
        """ Initialize the ImageFrame """
        self.root = root
        self.id_pts = []
        self.pts = []
        self.path = path
        self.reduction = 2  # reduction degree of image pyramid
        # Decide if this image huge or not
        self.huge = False  # huge or not
        self.huge_size = 10000  # define size of the huge image
        self.tile_height = 1024  # width of the tile band
        Image.MAX_IMAGE_PIXELS = 1000000000  # suppress DecompressionBombError for big image
        self.curr_img = 0  # current image from the pyramid

        self.scale = 1.0
        self.imscale = 1.0  # the scale for the canvas image zoom
        self.delta = 1.1  # zoom magnitude
        self.previous_state = 0  # Initialize the keyboard state
        self.interpolation_function = Image.ANTIALIAS  # could be: NEAREST, BILINEAR, BICUBIC and ANTIALIAS
        self.grid(row=0, column = 0, sticky = 'nswe')
        self.grid_rowconfigure(0, weight = 1)
        self.grid_columnconfigure(0, weight = 1)
        # Vertical and horizontal scrollbars for canvas
        hbar = CreateScrollbar(self, orient = 'horizontal')
        vbar = CreateScrollbar(self, orient = 'vertical')
        hbar.grid(row=1, column=0, sticky = 'we')
        vbar.grid(row=0, column=1, sticky = 'ns')
        # Create a message prompt label
        self.var_text = StringVar()
        Label(self.root, textvariable = self.var_text, fg = 'green', font = ("黑体", 30)).grid(row = 2, sticky = 'w')

        # Create canvas and bind it with scrollbars. Public for outer classes
        self.canvas = Canvas(self, highlightthickness=0,
                             xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        with catch_warnings():
            simplefilter('ignore')
            ds = rasterOpen(self.path)
            gdal_ds = Open(self.path)
            self.geotrans, self.proj = gdal_ds.GetGeoTransform(), gdal_ds.GetProjection()
            del gdal_ds
            self.imheight, self.imwidth = ds.height, ds.width

        # Put image into container rectangle and use it to set proper coordinates to the image
        self.container = self.canvas.create_rectangle((0, 0, self.imwidth, self.imheight), width = 0)

        self.canvas.grid(row=0, column=0, sticky='nswe')

        self.update()

        hbar.configure(command = self.scroll_x)  # bind scrollbars to the canvas
        vbar.configure(command = self.scroll_y)
        # Bind events to the Canvas
        self.canvas.bind('<Configure>', lambda event: self.show())  # canvas is resized
        self.canvas.bind('<ButtonPress-2>', self.move_start)  # remember canvas position
        self.canvas.bind('<B2-Motion>', self.move_to)  # move canvas to the new position
        self.canvas.bind('<MouseWheel>', self.zoom)  # zoom image
        self.canvas.bind("<ButtonPress-1>", self.left_click)
        self.canvas.bind("<ButtonRelease-1>", self.left_release)
        self.canvas.bind("<ButtonPress-3>", self.right_click)
        self.canvas.bind("<Control-z>", self.undo)
        self.canvas.bind('<KeyPress-q>', self.quit)

        # Handle keystrokes in idle mode, because program slows down on a weak computers,
        # when too many key stroke events in the same time
        self.canvas.bind('<Key>', lambda event: self.canvas.after_idle(self.keystroke, event))

        if self.imwidth * self.imheight > self.huge_size * self.huge_size:
            self.huge = True  # image is huge

        self.minlength = min(self.imwidth, self.imheight)  # get the fixed_size image side

        # Store images in fixed memory
        messagebox.showinfo("Promt", "please wait a moment for creating the image pyramids!")
        if self.huge:
            self.pyramid = [self.fixed_size()]
        else:
            img = ds.read()
            r = img[0]
            g = img[1]
            b = img[2]
            img = merge([r, g, b])
            self.pyramid = [Image.fromarray(img)]

        # Create image pyramid
        # Set ratio coefficient for image pyramid
        self.ratio = max(self.imwidth, self.imheight) / self.huge_size if self.huge else 1.0
        self.var_text.set("Promt: Start creating the image pyramid!")
        self.scale = self.imscale * self.ratio  # image pyramide scale

        (w, h), m, j = self.pyramid[-1].size, 512, 0

        n = ceil(log(min(w, h) / m, self.reduction)) + 1  # image pyramid length

        while w > m and h > m:  # top pyramid image is around 512 pixels in size
            j += 1
            w /= self.reduction  # divide on reduction degree
            h /= self.reduction  # divide on reduction degree
            self.pyramid.append(self.pyramid[-1].resize((int(w + 0.5), int(h + 0.5)), self.interpolation_function))
        self.var_text.set('Prompt: Creating {0}-layer image pyramids successfully!'.format(n))
        self.canvas.lower(self.container)
        self.show()  # show image on the canvas
        # Sets focus for the canvas in response to keyboard keystroke events
        self.canvas.focus_set()

    def left_click(self, event):
        # Save mouse click position coordinates
        x, y = self.getcanvasxy(event)
        self.pts.append(x)
        self.pts.append(y)

    def writeTif(self, path, img, im_geotrans, im_proj, nodata=None):
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
        gTiffDriver = GetDriverByName("GTiff")
        ds = gTiffDriver.Create(path, im_width, im_height, im_bands, dtype, options=["COMPRESS=LZW", "BIGTIFF=YES"])
        if (ds != None):
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
        else:
            self.var_text.set('Promt: Failed to create dataset when exporting tif image')
        del gTiffDriver
        del ds

    def left_release(self, event):
        if len(self.pts) < 2:
            pass
        elif len(self.pts) < 4:
            self.id_pts = self.canvas.create_oval(self.pts[0], self.pts[1], self.pts[0], self.pts[1], outline='red',
                                                  fill='red')
        else:
            allid = list(self.canvas.find('all'))
            allid.remove(self.bg_id)
            allid.remove(self.container)
            if allid:
                for singleid in allid:
                    self.canvas.delete(singleid)
            self.id_pts = self.canvas.create_line(self.pts, fill='red')

    def undo(self, event):
        if len(self.pts) < 2:
            self.var_text.set('Prompt: There are no dots on the image. It can not be undone！')
        elif len(self.pts) < 4:
            self.pts.pop()
            self.pts.pop()
            allid = list(self.canvas.find('all'))
            allid.remove(self.bg_id)
            allid.remove(self.container)
            if allid:
                for singleid in allid:
                    self.canvas.delete(singleid)
        else:
            self.pts.pop()
            self.pts.pop()
            if len(self.pts) < 4:
                allid = list(self.canvas.find('all'))
                allid.remove(self.bg_id)
                allid.remove(self.container)
                if allid:
                    for singleid in allid:
                        self.canvas.delete(singleid)
                self.id_pts = self.canvas.create_oval(self.pts[0], self.pts[1], self.pts[0], self.pts[1], outline = 'red',
                                                      fill = 'red')
            else:
                # advoid deleting the range indicating container and the background image
                allid = list(self.canvas.find('all'))
                allid.remove(self.bg_id)
                allid.remove(self.container)
                if allid:
                    for singleid in allid:
                        self.canvas.delete(singleid)
                self.id_pts = self.canvas.create_line(self.pts, fill = 'red')

    def right_click(self, event):
        box_image = self.canvas.coords(self.container)  # get image area
        reference_startx = box_image[0]
        reference_starty = box_image[1]
        if len(self.pts) <= 4:
            self.var_text.set(
                "Promt: You selected less than two points on the image, so it couldn't customly crop the image!")
        else:
            self.var_text.set("\nPromt: Select the file output path...")
            outpath = filedialog.asksaveasfilename(title = 'Select the output path...', initialdir = None, filetypes = [(
                "image", ".tif"), ('All Files', ' *')], defaultextension = '.tif')
            self.var_text.set("Promt: Clipping is under way!")
            # delete the line on the canvas
            allid = list(self.canvas.find('all'))
            # advoid deleting the reference extent container and the background image
            allid.remove(self.container)
            allid.remove(self.bg_id)
            if allid:
                for singleid in allid:
                    self.canvas.delete(singleid)
            new_points = []
            X = [int((self.pts[i] - reference_startx) / self.imscale) for i in range(len(self.pts)) if (i % 2 == 0)]
            Y = [int((self.pts[i] - reference_starty) / self.imscale) for i in range(len(self.pts)) if (i % 2 != 0)]

            self.pts.clear()

            # The maximum and minimum pixel coordinates of x and y
            X_max = max(X)
            Y_max = max(Y)
            X_min = min(X)
            Y_min = min(Y)
            # Get the x, y geographical coordinates in the upper left corner of the image, east-west resolution, and north-south resolution
            geox, geoy, pix_W, pix_H = self.geotrans[0], self.geotrans[3], self.geotrans[1], self.geotrans[5]

            # calculate the maximum and minimum geographical coordinates of x and y
            minx = X_min * pix_W + geox
            maxy = Y_min * pix_H + geoy

            # Create a new Geomatrix object for the image to attach geo-referenced data  
            new_geoT = list(self.geotrans)
            new_geoT[0] = minx
            new_geoT[3] = maxy
            # Read image blocks according to clipping extent
            ds = rasterOpen(self.path)
            img = ds.read(window=Window(X_min, Y_min, X_max - X_min + 1, Y_max - Y_min + 1))
            del ds
            r = img[0]
            g = img[1]
            b = img[2]
            img = merge([r, g, b])
            img_new = Image.fromarray(img)  # acquire image 
            del img
            # The ROI mask for the delineation
            mask = zeros((img_new.size[1], img_new.size[0], 3), uint8)
            for x, y in zip(X, Y):
                new_points.append([x - X_min, y - Y_min])
            mask = fillPoly(mask, [array(new_points)], (255, 255, 255))
            output = array(img_new)
            output[mask != 255] = 0
            new_proj = self.proj
            try:
                self.writeTif(outpath, output, new_geoT, new_proj, 0)
            except Exception as e:
                self.var_text.set("Error: " + e)
        self.var_text.set("Promt: Clipping is done!")

    def quit(self, event):
        self.root.destroy()

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
            img = ds.read(window=Window(0, i, self.imwidth, band))
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
        # calculate the coordinate range of visible area
        x1 = max(box_canvas[0] - box_image[0], 0)
        y1 = max(box_canvas[1] - box_image[1], 0)
        x2 = min(box_canvas[2], box_image[2]) - box_image[0]
        y2 = min(box_canvas[3], box_image[3]) - box_image[1]
        if self.huge and self.curr_img < 0:  # show huge image, which does not fit in RAM
            h = int((y2 - y1) / self.imscale)  # height of the tile band
            w = int((x2 - x1) / self.imscale)  # width of the tile band
            ds = rasterOpen(self.path)
            img = ds.read(window=Window(int(x1 / self.imscale + 0.5), int(y1 / self.imscale + 0.5),
                                        int(w + 0.5), int(h + 0.5)))
            del ds
            r = img[0]
            g = img[1]
            b = img[2]
            img = merge([r, g, b])
            image = Image.fromarray(img)  # acquire image
            del img
        else:
            # crop current img from pyramid
            image = self.pyramid[max(0, self.curr_img)].crop((int(x1 / self.scale + 0.5), int(y1 / self.scale + 0.5),
                                                              int(x2 / self.scale + 0.5), int(y2 / self.scale + 0.5)))

        imagetk = ImageTk.PhotoImage(
            image.resize((int(x2 - x1 + 0.5), int(y2 - y1 + 0.5)), self.interpolation_function))

        self.bg_id = self.canvas.create_image(max(box_canvas[0], box_image[0]),
                                              max(box_canvas[1], box_image[1]), anchor='nw', image=imagetk)

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
        #         print(self.curr_img)
        self.scale = k * pow(self.reduction, max(0, self.curr_img))
        #         print(k,self.scale)
        self.canvas.scale('all', x, y, scale, scale)  # zoom all object
        self.show()
        if self.id_pts:
            if len(self.pts) == 2:
                temp_pts = self.canvas.coords(self.id_pts)
                self.pts = [(temp_pts[0] + temp_pts[2]) / 2.0, (temp_pts[1] + temp_pts[3]) / 2.0]
            else:
                self.pts = self.canvas.coords(self.id_pts)

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


if __name__ == "__main__":
    path = None
    root = Tk()  # Create an instance of tkinter.Tk
    app = InputImage(root)
    root.mainloop()
    if path == None:
        root = Tk()
        root.withdraw()  # Realize the main window hide
        messagebox.showerror("Error",
                             "There was a problem with the image path and the image dataset could not be read successfully!")
        root.destroy()
        root.mainloop()
    else:
        mainWindow = Tk()
        mainWindow.state('zoomed')
        mainWindow.title('Zoom and clipping')
        frame = custom_Clip(mainWindow, path)
        mainWindow.columnconfigure(0, weight=1)
        mainWindow.rowconfigure(0, weight=1)
        mainWindow.mainloop()
