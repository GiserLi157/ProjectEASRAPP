from osgeo.ogr import GetDriverByName, FieldDefn, OFTReal, OFTInteger, wkbPolygon
from osgeo.osr import SpatialReference
from osgeo.gdal import Polygonize, GA_ReadOnly, Open, SetConfigOption
from os import path
from tkinter import Tk, Label, Entry, Button, StringVar, filedialog, messagebox


class Raster2vector:
    def __init__(self):
        width = 500
        height = 400
        self.root = Tk()
        size_align = '%dx%d+%d+%d' % (
            width, height, (self.root.winfo_screenwidth() - width) / 2, (self.root.winfo_screenheight() - height) / 2)
        self.root.geometry(size_align)
        self.root.title('Raster to vector...')
        # Creates the first Label
        Label(self.root, text="raster_paths:").place(x=100, y=100)
        # Creates the second Label
        Label(self.root, text="save_folder :").place(x=100, y=200)
        # Creates the second Label
        self.e1_text = StringVar()
        self.e2_text = StringVar()
        Entry(self.root, width=20, textvariable=self.e1_text).place(x=180, y=100)
        Entry(self.root, width=20, textvariable=self.e2_text).place(x=180, y=200)
        Button(self.root, text="...", command=self.select_raster_paths).place(x=330, y=96)
        Button(self.root, text="...", command=self.select_save_folder).place(x=330, y=196)
        Button(self.root, text="Convert", command=self.getpath, activebackground="pink",
               activeforeground="blue").place(x=145, y=300)
        Button(self.root, text="Cancel", command=self.root.destroy, activebackground="pink",
               activeforeground="blue").place(x=290, y=300)
        self.root.mainloop()

    def select_raster_paths(self):
        imgPaths = filedialog.askopenfilenames(title='Select the raster path...', initialdir=None,
                                               filetypes=[(
                                                   "raster", ".tif"), ('All Files', ' *')], defaultextension='.tif')
        imgPaths = ";".join(imgPaths)
        self.e1_text.set(str(imgPaths))

    def select_save_folder(self):
        savePath = filedialog.askdirectory(title='Select the vector output path...', initialdir=None,
                                           mustexist=True)
        self.e2_text.set(str(savePath))

    def getpath(self):
        self.root.destroy()
        rasterPaths, savePath = self.e1_text.get(), self.e2_text.get()
        self.raster_to_vector(rasterPaths, savePath)

    def raster_to_vector(self, rasterfiles, savePath):
        root = Tk()
        root.withdraw()
        rasterfiles = rasterfiles.split(";")
        for rasterfile in rasterfiles:
            [_, rfilename] = path.split(rasterfile)
            name = path.splitext(rfilename)[0]
            shapefile = savePath + "/" + name + ".shp"
            ds = Open(rasterfile, GA_ReadOnly)
            im_band = ds.GetRasterBand(1)
            SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
            SetConfigOption("SHAPE_ENCODING", "GBK")
            vector_driver = GetDriverByName('ESRI Shapefile')
            if vector_driver is None:
                messagebox.showerror("Error", '{0}driver is not available！'.format('ESRI Shapefile'))
            if path.exists(shapefile):
                vector_driver.DeleteDataSource(shapefile)
            vector_ds = vector_driver.CreateDataSource(savePath)  # Create datasource
            if vector_ds is None:
                messagebox.showerror("Error", 'Failed to create shp datasource: {0}！'.format(savePath))
            prj = SpatialReference()
            prj.ImportFromWkt(ds.GetProjection())  # Use the projection information

            vector_layer = vector_ds.CreateLayer(name, srs=prj, geom_type=wkbPolygon)

            img = im_band.ReadAsArray()
            data_type = img.dtype.name
            if 'int' in data_type:
                field_type = OFTInteger
            else:
                field_type = OFTReal
            field = FieldDefn('value', field_type)
            vector_layer.CreateField(field)
            Polygonize(im_band, None, vector_layer, 0)
            del vector_ds
            del ds

        messagebox.showinfo("Prompt", "Raster_to_vector conversion is successful!")
        root.destroy()
        root.mainloop()


if __name__ == "__main__":
    Raster2vector()
