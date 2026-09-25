#!/usr/bin/env python3
"""React to a push notification from a Reolink camera"""
from http.server import HTTPServer
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests
import app.integrations.webhook
import app.integrations.reolink
import app.integrations.mediamtx
import app.utils.config
import app.integrations.ntfy
import app.utils.help
import app.utils.logger
import app.utils.files


# Args
ARGS = {}
ARGS["CONFIG"]= False
ARGS["CONFIG_ARG"]= None
ARGS["NTFY_TAG"]= False
ARGS["NTFY_TAG_ARG"]= None
ARGS["WEBHOOK"]= False
ARGS["WEBHOOK_ARG"]= None
ARGS["CAMERA"]= False
ARGS["CAMERA_ARG"]= None


def parse_arguments(argv):
    """Parse command line arguments"""
    global ARGS
    passed_args = argv[1:]

    while len(passed_args) > 0:
        if passed_args[0] == "--help":
            app.utils.help.usage(argv)
            sys.exit(0)
        elif passed_args[0] == "--config":
            ARGS["CONFIG"] = True
            passed_args.pop(0)
            ARGS["CONFIG_ARG"] = str(passed_args[0])
        elif passed_args[0] == "--ntfy-tag":
            ARGS["NTFY_TAG"] = True
            passed_args.pop(0)
            ARGS["NTFY_TAG_ARG"] = str(passed_args[0])
        elif passed_args[0] == "--webhook-port":
            ARGS["WEBHOOK"] = True
            passed_args.pop(0)
            ARGS["WEBHOOK_ARG"] = int(passed_args[0])
        elif passed_args[0] == "--camera":
            ARGS["CAMERA"] = True
            passed_args.pop(0)
            ARGS["CAMERA_ARG"] = str(passed_args[0])
        else:
            app.utils.logger.eprint(f"Invalid option: {passed_args[0]}")
            app.utils.help.usage(argv)
            sys.exit(0)
        passed_args.pop(0)

    if not ARGS["CONFIG"] or ARGS["CONFIG_ARG"] is None:
        app.utils.logger.eprint("configuration not specified.")
        app.utils.help.usage(sys.argv)
        sys.exit(1)

    if not ARGS["NTFY_TAG"] or ARGS["NTFY_TAG_ARG"] is None:
        app.utils.logger.eprint("ntfy tag not specified")
        app.utils.help.usage(sys.argv)
        sys.exit(1)

    if not ARGS["WEBHOOK"] or ARGS["WEBHOOK_ARG"] is None:
        app.utils.logger.eprint("webhook not specified")
        app.utils.help.usage(sys.argv)
        sys.exit(1)

    if not ARGS["CAMERA"] or ARGS["CAMERA_ARG"] is None:
        app.utils.logger.eprint("camera not specified")
        app.utils.help.usage(sys.argv)
        sys.exit(1)



