from tkinter import ttk, TclError, Scrollbar, Label, Scale, Tk, Entry, Button, filedialog, StringVar, Canvas, \
    messagebox, simpledialog
from PIL import Image, ImageTk
from math import ceil, log
from warnings import catch_warnings, simplefilter
from rasterio import open as rasterOpen
from rasterio.windows import Window
from cv2 import merge, cvtColor, inRange, findContours, drawContours, threshold, COLOR_RGB2HSV, RETR_EXTERNAL, \
    THRESH_BINARY, CHAIN_APPROX_NONE, dilate, minAreaRect, arcLength, contourArea, fillPoly
from numpy import array, ones, uint8, mean, std, zeros_like, append, zeros
from osgeo.gdal import Open, GDT_Byte, GDT_UInt16, GDT_CInt16, GDT_Float32, GDT_Float64, SetConfigOption
from osgeo.gdal import GetDriverByName as gdalGetDriverByName
from osgeo.osr import SpatialReference
from osgeo.ogr import UseExceptions, FieldDefn, Geometry, wkbLinearRing, OFTReal, Feature, wkbLineString
from osgeo.ogr import GetDriverByName as ogrGetDriverByName
from os import path as ospath
from time import time


class InputImage:
    def __init__(self, root):
        width = 300
        height = 200
        self.root = root
        size_align = '%dx%d+%d+%d' % (
            width, height, (self.root.winfo_screenwidth() - width) / 2, (self.root.winfo_screenheight() - height) / 2)
        self.root.geometry(size_align)
        self.root.title('Input remote sensing image...')
        # Creates the Label
        Label(self.root, text="image_path:").place(x=27, y=75)
        self.e_text = StringVar()
        Entry(self.root, width=20, textvariable=self.e_text).place(x=107, y=75)

        Button(self.root, text="...", command=self.select_image_path).place(x=257, y=71)
        Button(self.root, text="Ok", command=self.output, activebackground="pink", activeforeground="blue").place(
            x=40, y=150)
        Button(self.root, text="Cancel", command=self.root.destroy, activebackground="pink",
               activeforeground="blue").place(x=230, y=150)

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


