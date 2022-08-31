from osgeo.ogr import GetDriverByName, Open, wkbLineString, Feature
from os import path
from osgeo.gdal import SetConfigOption
from tkinter import Tk, Label, Entry, Button, StringVar, filedialog, messagebox


class Surface2lineRing:
    def __init__(self):
        width = 500
        height = 400
        self.root = Tk()
        size_align = '%dx%d+%d+%d' % (
            width, height, (self.root.winfo_screenwidth() - width) / 2, (self.root.winfo_screenheight() - height) / 2)
        self.root.geometry(size_align)
        self.root.title('Surface vector to lineRing vector...')
        # Creates the first Label
        Label(self.root, text="surface_paths").place(x=98, y=100)
        # Creates the second Label
        Label(self.root, text="save_folder").place(x=100, y=200)
        self.e1_text = StringVar()
        self.e2_text = StringVar()
        Entry(self.root, width=20, textvariable=self.e1_text).place(x=180, y=100)
        Entry(self.root, width=20, textvariable=self.e2_text).place(x=180, y=200)

        Button(self.root, text="...", command=self.select_surface_paths).place(x=330, y=96)
        Button(self.root, text="...", command=self.select_save_folder).place(x=330, y=196)
        Button(self.root, text="Convert", command=self.getpath, activebackground="pink",
               activeforeground="blue").place(x=145, y=300)
        Button(self.root, text="Cancel", command=self.root.destroy, activebackground="pink",
               activeforeground="blue").place(x=290, y=300)
        self.root.mainloop()

    def select_surface_paths(self):
        sfPaths = filedialog.askopenfilenames(title='Select the surface vector path...', initialdir=None,
                                              filetypes=[(
                                                  "vector", ".shp"), ('All Files', ' *')], defaultextension='.shp')
        sfPaths = ";".join(sfPaths)
        self.e1_text.set(str(sfPaths))

    def select_save_folder(self):
        savePath = filedialog.askdirectory(title='Select the lineRing vector save folder...', initialdir=None,
                                           mustexist=True)
        self.e2_text.set(str(savePath))

    def getpath(self):
        self.root.destroy()
        sfPaths, savePath = self.e1_text.get(), self.e2_text.get()
        self.surface2line(sfPaths, savePath)

    def surface2line(self, sfPaths, savePath):
        SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
        SetConfigOption("SHAPE_ENCODING", "GBK")
        root = Tk()
        root.withdraw()
        sfPaths = sfPaths.split(";")
        for sfPath in sfPaths:
            ds = Open(sfPath)
            driver = ds.GetDriver()
            layer = ds.GetLayer()
            in_srs = layer.GetSpatialRef()
            [_, lfilename] = path.split(sfPath)
            name = path.splitext(lfilename)[0]
            linePath = savePath + "/" + lfilename
            filepath, filename = path.split(linePath)
            # driver = GetDriverByName('ESRI Shapefile')
            if driver is None:
                messagebox.showerror("Error", "{0} driver is not available！\n".format("ESRI Shapefile"))

            if path.exists(linePath):
                driver.DeleteDataSource(linePath)

            # Create output datasource
            lineds = driver.CreateDataSource(savePath)

            if lineds is None:
                messagebox.showerror("Error", "Failed to create lineRing vector data source!")

            linelayer = lineds.CreateLayer(name, in_srs, geom_type=wkbLineString)

            if linelayer is None:
                messagebox.showerror("Error", "Failed to create lineRingvector layer!")
            linelayer.CreateFields(layer.schema)
            defn = linelayer.GetLayerDefn()
            if defn is None:
                print("Failed to obtain the layer definition!")

            for feat in layer:
                geom = feat.GetGeometryRef()
                lineRing = geom.GetGeometryRef(0)
                feature = Feature(defn)
                feature.SetGeometry(lineRing)
                for i in range(feat.GetFieldCount()):
                    value = feat.GetField(i)
                    feature.SetField(i, value)

                linelayer.CreateFeature(feature)
                del feature
            del ds
            lineds.Destroy()
        messagebox.showinfo("Prompt", "Surface-to-lineRing conversion is successful!")
        root.destroy()
        root.mainloop()


if __name__ == "__main__":
    Surface2lineRing()
