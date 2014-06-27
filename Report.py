import os
import sys
import logging
import numpy
import pylab
from matplotlib import pyplot,colors,ticker
from matplotlib.backends.backend_pdf import PdfPages
from mpl_toolkits.basemap import Basemap

def log(message):
    sys.stderr.write("%s\n" % message)
    sys.stderr.flush()

class Page(object):

    def __init__(self):
        self.Graphs         =   []

class MultiGraph(object):

    def __init__(self,title,rows=[],vertical=True,preserve_order=False,sort_by_value=False,legend=""):
        self.__title        =   title
        self.__legend       =   legend
        self.__data         =   {}
        self.__keys         =   []
        self.__vertical     =   vertical
        if preserve_order and sort_by_value:
            raise RuntimeError
        self.__sortByValue  =   sort_by_value
        if preserve_order:
            self.__order        =   []
        else:
            self.__order        =   None
        for row in rows:
            self.incValue(row[0],row[1],1)

    def setVertical(self,vertical):
        self.__vertical     =   vertical

    def getVertical(self):
        return self.__vertical

    def getLegend(self):
        return self.__legend

    def getTitle(self):
        return self.__title

    def incValue(self,cat,key,value):
        if cat not in self.__data:
            self.__data[cat]      =   {}
            if self.__order is not None:
                self.__order =  [cat] + self.__order
        if key not in self.__data[cat]:
            self.__data[cat][key] =   0
            if key not in self.__keys:
                self.__keys =   [key] + self.__keys
        self.__data[cat][key]     +=  value

    def setValue(self,cat,key,value):
        if cat not in self.__data:
            self.__data[cat]      =   {}
            if self.__order is not None:
                self.__order = [cat] + self.__order
        if key not in self.__data[cat]:
            self.__data[cat][key] =   0
            if key not in self.__keys:
                self.__keys =   [key] + self.__keys
        self.__data[cat][key] =  value

    def getValue(self,cat,key):
        return self.__data.get(cat,{}).get(key,0)

    def getCats(self):
        sys.stderr.write("Cats [%s] Order [%s]\n" % (self.__data.keys(),self.__order)) 
        if self.__order is not None:  
            return sorted(self.__order)
        elif self.__sortByValue:
            tmp =   {}
            for cat in self.__data.keys():
                tmp[cat] = 0
            for k,v in self.__data.iteritems():
                for vv in v.values():
                    tmp[k] += vv
            return sorted(tmp,key=tmp.get)
        else:
            return self.__data.keys()

    def getKeys(self):
        sys.stderr.write("Keys [%s] Order [%s]\n" % (self.__keys,self.__order)) 
        if self.__order is not None:
            return self.__keys
        elif self.__sortByValue:
            tmp =   {}
            for key in self.__keys:
                tmp[key] = 0
            for v in self.__data.values():
                for k,vv in v.iteritems():
                    tmp[k] += vv
            return sorted(tmp,key=tmp.get)
        else:
            return sorted(self.__keys)

class PercentHeatMap(object):

    def __init__(self,title,values_rows=None,totals_rows=None):
        self.__title = title
        self.__values   =   MultiGraph("Values",rows=values_rows)
        self.__totals   =   MultiGraph("Totals",rows=totals_rows)
        
    def getTitle(self):
        return self.__title

    def incValue(self,cat,key,value):
        self.__values.incValue(cat,key,value)

    def incTotal(self,cat,key,value):
        self.__totals.incValue(cat,key,value)

    def getCatRange(self):
        return range(min(min(self.__values.getCats()),min(self.__totals.getCats())),max(max(self.__values.getCats()),max(self.__totals.getCats())))

    def getKeyRange(self):
        return range(min(min(self.__values.getKeys()),min(self.__totals.getKeys())),max(max(self.__values.getKeys()),max(self.__totals.getKeys())))

    def getValue(self,cat,key):
        if self.__totals.getValue(cat,key) == 0:
            return 0
        else:
            return int(100.0 * self.__values.getValue(cat,key)/self.__totals.getValue(cat,key))

