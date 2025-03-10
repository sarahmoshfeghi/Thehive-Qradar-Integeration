import os
import logging
import logging.config
from objects.common import getConf, setConf
from objects.offense2alert import allOffense2Alert

def qradar2thehive():
    ## logger configuration
    currentPath = os.path.dirname(os.path.abspath(__file__))
    loggerConfPath = currentPath + '/conf/log.conf'
    logging.config.fileConfig(loggerConfPath)

    logger = logging.getLogger(__name__)

    logger.info('%s.SMART_CLONNER', __name__)

    cfg = getConf()

    scStatus = cfg['smartclonner']['status']
    logger.info("smartclonner status: " + scStatus)

    if int(scStatus) == 0:
        try:
            cfg['smartclonner']['status'] = str(1)
            setConf(cfg)
            logger.info("launching clonning offenses as alert")
            report = allOffense2Alert()
            for reportOffense in report['offenses']:
                logger.info("Is offense " + str(reportOffense['qradar_offense_id']) +
                            " clonned to alert " + str(reportOffense['raised_alert_id']) +
                            " : " + str(reportOffense['success']))
        except Exception as ex:
            logger.error("Tool exception: " + str(ex))

        # set status to "completed"
        cfg = getConf()
        cfg['smartclonner']['status'] = str(0)
        setConf(cfg)
    else:
        logger.info("another instance of smartclonner has been launched")

if __name__ == "__main__":
    qradar2thehive()
