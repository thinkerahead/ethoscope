__author__ = 'quentin'


import os
import logging
import datetime
import urllib2
import json
import traceback
import random
import subprocess
import time

try:
    from netifaces import ifaddresses, AF_INET, AF_LINK
except:
    logging.warning("Could not load netifaces. This is needed for node stuff")
try:
    import concurrent
    import concurrent.futures as futures
except:
    logging.warning("Could not load concurrent. This is needed for node stuff")

class UnexpectedAction(Exception):
    pass
class NotNode(Exception):
    pass

def get_commit_version(commit):
    return {"id":str(commit),
            "date":datetime.datetime.utcfromtimestamp(commit.committed_date).strftime('%Y-%m-%d %H:%M:%S')
                    }
def assert_node(is_node):
    if not is_node:
        raise NotNode("This device is not a node.")

def close(exit_status=0):
    logging.info("Closing server")
    os._exit(exit_status)

def get_machine_info(path):
    """
    Reads the machine NAME file and returns the value.
    """
    try:
        with open(path,'r') as f:
            info = f.readline().rstrip()
        return info
    except Exception as e:
        logging.warning(traceback.format_exc(e))
        return 'Debug-'+str(random.randint(1,100))


def scan_one_device(ip, timeout=2, port=8888, page="id"):
    """
    :param url: the url to parse
    :param timeout: the timeout of the url request
    :param port: the port to request
    :return: The message, parsed as dictionary. the "ip" field is also added to the result.
    If the url could not be reached/parsed, (None,None) is returned
    """


    url="%s:%i/%s" % (ip, port, page)
    try:
        req = urllib2.Request(url)
        f = urllib2.urlopen(req, timeout=timeout)
        message = f.read()

        if not message:
            logging.error("URL error whist scanning url: %s. No message back." % url )
            raise urllib2.URLError("No message back")
        try:
            resp = json.loads(message)
            return (resp['id'],ip)
        except ValueError:
            logging.error("Could not parse response from %s as JSON object" % url )

    except urllib2.URLError:
        pass
        # logging.error("URL error whist scanning url: %s. Server down?" % url )

    except Exception as e:
        logging.error("Unexpected error whilst scanning url: %s" % url )
        raise e

    return None, ip


def update_dev_map_wrapped (devices_map,id, what="data",type=None, port=9000, data=None,result_main_dir="/ethoscope_results"):
    """
    Just a routine to format our GET urls. This improves readability whilst allowing us to change convention (e.g. port) without rewriting everything.

    :param id: machine unique identifier
    :param what: e.g. /data, /control
    :param type: the type of request for POST
    :param port:
    :return:
    """

    ip = devices_map[id]["ip"]

    request_url = "{ip}:{port}/{what}/{id}".format(ip=ip,port=port,what=what,id=id)
    if type is not None:
        request_url = request_url + "/" + type


    req = urllib2.Request(url=request_url, data = data, headers={'Content-Type': 'application/json'})

    logging.info("requesting %s" % request_url)

    try:
        f = urllib2.urlopen(req)
        message = f.read()

        if message:
            data = json.loads(message)

            if not id in devices_map:
                logging.warning("Device %s is not in device map. Rescanning subnet..." % id)
                generate_new_device_map(result_main_dir=result_main_dir)
            try:
                devices_map[id].update(data)
                return data

            except KeyError:
                logging.error("Device %s is not detected" % id)
                raise KeyError("Device %s is not detected" % id)

    except urllib2.httplib.BadStatusLine as e:
        logging.error('BadlineSatus, most probably due to update device and auto-reset')
        raise e

    except urllib2.URLError as e:
        if hasattr(e, 'reason'):
            logging.error('We failed to reach a server.')
            logging.error('Reason: '+ str(e.reason))
            raise e
        elif hasattr(e, 'code'):
            logging.error('The server couldn\'t fulfill the request.')
            logging.error('Error code: '+ str(e.code))
            raise e

    return devices_map