class SimpleGraph(object):

    def __init__(self,title,preserve_order=False,rows=[],default_colour=None,sort_by_value=False,highlight=None,percent=False):
        self.__title            =   title
        self.__Data             =   {}
        if preserve_order and sort_by_value:
            raise RuntimeError
        self.__sortByValue      =   sort_by_value
        if preserve_order:
            self.__order        =   []
        else:
            self.__order        =   None
        self.__defaultColour    =   default_colour
        self.__highlight        =   highlight
        self.__percent          =   percent
        self.__total            =   0
        for row in rows:
            self.incValue(row[0],1)
 
    def isPercent(self):
        return self.__percent

    def getTitle(self):
        return self.__title

    def getDefaultColour(self):
        return self.__defaultColour

    def getHighlight(self,key):
        if self.__highlight is None:
            return "Grey"
        if isinstance(self.__highlight,basestring):
            return self.__highlight
        if key in self.__highlight:
            return "Yellow"
        else:
            return "White"

    def setValue(self,x,value):
        if x not in self.__Data and self.__order is not None:
            self.__order = [x] + self.__order
        self.__Data[x]      =   value
        self.__total        +=  value

    def incValue(self,x,value):
        if x not in self.__Data:
            self.__Data[x]  =   0
            if self.__order is not None:
                self.__order = [x] + self.__order
        self.__Data[x]      +=  value
        self.__total        +=  value

    def getValue(self,x):
        if self.__percent:
            return 100 * self.__Data.get(x,0)/self.__total
        else:
            return self.__Data.get(x,0)

    def hasValue(self,x):
        return x in self.__Data.keys()

    def getKeys(self):
        if self.__order:
            return self.__order
        elif self.__sortByValue:
            return sorted(self.__Data,key=self.__Data.get)
        else:
            return sorted(self.__Data.keys())

class MapGraph(object):

    def __init__(self,title,rows=None):
        self.__title        =   title
        self.__Data         =   {}
        for row in rows:
            (lon,lat)       =   self.__safeCoord(row[0],row[1])

            self.incValue(row[0],row[1],1)
 
    def getTitle(self):
        return self.__title

    def setValue(self,lon,lat,value):
        x                   =   self.__safeCoord(lon,lat)
        self.__Data[x]      =   value

    def incValue(self,lon,lat,value):
        x                   =   self.__safeCoord(lon,lat)
        if x not in self.__Data:
            self.__Data[x]  =   0
        self.__Data[x]      +=  value

    def getValue(self,lon,lat):
        x                   =   self.__safeCoord(lon,lat)
        return self.__Data.get(x,0)

    def getKeys(self):
        return sorted(self.__Data.keys())

    def __safeCoord(self,lon,lat):
        return (int(lon),int(lat))

class ReportData(object):

    def __init__(self):
        self.Graphs         =   []
        self.AllProfiles    =   []
        self.ActiveProfiles =   []

