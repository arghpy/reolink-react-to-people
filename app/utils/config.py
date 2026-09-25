import sys
import app.utils.files
import app.utils.logger

CONFIG = {}
CONFIG["RTSP_USER"] = None
CONFIG["RTSP_PASS"] = None
CONFIG["VIDEO_NAME"] = None
CONFIG["VIDEO_PATH"] = None


def process_configuration(config_file):
    global CONFIG

    configuration = app.utils.files.load_json_file(config_file)

    try:
        # RTSP
        CONFIG["RTSP_USER"] = configuration["rtsp"]["user"]
        CONFIG["RTSP_PASS"] = configuration["rtsp"]["password"]
    except KeyError as e:
        app.utils.logger.eprint(f"Mandatory config option missing: {e}")
        sys.exit(1)

    try:
        CONFIG["VIDEO_NAME"] = configuration["rtsp"]["save_video"]["name"]
        CONFIG["VIDEO_PATH"] = configuration["rtsp"]["save_video"]["path"]
    except KeyError:
        app.utils.logger.eprint("Video won't pe saved")
