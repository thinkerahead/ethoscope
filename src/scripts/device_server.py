__author__ = 'luis'

import logging
import datetime
from optparse import OptionParser
from bottle import *
from pysolovideo.web_utils.control_thread import ControlThread
from pysolovideo.web_utils.helpers import get_machine_info, get_version
from pysolovideo.web_utils.record import RecordVideo
from subprocess import call

api = Bottle()

@api.route('/static/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root="/")

@api.route('/download/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root="/", download=filepath)


# fixme all this info should be in control.info
@api.get('/id')
def name():
    global control
    try:
        return {"id": control.info["id"]}

    except Exception as e:
        return {'error':e}

@api.post('/controls/<id>/<action>')
def controls(id, action):
    global control
    global record
    if id == machine_id:
            try:
                if action == 'start':

                    # getting the requested type of tracking
                    data = request.json
                    #TODO clean this, no needed now, node provices NTP service
                    #t = float(data['time'])
                    #set time, given in seconds from javascript, used in seconds for date
                    # FIXME This is needed on PI
                    #set_time = call(['date', '-s', '@' + str(t)])
                    #date = datetime.fromtimestamp(t)
                    # date_time = date.isoformat()

                    control = ControlThread(machine_id=machine_id, name=machine_name, version=version, video_file=INPUT_VIDEO,
                            psv_dir=PSV_DIR, draw_results = DRAW_RESULTS, max_duration=DURATION)
                    control.start()
                    return info(id)

                elif action == 'stop' or action == 'poweroff':
                    if control.info['status'] == 'running':
                        control.stop()
                        control.join()
                        logging.info("Stopping monitor")

                    if action == 'poweroff':
                        logging.info("Stopping monitor due to poweroff request")
                        logging.info("Powering off Device.")
                        # fixme, this is non blocking, is it ? maybe we should do something else
                        call('poweroff')
                    return info(id)

                elif action == 'start_record':
                    record = RecordVideo()
                    record.start()

                elif action == 'stop_record':
                    try:
                        if record is not None:
                            record.stop()
                        else:
                            logging.info("Can not stop video record. No video record started.")
                    except Exception as e:
                        logging.error("Exception on stopping record", e)

            except Exception as e:
                return {'error': "Error setting up control thread"+str(e)}

    else:
        return {'error': "Error on machine ID"}


@api.get('/data/<id>')
def info(id):
    if id == machine_id:
        return control.info
    else:
        return {'error': "Error on machine ID"}


@api.post('/update/<id>')
def update_system(id):
    if id == machine_id and control.info['status'] == 'stopped':
        try:
            device_update = subprocess.Popen(['git', 'pull'],
                                             cwd=GIT_WORKING_DIR,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
            stdout, stderr = device_update.communicate()
            if stderr != '':
                logging.error("Error on update:"+stderr)
            if stdout != '':
                logging.info("Update result:"+stdout)
            logging.info("Restarting script now. Systemd should restart script")
            close()

        except Exception as e:
            return {'error':e, 'updated':False}
    else:
        return {'error': 'Error on machine ID or not Stopped'}


def close(exit_status=0):
    global control
    if control is not None and control.is_alive():
        control.stop()
        control.join()
        control=None
    else:

        control = None
    os._exit(exit_status)

if __name__ == '__main__':

    parser = OptionParser()
    parser.add_option("-d", "--debug", dest="debug", default=False,help="Set DEBUG mode ON", action="store_true")
    parser.add_option("-p", "--port", dest="port", default=9000,help="port")
    parser.add_option("-b", "--branch", dest="branch", default="psv-package",help="the branch to work from")
    (options, args) = parser.parse_args()
    option_dict = vars(options)
    debug = option_dict["debug"]
    port = option_dict["port"]
    branch = option_dict["branch"]
    # import ConfigParser
    # config = ConfigParser.RawConfigParser(allow_no_value=True)
    # for loc in os.curdir, os.path.expanduser("~"), "/etc/pysolovideo/", os.environ.get("PSV_DEV_SERV_CONF"):
    #     try:
    #         with open(os.path.join(loc,"device_server.conf")) as source:
    #             config.readfp(source)
    #     except IOError:
    #         pass

    INPUT_VIDEO = None
    DURATION = None
    DRAW_RESULTS =False
    PSV_DIR = "/psv_data/results"
    GIT_WORKING_DIR = '/home/psv/pySolo-Video'

    MACHINE_ID_FILE = '/etc/machine-id'
    MACHINE_NAME_FILE = '/etc/machine-name'

    machine_id = get_machine_info(MACHINE_ID_FILE)
    machine_name = get_machine_info(MACHINE_NAME_FILE)


    if debug:
        import getpass
        DURATION = 60*60 * 100

        if getpass.getuser() == "quentin":
            INPUT_VIDEO = '/data/psv_misc/tube_monitor_validation/tube_monitor_validation_raw.mp4'
            PSV_DIR = "/psv_data/results/"
            #fixme Put your working directories
            GIT_WORKING_DIR = "./"


        elif getpass.getuser() == "asterix":
            PSV_DIR = "/tmp/psv_data"
            INPUT_VIDEO = '/data1/sleepMonitor_5days.avi'
            GIT_WORKING_DIR = "/data1/todel/pySolo-Device"

        elif getpass.getuser() == "psv" or getpass.getuser() == "root":
            INPUT_VIDEO = "/data/monitor_new_targets_short.avi"
            PSV_DIR = "/psv_data/results"
            GIT_WORKING_DIR = "/home/psv/pySolo-Video"
        else:
            raise Exception("where is your debugging video?")
        DRAW_RESULTS = True


    version = get_version(GIT_WORKING_DIR, branch)
    # fixme => the name should be hardcoded in a encrypted file? file.
    control = ControlThread(machine_id=machine_id, name=machine_name, version=version, video_file=INPUT_VIDEO,
                             psv_dir=PSV_DIR, draw_results = DRAW_RESULTS, max_duration=DURATION)


    try:
        run(api, host='0.0.0.0', port=port, server='cherrypy')

    except Exception as e:

        logging.error(e)
        close(1)
    finally:
        close()