class ReportManager(object):
    COLOURS =   {
                    "Female"    :   "Red",
                    "Male"      :   "Blue",
                    "Strait"    :   "Yellow",
                    "Bi"        :   "Purple",
                    "Gay"       :   "Green"
                }

    def __init__(self,experiment):
        self.__pdfName  =   os.path.join(os.path.dirname(sys.modules[__name__].__file__), "Reports","%s.pdf" % experiment)

    def __getColour(self,label,default=None):
        if label in ReportManager.COLOURS:
            return ReportManager.COLOURS[label]
        elif default is not None:
            return default
        else:
            return "Black"

    def __fontSize(self,value):
        if value >= 64:
            return 3
        if value >= 32:
            return 6
        if value >= 16:
            return 8
        return 10
        #if value >= 8:
        #    return 12
        #return 14
    def __unicodeLabels(self,values):
        rv  =   []
        for value in values:
            if isinstance(value,int):
                rv.append(unicode(int))
                continue
            if value is None:
                rv.append(unicode("None"))
                continue

            if len(value) > 12 and value.count(" ") > 0:
                value = "%s" % value
                if value.count(" ") == 1:
                    rv.append(value.replace(" ","\n"))
                else:
                    rv.append(value.replace(" ","\n",2))
                continue
            rv.append(unicode(value))
        return rv

    def __writePage(self,pdf,graphs):
        fig         =   pyplot.figure()
        for idx in range(len(graphs)):
            ax = pyplot.subplot2grid((len(graphs),1), (idx, 0))
            graph = graphs[idx]
            logging.info("*** [%s] ***" % graph.getTitle())
            if isinstance(graph,MapGraph):
                baseMap = Basemap(projection='mill',ax=ax)
                baseMap.drawcoastlines()
                baseMap.drawparallels(numpy.arange(-90,90,30),labels=[1,0,0,0])
                baseMap.drawmeridians(numpy.arange(baseMap.lonmin,baseMap.lonmax+30,60),labels=[0,0,0,1])
                baseMap.drawmapboundary(fill_color='aqua')
                baseMap.fillcontinents(color='coral',lake_color='aqua')
                lons    =   []
                lats    =   []
                r       =   []
                logging.info("Starting Map")
                for (lon,lat) in graph.getKeys():
                    value   =   graph.getValue(lon,lat)
                    r.append(len(str(value))*5)
                    while lon > baseMap.lonmax:
                        lon -=  360

                    while lon < baseMap.lonmin:
                        lon +=  360

                    while lat > baseMap.latmax:
                        lat -=  180

                    while lat < baseMap.latmin:
                        lat += 180

                    lons.append(lon)
                    lats.append(lat)
                x,y     =   baseMap(lons,lats)
                baseMap.scatter(x,y,r,zorder=99)


            elif isinstance(graph,SimpleGraph):
                keys        =   graph.getKeys()
                ind         =   numpy.arange(len(keys))
                values  =   [ graph.getValue(key) for key in keys ]
                colours =   [ self.__getColour(key,graph.getDefaultColour()) for key in keys]
                edgeColours =   []
                for key in keys:
                    edgeColours.append(graph.getHighlight(key))

                rect    =   ax.barh(ind, values, color=colours,edgecolor = edgeColours)
                ax.set_title(graph.getTitle())
                ax.set_yticks(ind)
                ax.set_yticklabels( keys )
                ax.set_ylim(0,len(keys))
                ax.tick_params('both', length=0, width=0, which='minor')
                ax.yaxis.set_major_formatter(ticker.NullFormatter())
                ax.yaxis.set_minor_locator(ticker.FixedLocator(0.5 + ind))
                ax.yaxis.set_minor_formatter(ticker.FixedFormatter(keys))
            elif isinstance(graph,PercentHeatMap):
                pyplot.rc('xtick', labelsize=6) 
                pyplot.rc('xtick', labelsize=6) 
                sys.stderr.write("Starting Heat Map [%s]\n" % graph.getTitle())
                catRange    =   graph.getCatRange()
                keyRange    =   graph.getKeyRange()
                sys.stderr.write("catRange [%s]\n" % catRange)
                sys.stderr.write("keyRange [%s]\n" % keyRange)
                data    =   numpy.random.randn(len(catRange),len(keyRange))
                for c in catRange:
                    for k in keyRange:
                        i   =   c-catRange[0]
                        j   =   k-keyRange[0]
                        data[i][j]  =   graph.getValue(c,k)
                        if data[i][j] == 0:
                            data[i][j] = -1
                c   =   pylab.ma.masked_where(c<0,c)
                cdict = {
                        'red':  (       (0.0,   0.0,  1.0),
                                        (0.0,   1.0,  0.0),
                                        (0.5,   0.0,  0.0), 
                                        (1.0,   1.0,  1.0)),
                        'green':(       (0.0,   0.0,  1.0),
                                        (0.0,   1.0,  0.0),
                                        (1.0,   0.0,  0.0)),
                        'blue': (       (0.0,   0.0,  1.0),
                                        (0.0,   1.0,  1.0),
                                        (0.5,   0.0,  0.0), 
                                        (1.0,   0.0,  0.0))
                        }

                colorMap    =   colors.LinearSegmentedColormap("custom",cdict)
                p = ax.pcolormesh(data,cmap=colorMap)
                evenKeys    =   []
                for idx in range(len(keyRange)):
                    if keyRange[idx]%2 == 0:
                        evenKeys.append(keyRange[idx])
                    else:
                        evenKeys.append("")
                ax.set_xticks(numpy.arange(len(evenKeys)))
                ax.set_xticklabels( evenKeys )
                ax.set_yticks(numpy.arange(len(catRange)))
                ind         =   numpy.arange(len(catRange))
                ax.tick_params('both', length=0, width=0, which='minor')
                ax.yaxis.set_major_formatter(ticker.NullFormatter())
                ax.yaxis.set_minor_locator(ticker.FixedLocator(0.5+ind))
                ax.yaxis.set_minor_formatter(ticker.FixedFormatter(catRange))
 
                ax.set_xlim(0,len(keyRange))
                colorBar    =   fig.colorbar(p,values=numpy.arange(101),boundaries=numpy.arange(101),ticks=[0,25,50,75,100],orientation='horizontal')
                colorBar.ax.set_xticklabels(['0%','25%' ,'50%','75%' ,'100%'])
                sys.stderr.write("boundries - %s\n" % str(colorBar._boundaries))
                pyplot.title(graph.getTitle())
            elif isinstance(graph,MultiGraph) and graph.getVertical():
                keys        =   graph.getKeys()
                cats        =   graph.getCats()
                labels      =   self.__unicodeLabels(keys)
                logging.info("Labels %s" % (labels))
                ind         =   numpy.arange(len(keys))*len(cats)
                for idx in range(len(graph.getCats())):
                    cat     =   cats[idx]
                    colour  =   self.__getColour(cat)
                    values  =   [ graph.getValue(cat,key) for key in keys ]
                    rect    =   ax.bar(ind+idx,values,color=colour,edgecolor = "none",label=cat)
                ax.set_title(graph.getTitle())
                ax.set_xticks(ind)
                ax.set_xticklabels( labels )
                ax.set_xlim(0,len(keys)*len(cats))
                ax.tick_params('both', length=0, width=0, which='minor')
                ax.xaxis.set_major_formatter(ticker.NullFormatter())
                ax.xaxis.set_minor_locator(ticker.FixedLocator(len(cats)/2.0 + ind))
                ax.xaxis.set_minor_formatter(ticker.FixedFormatter(keys))
                ax.legend(title=graph.getLegend(),loc="upper right")
            elif isinstance(graph,MultiGraph) and not graph.getVertical():
                keys        =   graph.getKeys()
                cats        =   graph.getCats()
                labels      =   self.__unicodeLabels(keys)
                logging.info("Labels %s" % (labels))
                ind         =   numpy.arange(len(keys))*(len(cats))
                for idx in range(len(graph.getCats())):
                    cat     =   cats[idx]
                    colour  =   self.__getColour(cat)
                    values  =   [ graph.getValue(cat,key) for key in keys ]
                    rect    =   ax.barh(ind+idx, values, color=colour,edgecolor = "none",label=cat)
                ax.set_title(graph.getTitle())
                ax.set_yticks(ind)
                ax.set_yticklabels( labels )
                ax.set_ylim(0,len(keys)*len(cats))
                ax.tick_params('both', length=0, width=0, which='minor')
                ax.yaxis.set_major_formatter(ticker.NullFormatter())
                ax.yaxis.set_minor_locator(ticker.FixedLocator(len(cats)/2.0 + ind))
                ax.yaxis.set_minor_formatter(ticker.FixedFormatter(keys))
                ax.legend(title=graph.getLegend(),loc="lower right")
            
            ax.tick_params(axis='x',which='both',labelsize=self.__fontSize(len(ax.get_xticks())))
            ax.tick_params(axis='y',which='both',labelsize=self.__fontSize(len(ax.get_yticks())))
 
        pdf.savefig(fig)

    def writeReport(self,data):
        log("Starting Doc Creation")
        pdf = PdfPages(self.__pdfName)
        for graph in data.Graphs:
            if isinstance(graph,Page):
                self.__writePage(pdf,graph.Graphs)
            else:
                self.__writePage(pdf,[graph])
        pdf.close()
        
        log("Done Doc Creation")

    def displayReport(self):
        import webbrowser
        controller = webbrowser.get()
        controller.open_new("file:" + os.path.abspath(self.__pdfName))