class ImageSegmentation(ttk.Frame):
    """ Display and zoom image """

    def __init__(self, root, path):
        super().__init__()
        """ Initialize the ImageFrame """
        global lower
        global upper
        self.pyramid = []
        # Decide if this image huge or not
        self.tile_height = 1024
        self.root = root
        self.reduction = 4  # reduction degree of image pyramid
        self.huge = False  # huge or not
        self.huge_size = 14000  # define size of the huge image
        Image.MAX_IMAGE_PIXELS = 1000000000  # suppress DecompressionBombError for big image
        self.curr_img = -1  # current image from the pyramid

        self.path = path
        self.scale = 1.0
        self.imscale = 1.0  # the scale for the canvas image zoom
        self.delta = 1.1  # zoom magnitude
        self.previous_state = 0  # Initialize the keyboard state
        self.interpolation_function = Image.ANTIALIAS  # could be: NEAREST, BILINEAR, BICUBIC and ANTIALIAS
        self.grid(row=0, column=0, sticky='nswe')
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        # Vertical and horizontal scrollbars for canvas
        hbar = CreateScrollbar(self, orient='horizontal')
        vbar = CreateScrollbar(self, orient='vertical')
        hbar.grid(row=1, column=0, sticky='we')
        vbar.grid(row=0, column=1, sticky='ns')
        # Create canvas and bind it with scrollbars. Public for outer classes
        self.canvas = Canvas(self, highlightthickness=0,
                             xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        with catch_warnings():
            simplefilter('ignore')
            ds = rasterOpen(self.path)
            self.imheight, self.imwidth = ds.height, ds.width
            del ds
        # Put image into container rectangle and use it to set proper coordinates to the image
        self.container = self.canvas.create_rectangle((0, 0, self.imwidth, self.imheight), width=0)

        self.canvas.grid(row=0, column=0, sticky='nswe')

        Label(self, text='h_min : ').grid(row=2, sticky='sw')
        self.h_min = Scale(self, command=self.change_img, orient='horizontal', from_=0, to=180,
                           length=self.winfo_screenwidth() - 70,
                           resolution=1)
        self.h_min.grid(row=2, sticky='e')

        Label(self, text='h_max : ').grid(row=3, sticky='sw')
        self.h_max = Scale(self, command=self.change_img, orient='horizontal', from_=0, to=180,
                           length=self.winfo_screenwidth() - 70,
                           resolution=1)
        self.h_max.grid(row=3, sticky='e')
        Label(self, text='s_min : ').grid(row=4, sticky='sw')
        self.s_min = Scale(self, command=self.change_img, orient='horizontal', from_=0, to=255,
                           length=self.winfo_screenwidth() - 70,
                           resolution=1)
        self.s_min.grid(row=4, sticky='e')

        Label(self, text='s_max : ').grid(row=5, sticky='sw')
        self.s_max = Scale(self, command=self.change_img, orient='horizontal', from_=0, to=255,
                           length=self.winfo_screenwidth() - 70,
                           resolution=1)
        self.s_max.grid(row=5, sticky='e')

        Label(self, text='v_min : ').grid(row=6, sticky='sw')
        self.v_min = Scale(self, command=self.change_img, orient='horizontal', from_=0, to=255,
                           length=self.winfo_screenwidth() - 70,
                           resolution=1)
        self.v_min.grid(row=6, sticky='e')

        Label(self, text='v_max : ').grid(row=7, sticky='sw')
        self.v_max = Scale(self, command=self.change_img, orient='horizontal', from_=0, to=255,
                           length=self.winfo_screenwidth() - 70,
                           resolution=1)
        self.v_max.grid(row=7, sticky='e')
        # Create a message prompt label
        self.var_text = StringVar()
        Label(self.root, textvariable=self.var_text, fg='green', font=("黑体", 20)).grid(row=8, sticky='w')
        self.update()

        hbar.configure(command=self.scroll_x)  # bind scrollbars to the canvas
        vbar.configure(command=self.scroll_y)
        # Bind events to the Canvas
        self.canvas.bind('<Configure>', lambda event: self.show())  # canvas is resized
        self.canvas.bind('<ButtonPress-2>', self.move_start)  # remember canvas position
        self.canvas.bind('<B2-Motion>', self.move_to)  # move canvas to the new position
        self.canvas.bind('<MouseWheel>', self.zoom)  # zoom image
        self.canvas.bind('<KeyPress-q>', self.quit)

        # Handle keystrokes in idle mode, because program slows down on a weak computers,
        # when too many key stroke events in the same time
        self.canvas.bind('<Key>', lambda event: self.canvas.after_idle(self.keystroke, event))

        if self.imwidth * self.imheight > self.huge_size * self.huge_size:
            self.huge = True  # image is huge

        # Set ratio coefficient for image pyramid
        self.ratio = max(self.imwidth, self.imheight) / self.huge_size if self.huge else 1.0

        self.h_max.set(34)
        self.s_max.set(255)
        self.v_max.set(85)
        lower = array([self.h_min.get(), self.s_min.get(), self.v_min.get()])
        upper = array([self.h_max.get(), self.s_max.get(), self.v_max.get()])
        self.scale = self.imscale * self.ratio  # image pyramide scale
        self.minlength = min(self.imwidth, self.imheight)  # get the fixed_size image side
        if self.huge:
            self.pyramid = [self.fixed_size()]
        else:
            ds = rasterOpen(self.path)
            self.pyramid = ds.read()
            r = self.pyramid[0]
            g = self.pyramid[1]
            b = self.pyramid[2]
            self.pyramid = merge([r, g, b])
            del r, g, b
            roiHSV = cvtColor(self.pyramid, COLOR_RGB2HSV)
            mask = inRange(roiHSV, lower, upper)
            del roiHSV
            _, thres_mask = threshold(mask, 0, 255, THRESH_BINARY)
            del mask
            contours, _ = findContours(thres_mask, RETR_EXTERNAL, CHAIN_APPROX_NONE)
            drawContours(self.pyramid, contours, -1, (255, 0, 0), thickness=1)
            self.pyramid = [Image.fromarray(self.pyramid)]
        self.var_text.set("Promt: Start creating the image pyramid!")
        # Create image pyramid
        (w, h), m, j = self.pyramid[-1].size, 512, 0

        n = ceil(log(min(w, h) / m, self.reduction)) + 1  # image pyramid length

        while w > m and h > m:  # top pyramid image is around 512 pixels in size
            j += 1
            w /= self.reduction  # divide on reduction degree
            h /= self.reduction  # divide on reduction degree
            self.pyramid.append(self.pyramid[-1].resize((int(w + 0.5), int(h + 0.5)), self.interpolation_function))
        self.var_text.set('Promt: Creating {0}-layer image pyramids successfully!'.format(n))
        self.canvas.lower(self.container)
        # Sets focus for the canvas in response to keyboard keystroke events
        self.canvas.focus_set()

    def quit(self, event):
        self.root.destroy()

    def change_img(self, event):
        global lower
        global upper
        # Update segmentation results in real time
        lower = array([self.h_min.get(), self.s_min.get(), self.v_min.get()])
        upper = array([self.h_max.get(), self.s_max.get(), self.v_max.get()])
        self.var_text.set("Prompt: The threshold value has changed!")
        if self.curr_img <= 0:
            self.show()
        else:
            if self.huge:
                self.pyramid = [self.fixed_size()]
            else:
                ds = rasterOpen(self.path)
                self.pyramid = ds.read()
                r = self.pyramid[0]
                g = self.pyramid[1]
                b = self.pyramid[2]
                self.pyramid = merge([r, g, b])
                del r, g, b
                roiHSV = cvtColor(self.pyramid, COLOR_RGB2HSV)
                mask = inRange(roiHSV, lower, upper)
                del roiHSV
                _, thres_mask = threshold(mask, 0, 255, THRESH_BINARY)
                del mask
                contours, _ = findContours(thres_mask, RETR_EXTERNAL, CHAIN_APPROX_NONE)
                drawContours(self.pyramid, contours, -1, (255, 0, 0), thickness=1)
                self.pyramid = [Image.fromarray(self.pyramid)]
            # Create image pyramid

            (w, h), m, j = self.pyramid[-1].size, 512, 0

            n = ceil(log(min(w, h) / m, self.reduction)) + 1  # image pyramid length

            while w > m and h > m:  # top pyramid image is around 512 pixels in size
                j += 1
                w /= self.reduction  # divide on reduction degree
                h /= self.reduction  # divide on reduction degree
                self.pyramid.append(self.pyramid[-1].resize((int(w + 0.5), int(h + 0.5)), self.interpolation_function))
                self.show()

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
        lower = array([self.h_min.get(), self.s_min.get(), self.v_min.get()])
        upper = array([self.h_max.get(), self.s_max.get(), self.v_max.get()])
        i, j, n = 0, 0, ceil(self.imheight / self.tile_height)

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
            roiHSV = cvtColor(img, COLOR_RGB2HSV)
            mask = inRange(roiHSV, lower, upper)
            _, thres = threshold(mask, 0, 255, THRESH_BINARY)
            contours, _ = findContours(thres, RETR_EXTERNAL, CHAIN_APPROX_NONE)
            drawContours(img, contours, -1, (255, 0, 0), thickness=1)
            img[-1] = img[-2]
            img[0] = img[1]
            img = Image.fromarray(img)  # acquire image 
            image.paste(img.resize((w, int(band * k) + 1), Image.ANTIALIAS), (0, int(i * k)))
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
        ds = rasterOpen(self.path)
        if self.curr_img <= 0:  # show huge image, which does not fit in RAM
            h = int((y2 - y1) / self.imscale)  # height of the tile band
            w = int((x2 - x1) / self.imscale)  # width of the tile band
            img = ds.read(window=Window(int(x1 / self.imscale + 0.5), int(y1 / self.imscale + 0.5),
                                        int(w + 0.5), int(h + 0.5)))
            r = img[0]
            g = img[1]
            b = img[2]
            img = merge([r, g, b])
            roiHSV = cvtColor(img, COLOR_RGB2HSV)
            # Update segmentation results in real time
            lower = array([self.h_min.get(), self.s_min.get(), self.v_min.get()])
            upper = array([self.h_max.get(), self.s_max.get(), self.v_max.get()])
            mask = inRange(roiHSV, lower, upper)
            del roiHSV
            _, thres_mask = threshold(mask, 0, 255, THRESH_BINARY)
            del mask
            contours, _ = findContours(thres_mask, RETR_EXTERNAL, CHAIN_APPROX_NONE)
            drawContours(img, contours, -1, (255, 0, 0), thickness=1)
            img = Image.fromarray(img)  # acquire image
        else:
            # crop current img from pyramid
            img = self.pyramid[max(0, self.curr_img)].crop((int(x1 / self.scale + 0.5), int(y1 / self.scale + 0.5),
                                                            int(x2 / self.scale + 0.5), int(y2 / self.scale + 0.5)))

        image = img.resize((int(x2 - x1 + 1), int(y2 - y1 + 1)), self.interpolation_function)
        imagetk = ImageTk.PhotoImage(image)
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
            if float(min(self.canvas.winfo_width(),
                         self.canvas.winfo_height())) < 1: return  # The minimum side length of the visible region is greater than 1 pixel
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


def preprocessing(mask, image, kernel_size=None):
    start = time()
    _, thresh = threshold(mask, 0, 255, THRESH_BINARY)  # binaryzation
    if kernel_size != None:  # The expansion method in mathematical morphology is used to expand the segmentation results
        kernel = ones((kernel_size, kernel_size), uint8)
        dilation = dilate(thresh, kernel, iterations=1)
        contours, _ = findContours(dilation, RETR_EXTERNAL, CHAIN_APPROX_NONE)
    else:
        contours, _ = findContours(thresh, RETR_EXTERNAL, CHAIN_APPROX_NONE)

    # Initialize empty list
    stdlist = []
    hwlist = []
    meanlist = []
    perimeterlist = []
    rotatedRectlist = []
    lengthlist = []
    widthlist = []
    anglelist = []
    new_contours = []
    for i in range(len(contours)):
        contour = contours[i]
        rect = minAreaRect(
            contour)  # Return: output as a tuple ((x,y),(w,h),anlge) ;(x,y) is center coordinates  of the smallest
        # enclosing rectangle; (w,h) are width and height,respectively;Angle is the rotation anlge.

        area = contourArea(contour)  # Return: the area enclosed by the contour
        perimeter = arcLength(contour, True)  # Return: the perimeter of the contour
        w, h = rect[1][0], rect[1][1]
        if h == 0 or w == 0 or area == 0 or perimeter == 0:
            pass
        else:
            length = max(w, h)
            width = min(w, h)
            hratiow = 1000 * length / width  # the aspect ratio of the smallest enclosing rectangle * 1000

            theta = rect[2]

            # opencv 4.5
            if w > h:
                theta = 180 - theta
            else:
                theta = 90 - theta
            '''
            # Versions prior to opencv 4.5
            if w > h:
                theta = 180 - theta
            else:
                theta = theta
            '''

            # Create a mask image that contains the contour filled in
            cimg = zeros_like(mask, uint8)
            fillPoly(cimg, [contour], 1)
            # Access the image pixels
            pts = image[cimg == 1]
            std_cal = std(pts)
            std_cal = std_cal * 10  # the spectral Standard Deviation of the object surrounded by the contour * 10
            mean_cal = mean(pts)
            mean_cal = mean_cal * 10  # the spectral Mean of the object surrounded by the contour * 10
            stdlist.append(std_cal)
            hwlist.append(hratiow)
            meanlist.append(mean_cal)
            rotatedRectlist.append(rect)
            perimeterlist.append(perimeter)
            lengthlist.append(length)
            widthlist.append(width)
            anglelist.append(theta)
            new_contours.append(contour)
    end = time()
    root = Tk()
    root.withdraw()  # Realize the main window hide
    messagebox.showinfo("Message", "The pretreatment process took {0} minutes".format(round(((end - start) / 60), 2)))
    root.destroy()
    root.mainloop()

    return [stdlist, meanlist, hwlist, perimeterlist, new_contours, rotatedRectlist, lengthlist, widthlist, anglelist]


class fine_extract(ttk.Frame):
    """ Display and zoom image """

    def __init__(self, root, path, mean_max, hw_max, std_max, peri_max, stdlist, meanlist, hwlist, perimeterlist,
                 contours, lengthlist, widthlist, anglelist):
        super().__init__()
        """ Initialize the ImageFrame """
        self.root = root
        self.path = path
        self.change = False
        self.tile_height = 1024
        self.stdlist, self.meanlist, self.hwlist, self.perimeterlist = stdlist, meanlist, hwlist, perimeterlist
        self.contours, self.lengthlist, self.widthlist, self.anglelist = contours, lengthlist, widthlist, anglelist
        # Decide if this image huge or not
        self.reduction = 2  # reduction degree of image pyramid
        self.huge = False  # huge or not
        self.huge_size = 10000  # define size of the huge image
        Image.MAX_IMAGE_PIXELS = 1000000000  # suppress DecompressionBombError for big image
        self.curr_img = -1  # current image from the pyramid

        self.path = path
        self.scale = 1.0
        self.imscale = 1.0  # the scale for the canvas image zoom
        self.delta = 1.1  # zoom magnitude
        self.previous_state = 0  # Initialize the keyboard state
        self.interpolation_function = Image.ANTIALIAS  # could be: NEAREST, BILINEAR, BICUBIC and ANTIALIAS
        self.grid(row=0, column=0, sticky='nswe')
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        # Vertical and horizontal scrollbars for canvas
        hbar = CreateScrollbar(self, orient='horizontal')
        vbar = CreateScrollbar(self, orient='vertical')
        hbar.grid(row=1, column=0, sticky='we')
        vbar.grid(row=0, column=1, sticky='ns')
        # Create canvas and bind it with scrollbars. Public for outer classes
        self.canvas = Canvas(self, highlightthickness=0,
                             xscrollcommand=hbar.set, yscrollcommand=vbar.set)

        self.canvas.grid(row=0, column=0, sticky='nswe')

        Label(self, text='std_min:').grid(row=2, sticky='sw')
        self.std_min = Scale(self, command=self.change_img, orient='horizontal', from_=-1, to=std_max,
                             length=self.winfo_screenwidth() - 70
                             , resolution=1)
        self.std_min.grid(row=2, sticky='e')

        Label(self, text='std_max:').grid(row=3, sticky='sw')
        self.std_max = Scale(self, command=self.change_img, orient='horizontal', from_=-1, to=std_max,
                             length=self.winfo_screenwidth() - 70
                             , resolution=1)
        self.std_max.grid(row=3, sticky='e')

        Label(self, text='mean_min:').grid(row=4, sticky='sw')
        self.mean_min = Scale(self, command=self.change_img, orient='horizontal', from_=-1, to=mean_max,
                              length=self.winfo_screenwidth() - 70
                              , resolution=1)
        self.mean_min.grid(row=4, sticky='e')

        Label(self, text='mean_max:').grid(row=5, sticky='sw')
        self.mean_max = Scale(self, command=self.change_img, orient='horizontal', from_=-1, to=mean_max,
                              length=self.winfo_screenwidth() - 70
                              , resolution=1)
        self.mean_max.grid(row=5, sticky='e')

        Label(self, text='hw_min:').grid(row=6, sticky='sw')
        self.hw_min = Scale(self, command=self.change_img, orient='horizontal', from_=-1, to=hw_max,
                            length=self.winfo_screenwidth() - 79
                            , resolution=1)
        self.hw_min.grid(row=6, sticky='e')

        Label(self, text='hw_max:').grid(row=7, sticky='sw')
        self.hw_max = Scale(self, command=self.change_img, orient='horizontal', from_=-1, to=hw_max,
                            length=self.winfo_screenwidth() - 79
                            , resolution=1)
        self.hw_max.grid(row=7, sticky='e')

        Label(self, text='peri_min:').grid(row=8, sticky='sw')
        self.peri_min = Scale(self, command=self.change_img, orient='horizontal', from_=-1, to=peri_max,
                              length=self.winfo_screenwidth() - 79
                              , resolution=1)
        self.peri_min.grid(row=8, sticky='e')

        Label(self, text='peri_max:').grid(row=9, sticky='sw')
        self.peri_max = Scale(self, command=self.change_img, orient='horizontal', from_=-1, to=peri_max,
                              length=self.winfo_screenwidth() - 79
                              , resolution=1)
        self.peri_max.grid(row=9, sticky='e')
        # Create a message prompt label
        self.var_text = StringVar()
        Label(self.root, textvariable=self.var_text, fg='green', font=("黑体", 20)).grid(row=10, sticky='w')

        self.update()

        hbar.configure(command=self.scroll_x)  # bind scrollbars to the canvas
        vbar.configure(command=self.scroll_y)
        # Bind events to the Canvas
        self.canvas.bind('<Configure>', lambda event: self.show())  # canvas is resized
        self.canvas.bind('<ButtonPress-2>', self.move_start)  # remember canvas position
        self.canvas.bind('<B2-Motion>', self.move_to)  # move canvas to the new position
        self.canvas.bind('<MouseWheel>', self.zoom)  # zoom image
        self.canvas.bind('<KeyPress-q>', lambda event: self.myquit())
        self.root.protocol('WM_DELETE_WINDOW', self.myquit)
        # Handle keystrokes in idle mode, because program slows down on a weak computers,
        # when too many key stroke events in the same time
        self.canvas.bind('<Key>', lambda event: self.canvas.after_idle(self.keystroke, event))
        #######################################################################################
        #######################################################################################

        with catch_warnings():  # suppress DecompressionBombWarning for big image
            simplefilter('ignore')
            ds = rasterOpen(self.path)
            gdal_ds = Open(self.path)
            self.geotrans, self.proj = gdal_ds.GetGeoTransform(), gdal_ds.GetProjection()
            del gdal_ds
            self.imheight, self.imwidth = ds.height, ds.width

        # Put image into container rectangle and use it to set proper coordinates to the image
        self.container = self.canvas.create_rectangle((0, 0, self.imwidth, self.imheight), width=0)

        if self.imwidth * self.imheight > self.huge_size * self.huge_size:
            self.huge = True  # image is huge

        self.minlength = min(self.imwidth, self.imheight)  # get the fixed_size image side

        # Store images in fixed memory
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

        self.scale = self.imscale * self.ratio  # image pyramide scale
        self.var_text.set("Promt: Start creating the image pyramid!")
        (w, h), m, j = self.pyramid[-1].size, 512, 0

        n = ceil(log(min(w, h) / m, self.reduction)) + 1  # image pyramid length

        while w > m and h > m:  # top pyramid image is around 512 pixels in size
            j += 1
            w /= self.reduction  # divide on reduction degree
            h /= self.reduction  # divide on reduction degree
            self.pyramid.append(self.pyramid[-1].resize((int(w + 0.5), int(h + 0.5)), self.interpolation_function))
        self.var_text.set("Promt: Creating {0}-layer image pyramids successfully!".format(n))
        self.std_min.set(180)
        self.std_max.set(std_max)
        self.mean_max.set(mean_max)
        self.hw_min.set(1000)
        self.hw_max.set(hw_max)
        self.peri_max.set(peri_max)

        self.canvas.lower(self.container)
        # Sets focus for the canvas in response to keyboard keystroke events
        self.canvas.focus_set()

    def save_fineExt(self):
        width = 500
        height = 400
        self.root = Tk()
        size_align = '%dx%d+%d+%d' % (
            width, height, (self.root.winfo_screenwidth() - width) / 2, (self.root.winfo_screenheight() - height) / 2)
        ds = rasterOpen(self.path)
        self.image = ds.read()
        r = self.image[0]
        g = self.image[1]
        b = self.image[2]
        self.image = merge([r, g, b])
        del r, g, b
        gdal_ds = Open(self.path)
        self.geotrans, self.proj = gdal_ds.GetGeoTransform(), gdal_ds.GetProjection()
        self.imheight, self.imwidth = ds.height, ds.width
        del gdal_ds, ds
        self.cnts, self.resolution, self.length, self.width, self.angle = self.new_contours, self.geotrans[
            1], self.new_lengthlist, self.new_widthlist, self.new_anglelist
        self.root.geometry(size_align)
        self.root.title('Save the result...')
        # Creates the first Label Label
        Label(self.root, text="vector_path").place(x=100, y=100)
        # Creates the second Label Label
        Label(self.root, text="raster_path").place(x=100, y=200)
        self.e1_text = StringVar()
        self.e2_text = StringVar()
        Entry(self.root, width=20, textvariable=self.e1_text).place(x=180, y=100)
        Entry(self.root, width=20, textvariable=self.e2_text).place(x=180, y=200)

        Button(self.root, text="...", command=self.select_vector_path).place(x=330, y=96)
        Button(self.root, text="...", command=self.select_raster_path).place(x=330, y=196)
        Button(self.root, text="Save", command=self.output, activebackground="pink",
               activeforeground="blue").place(x=145, y=300)
        Button(self.root, text="Cancel", command=self.root.destroy, activebackground="pink",
               activeforeground="blue").place(x=290, y=300)

    def select_vector_path(self):
        save_file = filedialog.asksaveasfilename(title='Select the file storage path...', initialdir=None,
                                                 filetypes=[(
                                                     "vector", ".shp"), ('All Files', ' *')], defaultextension='.shp')
        self.e1_text.set(str(save_file))

    def select_raster_path(self):
        save_file = filedialog.asksaveasfilename(title='Select the file storage path...', initialdir=None,
                                                 filetypes=[(
                                                     "raster", ".tif"), ('All Files', ' *')], defaultextension='.tif')
        self.e2_text.set(str(save_file))

    def pixel2geo(self, row, col, geoTrans):
        geox = geoTrans[0] + geoTrans[1] * col + geoTrans[2] * row
        geoy = geoTrans[3] + geoTrans[4] * col + geoTrans[5] * row
        return geox, geoy

    def output(self):
        self.root.destroy()
        vector_path = self.e1_text.get()
        raster_path = self.e2_text.get()
        if vector_path or raster_path:
            pass
        else:
            messagebox.showinfo("Prompt", "Please input the paths correctly!")
            return
        if vector_path:
            UseExceptions()
            SetConfigOption("GDAL_FILENAME_IS_UTF8", "NO")  # In order to support the Chinese path
            SetConfigOption("SHAPE_ENCODING", "CP936")  # in order to enable property sheet fields to support Chinese
            [outfilepath, outfilename] = ospath.split(vector_path)
            name = ospath.splitext(outfilename)[0]

            # To create data. Here,create an ESRI SHP file
            driver = ogrGetDriverByName("ESRI Shapefile")
            if driver is None:
                messagebox.showerror("Error", "The driver ({0}) is not available!\n".format("ESRI Shapefile"))
            if ospath.exists(vector_path):
                driver.DeleteDataSource(vector_path)
            ds = driver.CreateDataSource(outfilepath)  # To create Datasource

            if ds is None:
                messagebox.showerror("Error", "Failed to create SHP data source({0}) failed!".format(outfilepath))

            in_srs = SpatialReference()  # Creating a space reference
            in_srs.ImportFromWkt(self.proj)  # Import projection coordinate system

            # Create a layer:creating a polyline layer. name==>SHP name
            layer = ds.CreateLayer(name, in_srs, geom_type=wkbLineString)

            if layer == None:
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
                    row = point[0, 1]
                    col = point[0, 0]
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

            root = Tk()
            root.withdraw()
            messagebox.showinfo("Message",
                                "The surface rupture contour vector obtained by fine-extraction has been created！")
            root.destroy()
            root.mainloop()

        if raster_path:
            maskout = zeros((self.image.shape[0], self.image.shape[1], 3), uint8)
            oF = otherFunction()
            drawContours(maskout, self.cnts, -1, (255, 255, 255), -1)
            oF.writeTif(raster_path, maskout, self.geotrans, self.proj)

            root = Tk()
            root.withdraw()
            messagebox.showinfo("Message",
                                "The surface rupture mask image obtained by fine-extraction has been created!")
            root.destroy()
            root.mainloop()

    def myquit(self):
        self.root.destroy()
        self.save_fineExt()

    def change_img(self, event):
        self.new_contours, self.new_lengthlist, self.new_widthlist, self.new_anglelist = [], [], [], []
        self.change = True
        self.var_text.set("Prompt: The threshold value has changed!")
        self.val_std_min = self.std_min.get()
        self.val_std_max = self.std_max.get()
        self.val_mean_min = self.mean_min.get()
        self.val_mean_max = self.mean_max.get()
        self.val_hw_min = self.hw_min.get()
        self.val_hw_max = self.hw_max.get()
        self.val_peri_min = self.peri_min.get()
        self.val_peri_max = self.peri_max.get()
        # Update fine-extract results in real time
        if self.val_std_min < 0:
            self.val_std_min == 0
        if self.val_std_max < 0:
            self.val_std_max = std_max
        if self.val_mean_min < 0:
            self.val_mean_min = 0
        if self.val_mean_max < 0:
            self.val_mean_max = mean_max
        if self.val_hw_min < 0:
            self.val_hw_min = 0
        if self.val_hw_max < 0:
            self.val_hw_max = hw_max
        if self.val_peri_min < 0:
            self.val_peri_min = 0
        if self.val_peri_max < 0:
            self.val_peri_max = peri_max

        for j in range(len(contours)):
            if ((self.stdlist[j] >= self.val_std_min) and (self.stdlist[j] <= self.val_std_max) and (
                    self.meanlist[j] >= self.val_mean_min)
                    and (self.meanlist[j] <= self.val_mean_max) and (self.hwlist[j] >= self.val_hw_min) and (
                            self.hwlist[j] <= self.val_hw_max)
                    and (self.perimeterlist[j] >= self.val_peri_min) and (self.perimeterlist[j] <= self.val_peri_max)):
                self.contours[j] = append(self.contours[j], [list((self.contours[j])[0])], axis=0)
                self.canvas.create_line(list((self.contours[j].flatten())), fill='red', activefill='gray75',
                                        tag=('del'))
                self.new_contours.append(self.contours[j])
                self.new_lengthlist.append(self.lengthlist[j])
                self.new_widthlist.append(self.widthlist[j])
                self.new_anglelist.append(self.anglelist[j])

        self.new_contours = self.new_contours[:]
        self.show()

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

        i, j, n = 0, 0, ceil(self.imheight / self.tile_height)

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
            # img[-1] = img[-2]
            # img[0] = img[1]
            img = Image.fromarray(img)  # acquire image 
            image.paste(img.resize((w, int(band * k) + 1), Image.ANTIALIAS), (0, int(i * k)))
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

        img_posx = box_image[0]
        img_posy = box_image[1]

        if self.change:
            try:
                self.canvas.delete('del')
            except:
                pass

            for cnt in self.new_contours:
                cnt = append(cnt, [list(cnt[0])], axis=0)
                cnt[:, :, 0] = cnt[:, :, 0] * self.imscale + img_posx
                cnt[:, :, 1] = cnt[:, :, 1] * self.imscale + img_posy
                self.canvas.create_line(list(cnt.flatten()), fill='red', activefill='gray75', tag=('del'))

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
            image = Image.fromarray(img)  # obtain image
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
        self.change = False

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
        #         # Take appropriate image from the pyramid
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


class otherFunction:
    def __init__(self, path=None, maskout=None):
        self.path, self.maskout = path, maskout

    def save_mask(self):
        self.root = Tk()
        width = 358
        height = 190
        size_align = '%dx%d+%d+%d' % (
            width, height, (self.root.winfo_screenwidth() - width) / 2, (self.root.winfo_screenheight() - height) / 2)
        self.root.geometry(size_align)
        self.root.title('Please input the output path...')
        # Creates the Label
        Label(self.root, text="save_path").place(x=45, y=60)
        self.var_text = StringVar()
        Entry(self.root, width=20, textvariable=self.var_text).place(x=125, y=60)

        Button(self.root, text="...", command=self.select_path).place(x=275, y=56)
        Button(self.root, text="Save", command=self.output, activebackground="pink",
               activeforeground="blue").place(x=90, y=150)
        Button(self.root, text="Cancel", command=self.root.destroy, activebackground="pink",
               activeforeground="blue").place(x=235, y=150)
        gdal_ds = Open(self.path)
        self.geotrans, self.proj = gdal_ds.GetGeoTransform(), gdal_ds.GetProjection()
        # Ensure that the following program does not run before closing the UI
        self.root.mainloop()

    def select_path(self):
        save_file = filedialog.asksaveasfilename(title='Select the storage path...', initialdir=None,
                                                 filetypes=[("raster", ".tif"), ('All Files', ' *')],
                                                 defaultextension='.tif')
        self.var_text.set(str(save_file))

    def output(self):
        newpath = self.var_text.get()
        try:
            self.writeTif(newpath, self.maskout, self.geotrans, self.proj)
            messagebox.showinfo('Message', 'It has been created successfully!')
        except Exception as e:
            messagebox.showerror('Error', e)
        self.root.destroy()

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

    def kernel_size(self):
        self.root = Tk()
        self.root.withdraw()
        # acquire string
        result = simpledialog.askstring(title='Get convolution size', prompt='Please enter convolution kernel size: ',
                                        initialvalue='2')
        self.root.destroy()
        self.root.mainloop()

        return result


class funcModule:
    def __init__(self):
        self.flag = []
        self.root = Tk()
        self.root.title('Select the function modules you want to use...')
        self.root.geometry('%dx%d+%d+%d' % (
            150, 200, (self.root.winfo_screenwidth() - 150) / 2, (self.root.winfo_screenheight() - 200) / 2))
        Button(self.root, text="colorSeg", height=1, width=14, command=self.colorSeg).place(x=22, y=40)
        Button(self.root, text="fineExt", height=1, width=14, command=self.fineExt, activebackground="pink",
               activeforeground="blue").place(
            x=22, y=90)
        Button(self.root, text="roughSeg_fineExt", height=1, width=14, command=self.roughSeg_fineExt,
               activebackground="pink",
               activeforeground="blue").place(x=22, y=140)
        self.root.mainloop()

    def colorSeg(self):
        self.root.destroy()
        self.flag.append(0)

    def fineExt(self):
        self.root.destroy()
        self.imageAndmask()

    def roughSeg_fineExt(self):
        self.root.destroy()
        self.flag.append(2)

    def imageAndmask(self):
        width = 500
        height = 400
        self.root = Tk()
        size_align = '%dx%d+%d+%d' % (
            width, height, (self.root.winfo_screenwidth() - width) / 2, (self.root.winfo_screenheight() - height) / 2)
        self.root.geometry(size_align)
        self.root.title('Select the image and corresponding mask...')
        # Creates the first Label Label
        Label(self.root, text="image_path").place(x=100, y=100)
        # Creates the second Label Label
        Label(self.root, text="mask_path").place(x=100, y=200)
        self.e1_text = StringVar()
        self.e2_text = StringVar()
        Entry(self.root, width=20, textvariable=self.e1_text).place(x=180, y=100)
        Entry(self.root, width=20, textvariable=self.e2_text).place(x=180, y=200)

        Button(self.root, text="...", command=self.select_image_path).place(x=330, y=96)
        Button(self.root, text="...", command=self.select_mask_path).place(x=330, y=196)
        Button(self.root, text="Ok", command=self.getpath, activebackground="pink",
               activeforeground="blue").place(x=145, y=300)
        Button(self.root, text="Cancel", command=self.root.destroy, activebackground="pink",
               activeforeground="blue").place(x=290, y=300)
        self.root.mainloop()

    def select_image_path(self):
        imgPath = filedialog.askopenfilename(title='Select the image path...', initialdir=None,
                                             filetypes=[(
                                                 "image", ".tif"), ('All Files', ' *')], defaultextension='.tif')
        self.e1_text.set(str(imgPath))

    def select_mask_path(self):
        maskPath = filedialog.askopenfilename(title='Select the mask path...', initialdir=None,
                                              filetypes=[(
                                                  "mask", ".tif"), ('All Files', ' *')], defaultextension='.tif')
        self.e2_text.set(str(maskPath))

    def getpath(self):
        self.root.destroy()
        imagePath, maskPath = self.e1_text.get(), self.e2_text.get()
        self.flag = [imagePath, maskPath]


if __name__ == "__main__":
    fM = funcModule()
    flag = fM.flag
    # Select the function modules
    if flag == [0]:
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
            lower = []
            upper = []
            mainWindow = Tk()
            mainWindow.state('zoomed')
            mainWindow.title('Zoom and Segmentation')
            frame = ImageSegmentation(mainWindow, path)
            mainWindow.columnconfigure(0, weight=1)
            mainWindow.rowconfigure(0, weight=1)
            mainWindow.mainloop()

            ds = rasterOpen(path)
            new_image = ds.read()
            r = new_image[0]
            g = new_image[1]
            b = new_image[2]
            new_image = merge([r, g, b])
            del r, g, b
            originalHSV = cvtColor(new_image, COLOR_RGB2HSV)
            mask = inRange(originalHSV, lower, upper)
            del originalHSV
            _, thres_mask = threshold(mask, 0, 255, THRESH_BINARY)
            contours, _ = findContours(thres_mask, RETR_EXTERNAL, CHAIN_APPROX_NONE)

            root = Tk()
            root.withdraw()  # Realize the main window hide
            messagebox.showinfo("Message",
                                "Image segmentation has been completed! The parameter of image segmentation lower: {0},upper: {1}".format(
                                    lower, upper))
            root.destroy()
            root.mainloop()

            root1 = Tk()
            root1.withdraw()
            save_mask = messagebox.askokcancel("Prompt",
                                               "Do you want to save the segmented result mask image?(binary image: pixel value 255 is the candidate area for surface rupture)")
            root1.destroy()
            root1.mainloop()
            oF = otherFunction(path, thres_mask)
            if save_mask:
                oF.save_mask()

    elif flag == [2]:
        path = None
        root = Tk()
        app = InputImage(root)
        root.mainloop()

        if path is None:
            root = Tk()
            root.withdraw()  # Realize the main window hide
            messagebox.showerror("Error",
                                 "There was a problem with the image path and the image dataset could not be read successfully!")
            root.destroy()
            root.mainloop()
        else:
            lower = []
            upper = []
            mainWindow = Tk()
            mainWindow.state('zoomed')
            mainWindow.title('Zoom and Segmentation')
            frame = ImageSegmentation(mainWindow, path)
            mainWindow.columnconfigure(0, weight=1)
            mainWindow.rowconfigure(0, weight=1)
            mainWindow.mainloop()

            ds = rasterOpen(path)
            new_image = ds.read()
            r = new_image[0]
            g = new_image[1]
            b = new_image[2]
            new_image = merge([r, g, b])
            del r, g, b
            originalHSV = cvtColor(new_image, COLOR_RGB2HSV)
            mask = inRange(originalHSV, lower, upper)
            del originalHSV
            _, thres_mask = threshold(mask, 0, 255, THRESH_BINARY)
            contours, _ = findContours(thres_mask, RETR_EXTERNAL, CHAIN_APPROX_NONE)

            root1 = Tk()
            root1.withdraw()  # Realize the main window hide
            messagebox.showinfo("Message",
                                "Image segmentation has been completed! The parameter of image segmentation lower: {0},upper: {1}".format(
                                    lower, upper))
            root1.destroy()
            root1.mainloop()

            root2 = Tk()
            root2.withdraw()
            save_mask = messagebox.askokcancel("Prompt",
                                               "Do you want to save the segmented result mask image?(binary image: pixel value 255 is the candidate area for surface rupture)")
            root2.destroy()
            root2.mainloop()

            oF = otherFunction(path, thres_mask)
            if save_mask:
                oF.save_mask()

            root3 = Tk()
            root3.withdraw()
            useDilate = messagebox.askokcancel("Prompt",
                                               "Using dilation methods of mathematical morphological?（If need,The convolution kernel size can be entered. (After many experiments, the convolution kernel size is set to 2 by default))")
            root3.destroy()
            root3.mainloop()

            if useDilate:
                size = '2'
                size = oF.kernel_size()
                # Some non-extracted ground objects were initially deleted and characteristic parameters were extracted
                [stdlist, meanlist, hwlist, perimeterlist, contours, rotatedRectlist, lengthlist, widthlist,
                 anglelist] = preprocessing(mask, new_image, int(size))
            else:
                [stdlist, meanlist, hwlist, perimeterlist, contours, rotatedRectlist, lengthlist, widthlist,
                 anglelist] = preprocessing(mask, new_image)

            hw_max = int(max(hwlist)) + 1
            std_max = int(max(stdlist)) + 1
            mean_max = int(max(meanlist)) + 1
            peri_max = int(max(perimeterlist)) + 1

            root4 = Tk()
            root4.withdraw()
            messagebox.showinfo("Message",
                                "maximum of (Aspect ratio * 1000):{0},maximum of (Mean * 10):{1},maximum of (standard deviation * 10):{2},maximum of perimeter:{3}".format(
                                    hw_max, mean_max, std_max, peri_max))
            root4.destroy()
            root4.mainloop()

            mainWindow = Tk()
            mainWindow.state('zoomed')
            mainWindow.title('Zoom and Fine-Extraction')
            frame = fine_extract(mainWindow, path, mean_max, hw_max, std_max, peri_max, stdlist, meanlist, hwlist,
                                 perimeterlist, contours, lengthlist, widthlist, anglelist)
            mainWindow.columnconfigure(0, weight=1)
            mainWindow.rowconfigure(0, weight=1)
            mainWindow.mainloop()
    else:
        if flag:
            [imgPath, maskPath] = fM.flag
            ds = rasterOpen(imgPath)
            new_image = ds.read()
            r = new_image[0]
            g = new_image[1]
            b = new_image[2]
            new_image = merge([r, g, b])
            del r, g, b
            ds = rasterOpen(maskPath)
            mask = ds.read()
            if len(mask.shape) != 2:
                mask = mask[0]

            root = Tk()
            root.withdraw()
            useDilate = messagebox.askokcancel("Prompt",
                                               "Using dilation methods of mathematical morphological?（If need,The convolution kernel size can be entered. (After many experiments, the convolution kernel size is set to 2 by default))")
            root.destroy()
            root.mainloop()

            if useDilate:
                size = '2'
                oF = otherFunction()
                size = oF.kernel_size()
                # Some non-extracted ground objects were initially deleted and characteristic parameters were extracted
                [stdlist, meanlist, hwlist, perimeterlist, contours, rotatedRectlist, lengthlist, widthlist,
                 anglelist] = preprocessing(mask, new_image, int(size))
            else:
                [stdlist, meanlist, hwlist, perimeterlist, contours, rotatedRectlist, lengthlist, widthlist,
                 anglelist] = preprocessing(mask, new_image)
            hw_max = int(max(hwlist)) + 1
            std_max = int(max(stdlist)) + 1
            mean_max = int(max(meanlist)) + 1
            peri_max = int(max(perimeterlist)) + 1

            root1 = Tk()
            root1.withdraw()
            messagebox.showinfo("Message",
                                "maximum of (Aspect ratio * 1000):{0},maximum of (Mean * 10):{1},maximum of (standard deviation * 10):{2},maximum of perimeter:{3}".format(
                                    hw_max, mean_max, std_max, peri_max))
            root1.destroy()
            root1.mainloop()

            mainWindow = Tk()
            mainWindow.state('zoomed')
            mainWindow.title('Zoom and Fine-Extraction')
            frame = fine_extract(mainWindow, imgPath, mean_max, hw_max, std_max, peri_max, stdlist, meanlist, hwlist,
                                 perimeterlist, contours, lengthlist, widthlist, anglelist)
            mainWindow.columnconfigure(0, weight=1)
            mainWindow.rowconfigure(0, weight=1)
            mainWindow.mainloop()
