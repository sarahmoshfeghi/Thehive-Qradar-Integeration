
#!/usr/bin/env python3
# -*- coding: utf8 -*-
import os
import sys
import logging
import copy
import json

from time import sleep

from objects.common import getConf, setConf
from objects.qradar_connector import QRadarConnector
from objects.thehive_connector import TheHiveConnector

def getEnrichedOffenses(qradarConnector, timerange):
    enrichedOffenses = []

    for offense in qradarConnector.getOffenses(timerange):
        enrichedOffenses.append(enrichOffense(qradarConnector, offense))

    return enrichedOffenses

def enrichOffense(qradarConnector, offense):

    enriched = copy.deepcopy(offense)

    artifacts = []

    enriched['offense_type_str'] = \
                qradarConnector.getOffenseTypeStr(offense['offense_type'])

    # Add the offense source explicitly
    if enriched['offense_type_str'] == 'Username':
        artifacts.append({'data': offense['offense_source'], 'dataType': 'username', 'message': 'Offense Source'})
    else:
        # Assume offense_source is an IP if not a username
        artifacts.append({'data': offense['offense_source'], 'dataType': 'ip', 'message': 'Offense Source', 'tags': ['src']})

    # Add the local and remote sources
    srcIps = qradarConnector.getSourceIPs(enriched)
    dstIps = qradarConnector.getLocalDestinationIPs(enriched)
    srcDstIps = list(set(srcIps) & set(dstIps))
    srcIps = list(set(srcIps) - set(srcDstIps))
    dstIps = list(set(dstIps) - set(srcDstIps))

    for ip in srcIps:
        artifacts.append({'data': ip, 'dataType': 'ip', 'message': 'Source IP', 'tags': ['src']})
    for ip in dstIps:
        artifacts.append({'data': ip, 'dataType': 'ip', 'message': 'Local destination IP', 'tags': ['dst']})
    for ip in srcDstIps:
        artifacts.append({'data': ip, 'dataType': 'ip', 'message': 'Source and local destination IP', 'tags': ['src', 'dst']})

    # Define default observable data types
    defaultObservableDatatype = ['autonomous-system', 'domain', 'file', 'filename', 'fqdn', 'hash', 'ip', 'mail', 'mail_subject', 'other', 'regexp', 'registry', 'uri_path', 'url', 'user-agent']

    # Check and add observables for each data type if they exist in the offense data
    for dataType in defaultObservableDatatype:
        if dataType in offense:
            artifacts.append({'data': offense[dataType], 'dataType': dataType, 'message': dataType})
        # Additionally check in the enriched data
        if dataType in enriched:
            artifacts.append({'data': enriched[dataType], 'dataType': dataType, 'message': dataType})

    # Add all the observables
    enriched['artifacts'] = artifacts

    # waiting 1s to make sure the logs are searchable
    sleep(1)
    # adding the first 3 raw logs
    enriched['logs'] = qradarConnector.getOffenseLogs(enriched)

    return enriched

def qradarOffenseToHiveAlert(theHiveConnector, offense):

    def getHiveSeverity(offense):
        # severity in TheHive is either low, medium or high
        # while severity in QRadar is from 1 to 10
        # low will be [1;4] => 1
        # medium will be [5;6] => 2
        # high will be [7;10] => 3
        if offense['severity'] < 5:
            return 1
        elif offense['severity'] < 7:
            return 2
        elif offense['severity'] < 11:
            return 3
        return 1

    #
    # Creating the alert
    #

    # Setup Tags
    tags = ['QRadar', 'Offense']

    if "categories" in offense:
        for cat in offense['categories']:
            tags.append(cat)

    defaultObservableDatatype = ['autonomous-system', 'domain', 'file', 'filename', 'fqdn', 'hash', 'ip', 'mail', 'mail_subject', 'other', 'regexp', 'registry', 'uri_path', 'url', 'user-agent']

    artifacts = []
    for artifact in offense['artifacts']:
        if artifact['dataType'] in defaultObservableDatatype:
            hiveArtifact = theHiveConnector.craftAlertArtifact(dataType=artifact['dataType'], data=artifact['data'], message=artifact['message'], tags=artifact.get('tags', []))
        else:
            tags = list()
            tags.append('type:' + artifact['dataType'])
            hiveArtifact = theHiveConnector.craftAlertArtifact(dataType='other', data=artifact['data'], message=artifact['message'], tags=tags)
        artifacts.append(hiveArtifact)

    # Build TheHive alert
    alert = theHiveConnector.craftAlert(
        offense['description'],
        craftAlertDescription(offense),
        getHiveSeverity(offense),
        offense['start_time'],
        tags,
        2,
        'Imported',
        'internal',
        'QRadar_Offenses',
        str(offense['id']),
        artifacts,
        '')

    return alert

