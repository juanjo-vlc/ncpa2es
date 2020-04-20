#!/usr/bin/env python3
"""
Gets data from Nagios Cross-Platform Agent and loads it
on elasticsearch
"""
__version__ = "RC1"
__author__  = "Juanjo Garcia"

#TODO: remove dependency from ncpa
#TODO: manage ncpa host failure
#TODO: manage es host failure
#TODO: upload to github
#TODO: convert to a long running process/systemd service
#TODO: reload by signal

import check_ncpa as ncpa
import yaml
import logging
import sys
import json
import datetime
from optparse import Values
import requests
from urllib.error import URLError
import re




logger = logging.getLogger(__name__)
logger.setLevel(logging.WARN)
logger.addHandler(logging.StreamHandler())

def parse_config(configfile='config.yml'):
    """
        Loads the config file

        Arguments:
            - configfile: File to parse, default config.yml
        Returns:
            Configuration dict
        Raises:
            YAMLError if config file is not a valid YML
            ValueError if configuration components are missing
    """

    global logger
    with open(configfile, 'r') as c:
        try:
            config = yaml.safe_load(c)
        except yaml.YAMLError as e:
            logger.fatal(e)
            raise e
    if not "community_string" in config or config['community_string'] is None:
        raise ValueError("community_string is mandatory")
    
    if not "hosts" in config:
        config['hosts'] = {}

    if not "es_hosts" in config:
        config['es_hosts'] = {}
    
    if not "port" in config:
        config['port'] = 5693

    if not "es_security_enabled" in config:
        config['es_security_enabled'] = False

    if "debug" in config and config['debug']:
        logger.setLevel(logging.DEBUG)
    return config

def _flattern(item):
    """ Flatterns an item """
    doc = {}
    for k,v in item.items():
        if isinstance(v, list):
            doc[k] = v[0]
            doc[k + '_unit'] = v[-1]
        else:                    
            doc[k] = v
    return doc

def prepare_documents(host, ncpadata):
    """
        Converts ncpa data into ES compatible document

        Arguments:
            host: host which's data is being converted
            ncpadata: data to be converted
        
        Returns:
            A list of flat documents ready to be stored on ES
    """
    data = ncpadata['root']
    utc_datetime = datetime.datetime.utcfromtimestamp(int(data['system']['time'])).strftime('%Y-%m-%dT%H:%M:%S.%f')
    common = {
        '@timestamp': utc_datetime,
        'host': data['system']['node'],
        'address': host['address']
    }
    logger.debug(common)
    documents = []
    try:
        for name, item in data['disk']['logical'].items():
            doc = _flattern(item)
            doc['name'] = name.replace("|", "/")
            doc['type'] = 'disk_logical'
            doc.update(common)
            documents.append(doc)
    except KeyError:
        pass
    
    try:
        for name, item in data['disk']['physical'].items():
            if name.startswith('ram'):
                continue
            doc = _flattern(item)
            doc['name'] = name
            doc['type'] = 'disk_physical'
            doc.update(common)
            documents.append(doc)
    except KeyError:
        pass

    try:
        for name, item in data['memory'].items():
            doc = _flattern(item)
            doc['name'] = name
            doc['type'] = 'memory'
            if 'available' in doc:
                doc['available_percent'] = doc['available'] / doc['total'] * 100
            doc.update(common)
            documents.append(doc)
    except KeyError:
        pass

    try:
        for name, item in data['interface'].items():
            doc = _flattern(item)
            doc['name'] = name
            doc['type'] = 'interface'
            doc.update(common)
            documents.append(doc)
    except KeyError:
        pass


    try:
        for i in range(0, data['cpu']['count'][0][0]):
            doc = {
                'name': f"CPU{i}",
                'type': 'cpu',
                'user': data['cpu']['user'][0][i],
                'system': data['cpu']['system'][0][i],
                'idle': data['cpu']['idle'][0][i],
                'percent': data['cpu']['percent'][0][i]
            }
            doc.update(common)
            documents.append(doc)
    except KeyError:
        pass

    try:
        for item in data['processes']:
            doc = _flattern(item)
            doc['type'] = 'process'
            doc.update(common)
            documents.append(doc)
    except KeyError:
        pass

    return documents
    



def store_data(data, config):
    """
    Stores data on ES cluster

    Arguments:
        - data: data to be stored
        - config: global configuration
    """
    post_data(data, config)


def post_data(data, config):
    """Posts data to ES server

        Inspired by https://github.com/trevorndodds/elasticsearch-metrics

        Parameters
        ----------
            data: data to be posted
            config: configuration data
    """

    #TODO: round robin in es_hosts
    utc_datetime = datetime.datetime.utcnow()
    url_parameters = {'cluster': config['es_hosts'][0], 'index': config['es_index'],
        'index_period': utc_datetime.strftime("%Y.%m.%d"), }
    url = "%(cluster)s/%(index)s-%(index_period)s/message/_bulk" % url_parameters
    headers = {'Content-Type': 'application/x-ndjson'}
    newdata = [val for pair in zip([{'index': {}}] * len(data), data) for val in pair]
    bulkdata = "\n".join(map(json.dumps, newdata))

    try:
        if config['es_security_enable']:
            response = requests.post(url, headers=headers, auth=(config['es_username'],config['es_password']), data=bulkdata)
        else:
            response = requests.post(url, headers=headers, data=data)
    except Exception as e:
        logger.error("Error:  {0}".format(str(e)))


if __name__ == "__main__":
    config = parse_config()
    logger.debug(config)
    for (index, host) in config['hosts'].items():
        try:
            logger.debug(f"Processing host {index}")
            if not 'address' in host or host['address'] is None:
                host['address'] = index
            options = Values(defaults={'list':True, 'metric': None, 'arguments': None, 'units': 'k', 'queryargs': None, 'verbose': False, 'secure': False})
            options.hostname = host['address']
            options.port = config['port'] if not 'port' in host or host['port'] is None else host['port']
            options.token = config['community_string'] if not 'community_string' in host or host['community_string'] is None else host['community_string']
            info_json = ncpa.get_json(options)
            
            options.metric = 'processes'
            options.arguments = ''
            info_json['root'].update(ncpa.get_json(options))

            options.metric = 'cpu'
            options.arguments = 'percent'
            #DEBUG print(ncpa.get_url_from_options(options))
            info_json['root']['cpu'].update(ncpa.get_json(options))
            #DEBUG print(json.dumps(info_json['root']['memory'],indent=4,sort_keys=True))

            options.metric = 'interface'
            options.queryargs = 'delta=1'
            for i in info_json['root']['interface']:
                options.arguments = i
                info_json['root']['interface'].update(ncpa.get_json(options))
            
            options.metric = 'disk/physical'
            options.queryargs = 'delta=1'
            for i in info_json['root']['disk']['physical']:
                if not re.match("/(ram|loop)/", i): 
                    options.arguments = i
                    info_json['root']['disk']['physical'].update(ncpa.get_json(options))
                else:
                    info_json['root']['disk']['physical'].remove(i)

            #DEBUG print(json.dumps(info_json['root']['disk']['physical'],indent=4,sort_keys=True))

            docs = prepare_documents(host, info_json)
            #DEBUG print(json.dumps(docs,indent=4,sort_keys=True))
            logger.debug(f"Total records for {options.hostname}: {len(docs)}")
            store_data(docs, config)
        except OSError as e:
            logger.error(f"Errno: {e.errno}; msg: {e.strerror}")
            if e.errno == 113:
                logger.warn(f"{options.hostname} Not reachable")
        except URLError as e:
            logger.error(e)





