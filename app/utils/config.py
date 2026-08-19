import sys
import app.utils.files
import app.utils.logger

CONFIG = {}
CONFIG["RTSP_USER"] = None
CONFIG["RTSP_PASS"] = None
CONFIG["RTSP_FEED"] = None
CONFIG["RTSP_URL"] = None
CONFIG["VIDEO_FPS"] = None
CONFIG["VIDEO_FPS"] = None
CONFIG["VIDEO_NAME"] = None
CONFIG["VIDEO_PATH"] = None


def process_configuration(config_file):
    global CONFIG

    configuration = app.utils.files.load_json_file(config_file)

    try:
        # RTSP
        CONFIG["RTSP_USER"] = configuration["rtsp"]["user"]
        CONFIG["RTSP_PASS"] = configuration["rtsp"]["password"]
        CONFIG["RTSP_FEED"] = configuration["rtsp"]["feed"]
        CONFIG["RTSP_URL"] = f"rtsp://{CONFIG['RTSP_USER']}:{CONFIG['RTSP_PASS']}@{CONFIG['RTSP_FEED']}"
    except KeyError as e:
        app.utils.logger.eprint(f"Mandatory config option missing: {e}")
        sys.exit(1)

    try:
        CONFIG["VIDEO_NAME"] = configuration["rtsp"]["save_video"]["name"]
        CONFIG["VIDEO_PATH"] = configuration["rtsp"]["save_video"]["path"]
        CONFIG["VIDEO_FPS"] = int(configuration["rtsp"]["save_video"]["optional_force_fps"])
    except KeyError:
        app.utils.logger.eprint("Video won't pe saved")