if __name__ == "__main__":
    parse_arguments(sys.argv)
    app.utils.config.process_configuration(ARGS["CONFIG_ARG"])

    webhook_reader_thread = threading.Thread(
        target=lambda: HTTPServer(("0.0.0.0", ARGS["WEBHOOK_ARG"]), app.integrations.webhook.Handler).serve_forever(),
        daemon=True
    )
    webhook_reader_thread.start()
    app.utils.logger.iprint(f"Started listening on {ARGS['WEBHOOK_ARG']}")

    reolink_token, reolink_token_expiration = app.integrations.reolink.login(ARGS["CAMERA_ARG"],
                                                                             app.utils.config.CONFIG["RTSP_USER"],
                                                                             app.utils.config.CONFIG["RTSP_PASS"])
    if not reolink_token:
        app.utils.logger.eprint(f"Could not login to Reolink camera: {ARGS['CAMERA_ARG']}")
        sys.exit(1)

    # Create directory structure
    now = datetime.now(ZoneInfo("Europe/Bucharest"))
    next_now = now + timedelta(hours=1)

    base_video_path = app.utils.config.CONFIG["VIDEO_PATH"]
    now_video_path = (
        f"{base_video_path}"
        f"{now.strftime('/%Y/%m/%d/%H')}"
    )
    next_video_path = (
        f"{base_video_path}"
        f"{next_now.strftime('/%Y/%m/%d/%H')}"
    )

    SAVE_IMAGE_PATH = f"{now_video_path}/captures"
    NEXT_SAVE_IMAGE_PATH = f"{next_video_path}/captures"
    os.makedirs(SAVE_IMAGE_PATH, exist_ok=True)
    os.makedirs(NEXT_SAVE_IMAGE_PATH, exist_ok=True)


    # MAIN LOOP
    while True:
        if datetime.now(ZoneInfo("Europe/Bucharest")).hour == next_now.hour:
            # Create directory structure
            now = datetime.now(ZoneInfo("Europe/Bucharest"))
            next_now = now + timedelta(hours=1)
            prev_now = now - timedelta(hours=1)

            now_video_path = (
                f"{base_video_path}"
                f"{prev_now.strftime('/%Y/%m/%d/%H')}"
            )
            next_video_path = (
                f"{base_video_path}"
                f"{next_now.strftime('/%Y/%m/%d/%H')}"
            )

            SAVE_IMAGE_PATH = f"{now_video_path}/captures"
            NEXT_SAVE_IMAGE_PATH = f"{next_video_path}/captures"
            os.makedirs(NEXT_SAVE_IMAGE_PATH, exist_ok=True)

            # A date object is immutable; all operations produce a new object
            start = prev_now.replace(minute=0, second=0, microsecond=0).isoformat()
            end = now.replace(minute=0, second=0, microsecond=0).isoformat()
            download_hour_recording = threading.Thread(
                target=app.integrations.mediamtx.download_recording,
                args=(ARGS['CAMERA_ARG'], start, end, f"{now_video_path}/{ARGS['CAMERA_ARG']}.mp4"),
                daemon=True,
            )
            download_hour_recording.start()

        if (reolink_token_expiration - time.time()) < 100:
            reolink_token, reolink_token_expiration = app.integrations.reolink.login(ARGS["CAMERA_ARG"], app.utils.config.CONFIG["RTSP_USER"], app.utils.config.CONFIG["RTSP_PASS"])
            if not reolink_token:
                app.utils.logger.eprint(f"Could not log in to Reolink camera: {ARGS['CAMERA_ARG']}")
                sys.exit(1)

        if app.integrations.webhook.camera_alert():
            now = datetime.now(ZoneInfo("Europe/Bucharest"))
            minute = now.minute
            second = now.second

            SAVE_IMAGE_NAME = (
                f"{app.utils.config.CONFIG['VIDEO_NAME']}"
                f"_{minute}"
                f":{second}"
                f".jpeg"
            )
            SAVE_IMAGE = f"{SAVE_IMAGE_PATH}/{SAVE_IMAGE_NAME}"

            img = app.integrations.reolink.get_snapshot(ARGS["CAMERA_ARG"], reolink_token)
            if img is not None:
                compressed_img = app.integrations.ntfy.compress_for_ntfy(img)
                with open(SAVE_IMAGE, "wb") as f:
                    f.write(compressed_img)
                app.utils.logger.iprint(f"Saved snapshot to {SAVE_IMAGE}")
            else:
                app.utils.logger.eprint(f"Failed to save snapshot to {SAVE_IMAGE}")

            try:
                # Sent on the docker network to container
                app.integrations.ntfy.send_ntfy(
                    "http://ntfy", ARGS["NTFY_TAG_ARG"],
                    "Person detected", "",
                    SAVE_IMAGE, "detection.jpeg",
                )
                app.utils.logger.iprint("Successfully sent ntfy")
            except requests.exceptions.HTTPError:
                app.utils.logger.eprint("Failed to send ntfy")