def generate_new_device_map(local_ip, ip_range=(2,64), result_main_dir="/ethoscope_results"):
        devices_map = {}
        subnet_ip = local_ip.split(".")[0:3]
        subnet_ip = ".".join(subnet_ip)

        t0 = time.time()

        logging.info("Scanning attached devices")

        scanned = [ "%s.%i" % (subnet_ip, i) for i in range(*ip_range) ]
        urls= ["http://%s" % str(s) for s in scanned]


        # We can use a with statement to ensure threads are cleaned up promptly
        with futures.ThreadPoolExecutor(max_workers=64) as executor:
            # Start the load operations and mark each future with its URL

            fs = [executor.submit(scan_one_device, url) for url in urls]
            for f in concurrent.futures.as_completed(fs):

                try:
                    id, ip = f.result()
                    devices_map[id] = {"ip":ip, "id":id}

                except Exception as e:
                    logging.error("Error whilst pinging url")
                    logging.error(traceback.format_exc(e))

        if len(devices_map) < 1:
            logging.warning("No device detected")
            return  devices_map

        all_devices = sorted(devices_map.keys())
        logging.info("DEVICE ID -> Detected %i devices in %i seconds:\n%s" % (len(devices_map),time.time() - t0, str(all_devices)))
        # We can use a with statement to ensure threads are cleaned up promptly

        with futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Start the load operations and mark each future with its URL
            fs = {}
            for id in devices_map.keys():
                fs[executor.submit(update_dev_map_wrapped,devices_map, id)] = id

            for f in concurrent.futures.as_completed(fs):
                try:
                    id = fs[f]
                    data = f.result()
                    devices_map[id].update(data)

                except Exception as e:
                    logging.error("Could not get data from device %s :" % id)
                    logging.error(traceback.format_exc(e))
                    del devices_map[id]
        all_devices = sorted(devices_map.keys())
        logging.info("DEVICE INFO -> Detected %i devices in %i seconds:\n%s" % (len(devices_map),time.time() - t0, str(all_devices)))


 # We can use a with statement to ensure threads are cleaned up promptly
        with futures.ThreadPoolExecutor(max_workers=64) as executor:
            # Start the load operations and mark each future with its URL
            fs = {}
            for id in devices_map.keys():
                device = devices_map[id]
                fs[executor.submit(make_backup_path, device,result_main_dir)] = id

            for f in concurrent.futures.as_completed(fs):
                try:
                    id = fs[f]
                    path = f.result()
                    if path:
                        devices_map[id]["backup_path"] = path

                except Exception as e:
                    logging.error("Error whilst getting backup path for device")
                    logging.error(traceback.format_exc(e))


        for d in devices_map.values():
            d["time_since_backup"] = get_last_backup_time(d)


        all_devices = sorted(devices_map.keys())
        logging.info("BACKUP_PATH -> Detected %i devices in %i seconds:\n%s" % (len(devices_map),time.time() - t0, str(all_devices)))

        return devices_map

def updates_api_wrapper(ip,id, what="check_update",type=None, port=8888, data=None):
    response = ''
    request_url = "{ip}:{port}/{what}/{id}".format(ip=ip,port=port,what=what,id=id)

    # if type is not None:
    #     request_url = request_url + "/" + type
    if data is not None:
        data= json.dumps(data)

    req = urllib2.Request(url=request_url, data = data, headers={'Content-Type': 'application/json'})

    logging.info("requesting %s" %request_url)

    try:
        f = urllib2.urlopen(req)
        message = f.read()

        if message:
            response = json.loads(message)

    except urllib2.httplib.BadStatusLine as e:
        logging.error('BadlineSatus, most probably due to update device and auto-reset')
        raise e

    except urllib2.URLError as e:
        if hasattr(e, 'reason'):
            logging.error('We failed to reach a server.')
            logging.error('Reason: '+ str(e.reason))
            raise e
        elif hasattr(e, 'code'):
            logging.error('The server couldn\'t fulfill the request.')
            logging.error('Error code: '+ str(e.code))
            raise e

    return response

def _reload_daemon(name):
    subprocess.call(["systemctl","restart", name])

def reload_node_daemon():
    _reload_daemon("ethoscope_node")

def reload_device_daemon():
    _reload_daemon("ethoscope_device")




def get_local_ip(local_router_ip = "192.169.123.254", node_subnet_address="1"):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((local_router_ip ,80))
    except socket.gaierror:
        raise Exception("Cannot find local ip, check your connection")


    ip = s.getsockname()[0]
    s.close()

    router_ip = local_router_ip.split(".")
    ip_list = ip.split(".")
    if router_ip[0:3] != ip_list[0:3]:
        raise Exception("The local ip address does not match the expected router subnet: %s != %s" % (str(router_ip[0:3]), str(ip_list[0:3])))
    if  ip_list[3] != node_subnet_address:
        raise Exception("The ip of the node in the intranet should finish by %s. current ip = %s" % (node_subnet_address, ip))
    return ip


def get_internet_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        s.connect(("google.com", 80))
    except socket.gaierror:
        raise Exception("Cannot find internet (www) connection")

    ip = s.getsockname()[0]
    s.close()
    return ip
