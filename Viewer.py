import sys
import logging
import optparse
from Blobber import LoadSavedBlob,CreateMemoryOnlyBlob
from Report import ReportManager,ReportData,MultiGraph,SimpleGraph,PercentHeatMap,MapGraph,Page


if __name__ == "__main__":
    usage       =   "usage: %prog [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-b', '--blob', help="load a blob file", action="store",default=None)
    parser.add_option('-e', '--experiment', help="load experiment into in-memory db", action="store",default=None)

    logging.basicConfig(level=logging.INFO)

    options, args = parser.parse_args()
    if not (options.blob is None) ^ (options.experiment is None):
        logging.error("Select Blob or Experiment")
        sys.exit(0)        

    if options.blob:
        db              =   LoadSavedBlob(options.blob)
    elif options.experiment:
        db   =   CreateMemoryOnlyBlob(options.experiment)

    experimentName  =   db.getExperimentName()   
    logging.info("Experiment Name [%s]" % experimentName)

    MINUTE          =   60
    HOUR            =   MINUTE*60
    DAY             =   HOUR*60
    WEEK            =   DAY*7
    MONTH           =   WEEK*4
    YEAR            =   WEEK*52
    DECADE          =   YEAR*10

    reportData      =   ReportData()
    reportData.Graphs.append(MapGraph("Locations",rows=db.GetLocations("Longitude","Latitude","Users.UserId")))

    reportData.Graphs.append(SimpleGraph("Account Ages",preserve_order=True))
    for month in range(12):
        reportData.Graphs[-1].setValue("%s Months" % (month),len(db.GetUsersJoinRange(MONTH*month,MONTH*(month+1))))
    year            =   1
    while True:
        if len(db.GetUsersOlderThen(YEAR*year)) == 0:
            break
        reportData.Graphs[-1].setValue("%d Years" % (year),len(db.GetUsersJoinRange(YEAR*year,YEAR*(year+1))))
        year += 1

    """
    reportData.Graphs.append(Page())
    reportData.Graphs.append(MultiGraph("Searches By Sex",legend="Sex"))
    cursor = db.getCursor()
    cursor.execute("SELECT Searches.Age,Searches.Gentation,COUNT(SearchToUser
    """



    reportData.Graphs.append(Page())
    reportData.Graphs[-1].Graphs.append(SimpleGraph("Account Types by Sex",preserve_order=True,percent=True))
    reportData.Graphs[-1].Graphs[-1].setValue("Female",db.GetUserCount(filterEqField=("Sex","Female")))
    reportData.Graphs[-1].Graphs[-1].setValue("Male",db.GetUserCount(filterEqField=("Sex","Male")))
    reportData.Graphs[-1].Graphs.append(SimpleGraph("Account Types by Orientation",preserve_order=True,percent=True))
    reportData.Graphs[-1].Graphs[-1].setValue("Bi",db.GetUserCount(filterEqField=("Orientation","Bi")))
    reportData.Graphs[-1].Graphs[-1].setValue("Gay",db.GetUserCount(filterEqField=("Orientation","Gay")))
    reportData.Graphs[-1].Graphs[-1].setValue("Strait",db.GetUserCount(filterEqField=("Orientation","Strait")))

    reportData.Graphs.append(MultiGraph("Age By Sex",rows=db.GetUsers("Sex","Age"),legend="Sex"))
    reportData.Graphs.append(MultiGraph("Age By Orientation",rows=db.GetUsers("Orientation","Age"),legend="Orientation"))
    reportData.Graphs.append(MultiGraph("Orientation By Sex",rows=db.GetUsers("Sex","Orientation"),legend="Sex"))
    #------------------------------------------------------------------------------------
    reportData.Graphs.append(MultiGraph("Reply Rate By Sex",rows=db.GetUsers("Sex","Contacts.ReplyPercent"),legend="Sex"))
    reportData.Graphs.append(MultiGraph("Reply Rate By Orientation - Male",rows=db.GetUsers("Orientation","Contacts.ReplyPercent",filterEqField=("Sex","Male")),legend="Orientation"))
    reportData.Graphs.append(MultiGraph("Reply Rate By Orientation - Female",rows=db.GetUsers("Orientation","Contacts.ReplyPercent",filterEqField=("Sex","Female")),legend="Orientation"))
    #------------------------------------------------------------------------------------
    reportData.Graphs.append(MultiGraph("Contacts This Week By Sex",rows=db.GetUsers("Sex","Contacts.ContactsWeek"),legend="Sex"))
    reportData.Graphs.append(MultiGraph("Contacts This Week By Orientation - Male",rows=db.GetUsers("Orientation","Contacts.ContactsWeek",filterEqField=("Sex","Male")),legend="Orientation"))
    reportData.Graphs.append(MultiGraph("Contacts This Week By Orientation - Female",rows=db.GetUsers("Orientation","Contacts.ContactsWeek",filterEqField=("Sex","Female")),legend="Orientation"))
    #------------------------------------------------------------------------------------
    reportData.Graphs.append(MultiGraph("Recent Contacts By Sex",rows=db.GetUsers("Sex","Contacts.ContactsRecent"),legend="Sex"))
    reportData.Graphs.append(MultiGraph("Recent Contacts By Orientation - Male",rows=db.GetUsers("Orientation","Contacts.ContactsRecent",filterEqField=("Sex","Male")),legend="Orientation"))
    reportData.Graphs.append(MultiGraph("Recent Contacts By Orientation - Female",rows=db.GetUsers("Orientation","Contacts.ContactsRecent",filterEqField=("Sex","Female")),legend="Orientation"))
    #------------------------------------------------------------------------------------
    reportData.Graphs.append(MultiGraph("Recent Replies By Sex",rows=db.GetUsers("Sex","Contacts.RepliesRecent"),legend="Sex"))
    reportData.Graphs.append(MultiGraph("Recent Replies By Orientation - Male",rows=db.GetUsers("Orientation","Contacts.RepliesRecent",filterEqField=("Sex","Male")),legend="Orientation"))
    reportData.Graphs.append(MultiGraph("Recent Replies By Orientation - Female",rows=db.GetUsers("Orientation","Contacts.RepliesRecent",filterEqField=("Sex","Female")),legend="Orientation"))
    #------------------------------------------------------------------------------------
    reportData.Graphs.append(Page())
    reportData.Graphs[-1].Graphs.append(SimpleGraph("Sampled Account Types by Sex",preserve_order=True,percent=True))
    reportData.Graphs[-1].Graphs[-1].setValue("Female",db.GetSampleUserCount(filterEqField=("Sex","Female")))
    reportData.Graphs[-1].Graphs[-1].setValue("Male",db.GetSampleUserCount(filterEqField=("Sex","Male")))
    reportData.Graphs[-1].Graphs.append(SimpleGraph("Sampled Account Types by Orientation",preserve_order=True,percent=True))
    reportData.Graphs[-1].Graphs[-1].setValue("Bi",db.GetSampleUserCount(filterEqField=("Orientation","Bi")))
    reportData.Graphs[-1].Graphs[-1].setValue("Gay",db.GetSampleUserCount(filterEqField=("Orientation","Gay")))
    reportData.Graphs[-1].Graphs[-1].setValue("Strait",db.GetSampleUserCount(filterEqField=("Orientation","Strait")))
    #------------------------------------------------------------------------------------
    reportData.Graphs.append(SimpleGraph("Ethnicities",rows=db.GetRecords("UserEthnicitie","Ethnicity")))
    reportData.Graphs.append(SimpleGraph("Languages",rows=db.GetRecords("UserLanguage","Language")))

    query = "SELECT Sex,Gentation.GentationText FROM Users,UserLookingFor,Gentation WHERE Users.UserId = UserLookingFor.UserId AND UserLookingFor.Gentation=Gentation.GentationId"
    reportData.Graphs.append(MultiGraph("Looking For - Gentation",rows=db.GetRaw(query),legend="Sex",vertical=False))
    reportData.Graphs.append(Page())
    reportData.Graphs[-1].Graphs.append(MultiGraph("Relationship Status by Orientation",rows=db.GetUsers("Orientation","UserInfos.RelationshipStatus"),legend="Orientation",vertical=False))
    reportData.Graphs[-1].Graphs.append(MultiGraph("Relationship Status by Sex",rows=db.GetUsers("Sex","UserInfos.RelationshipStatus"),legend="Sex",vertical=False))
    reportData.Graphs.append(Page())
    reportData.Graphs[-1].Graphs.append(MultiGraph("Relationship Type by Orientation",rows=db.GetUsers("Orientation","UserInfos.RelationshipType"),legend="Orientation",vertical=False))
    reportData.Graphs[-1].Graphs.append(MultiGraph("Relationship Type by Sex",rows=db.GetUsers("Sex","UserInfos.RelationshipType"),legend="Sex",vertical=False))

    reportManager   =   ReportManager(experimentName)
    reportManager.writeReport(reportData)
    reportManager.displayReport()
