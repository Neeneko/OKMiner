import os
import sys
import optparse
import ConfigParser
from ProfileManager import ProfileManager
from Experiment import MinerExperiment

class ExperimentManager(object):

    def __init__(self):
        self.__configPath   =   os.path.join(os.path.dirname(sys.modules[__name__].__file__), "Config")
        self.__config       =   ConfigParser.ConfigParser()
        self.__config.optionxform=str
        self.__configName   =   os.path.join(self.__configPath,"experiments.ini")
        if not os.path.exists(self.__configPath):
            sys.stderr.write("Config path does not exist, creating\n")
            os.mkdir(self.__configPath)
        if not os.path.exists(self.__configName):
            sys.stderr.write("Config file does not exist, creating\n")
            self.saveConfig()

        self.__config.read(self.__configName)

    def saveConfig(self):
        with open(self.__configName,'wb') as configFile:
            self.__config.write(configFile)

    def getExperimentNames(self):
        return self.__config.sections()

    def newExperiment(self,name):
        self.__config.add_section(name)

    def delExperiment(self,name):
        self.__config.remove_section(name)

    def setProperty(self,name,prop,value):
        self.__config.set(name,prop,value)

    def getProperty(self,name,prop):
        return self.__config.get(name,prop)

    def delProperty(self,name,prop):
        self.__config.remove_option(name,prop)

    def getPropertyNames(self,name):
        return [ x for (x,_) in self.__config.items(name) ]

    def createExperiment(self,name):
        properties = {}
        for k,v in self.__config.items(name):
            properties[k] = v
        rv = MinerExperiment()
        rv.createExperiment(properties)
        return rv

def doStuff(experiments,options,args):

    def checkExist(exp):
        if exp not in experiments.getExperimentNames():
            raise ValueError,"Experiment [%s] does not exist!\n" % exp
 
    def checkNotExist(exp):
        if exp in experiments.getExperimentNames():
            raise ValueError,"Experiment [%s] already exists!\n" % exp

    def checkValid(prop): 
        if prop not in MinerExperiment.getValidProperties():
            raise ValueError,"Property [%s] is not valid!\n" % prop

    def checkSet(exp,prop):
        if prop not in experiments.getPropertyNames(exp):
            raise ValueError,"Property [%s] is not set in experiment [%s]!\n" % (prop,exp)

    def checkUserName(value):
        profileManager = ProfileManager()
        if value not in profileManager.getProfileNames():
            raise ValueError,"Profile [%s] not currently stored!\n" % (value)

    if options.new:
        checkNotExist(args[0])
        experiments.newExperiment(args[0])
    elif options.delete:
        checkExist(args[0])
        experiments.delExperiment(args[0])
    elif options.list:
        for name in experiments.getExperimentNames():
            sys.stderr.write("Experiment - %s\n" % name)
    elif options.set:
        checkExist(args[0])
        checkValid(args[1])
        if args[1] == "UserName":
            checkUserName(args[2])
        experiments.setProperty(args[0],args[1],args[2])
    elif options.unset:
        checkExist(args[0])
        checkValid(args[1])
        checkSet(args[0],args[1])
        experiments.delProperty(args[0],args[1])
    elif options.exam:
        checkExist(args[0])
        sys.stderr.write("Experiment - %s\n" % args[0])
        for propName in experiments.getPropertyNames(args[0]):
            propValue = experiments.getProperty(args[0],propName)
            sys.stderr.write("%-16s - %s\n" % (propName,propValue))
    elif options.copy:
        raise NotImplementedError
    else:
        raise RuntimeError,"Must select what to do"

if __name__ == "__main__":
    usage = "usage: %prog [options] experiment property value"
    parser = optparse.OptionParser(usage)
    parser.add_option('-l','--list',help="List currently stored experiments",action="store_true",default=False)
    parser.add_option('-e','--exam',help="Display the details of a stored experiment",action="store_true",default=False)
    parser.add_option('-n','--new',help="Add a new experiment",action="store_true",default=False)
    parser.add_option('-c','--copy',help="Copy an existing experiment into a new one",action="store_true",default=False)
    parser.add_option('-d','--delete',help="Delete an experiment",action="store_true",default=False)
    parser.add_option('-s','--set',help="Update an experiment with other values",action="store_true",default=False)
    parser.add_option('-u','--unset',help="Update an experiment with other values",action="store_true",default=False)

    options, args = parser.parse_args()

    if not options.list ^ options.new ^ options.delete ^ options.set ^ options.unset ^ options.exam ^ options.copy: 
        sys.stderr.write("Please select between list, new, delete, set, unset, or exam\n")
        sys.exit()

    if options.list and len(args) != 0:
        sys.stderr.write("list option does not take any arguments\n")
        sys.exit()

    if (options.new or options.exam or options.delete) and len(args) != 1:
        sys.stderr.write("must specify experiment name for new, exam, and delete\n")
        sys.exit()

    if options.unset and len(args) != 2:
        sys.stderr.write("Must specify experiment name and property for unset.\n")
        sys.exit()

    if options.copy and len(args) != 2:
        sys.stderr.write("Must specify experiment source and destination for copy.\n")
        sys.exit()

    if options.set and len(args) != 3:
        sys.stderr.write("Must specifiocy experiment name, property, and value for set.\n")
        sys.exit()

    experiments = ExperimentManager()
    doStuff(experiments,options,args)
    experiments.saveConfig()