def allOffense2Alert():
    """
       Get all open offenses created within the last
       <timerange> minutes and creates alerts for them in
       TheHive
    """
    logger = logging.getLogger(__name__)
    logger.info('%s.allOffense2Alert starts', __name__)

    report = dict()
    report['success'] = True
    report['offenses'] = list()

    try:
        cfg = getConf()

        qradarConnector = QRadarConnector(cfg)
        theHiveConnector = TheHiveConnector(cfg)

        offensesList = qradarConnector.getOffensesAfter()

        offenseLastId = int(cfg.get('QRadar', 'offense_id_after'))

        # each offense in the list is represented as a dict
        # we enrich this dict with additional details
        for offense in offensesList:
            # searching if the offense has already been converted to alert
            q = dict()
            q['sourceRef'] = str(offense['id'])
            logger.info('Looking for offense %s in TheHive alerts', str(offense['id']))
            results = theHiveConnector.findAlert(q)
            if len(results) == 0:
                offense_report = dict()
                enrichedOffense = enrichOffense(qradarConnector, offense)
                try:
                    theHiveAlert = qradarOffenseToHiveAlert(theHiveConnector, enrichedOffense)
                    theHiveEsAlertId = theHiveConnector.createAlert(theHiveAlert)['id']
                    offense_report['raised_alert_id'] = theHiveEsAlertId
                    offense_report['qradar_offense_id'] = offense['id']
                    offense_report['success'] = True
                    if offenseLastId < offense['id']:
                        offenseLastId = offense['id']
                except Exception as e:
                    logger.error('%s.allOffense2Alert failed', __name__, exc_info=True)
                    report['success'] = False
                    offense_report['success'] = False
                    offense_report['offense_id'] = offense['id']
                    if isinstance(e, ValueError):
                        errorMessage = json.loads(str(e))['message']
                        offense_report['message'] = errorMessage
                    else:
                        offense_report['message'] = str(e) + ": Couldn't raise alert in TheHive"
                report['offenses'].append(offense_report)
            else:
                logger.info('Offense %s already imported as alert', str(offense['id']))

        cfg['QRadar']['offense_id_after'] = str(offenseLastId)
        setConf(cfg)

    except Exception as e:
        logger.error('Failed to create alert from QRadar offense (retrieving offenses failed)', exc_info=True)
        report['success'] = False
        report['message'] = "%s: Failed to create alert from offense" % str(e)

    return report

def craftAlertDescription(offense):
    """
        From the offense metadata, crafts a nice description in markdown
        for TheHive
    """
    logger = logging.getLogger(__name__)
    logger.info('craftAlertDescription starts')


    cfg = getConf()
    QRadarIp = cfg.get('QRadar', 'server')
    url = ('https://' + QRadarIp + '/console/qradar/jsp/QRadar.jsp?' +
        'appName=Sem&pageId=OffenseSummary&summaryId=' + str(offense['id']))

    description = (
        '## Summary\n\n' +
        '|                         |               |\n' +
        '| ----------------------- | ------------- |\n' +
        '| **Offense ID**          | ' + str(offense['id']) + ' |\n' +
        '| **Description**         | ' + str(offense['description'].replace('\n', '')) + ' |\n' +
        '| **Offense Type**        | ' + str(offense['offense_type_str']) + ' |\n' +
        '| **Offense Source**      | ' + str(offense['offense_source']) + ' |\n' +
        '| **Destination Network** | ' + str(offense['destination_networks']) +' |\n' +
        '| **Source Network**      | ' + str(offense['source_network']) + ' |\n\n\n' +
        '\n\n\n\n```\n')

    for log in offense['logs']:
        description += log['utf8_payload'] + '\n'

    description += '```\n\n' + url

    return description
