# CourtMotion

Local Raspberry Pi control panel for a tennis robot. The web page controls PCA9685 channels **2 and 4** together. The server listens at `http://192.168.99.1:8080/` on the Pi's local network.

## Files

- `index.html` — control page with separate output sliders and a start confirmation.
- `control_server.py` — local HTTP API, heartbeat watchdog, and emergency stop.
- `pca_ch1_30pct.py` — continuous output on channels 2 and 4 (the historical filename is retained for deployment compatibility).
- `pca_sweep_independant.py` — optional synchronized ramp on channels 2 and 4.
- `pca_all_off.py` — resets all 16 PCA9685 outputs to zero.
- `tennis` — command-line start, status, and stop wrapper.
- `tennis-control.service` — systemd service for the web controller.
- `deploy.sh` — backs up and deploys the controller to an existing Pi installation.

## Deployment layout

The scripts expect `/home/pi/Tennis/` to contain the Python files, with `index.html` at `/home/pi/Tennis/web/index.html` and `tennis` at `/home/pi/.local/bin/tennis`. Enable I2C and install the Raspberry Pi Python libraries `adafruit-blinka` and `adafruit-circuitpython-pca9685`. Install `tennis-control.service` as a systemd unit and start it after the files are in place.

For updates to an existing installation, configure the `tennispi` SSH alias and run `./deploy.sh tennispi`. Deployment stops all outputs, saves a backup under `/home/pi/Tennis/backup_slider_*`, installs the updated files, restarts the service, and checks `/api/status`.

The web page requires a safety confirmation before starting. It automatically stops after eight seconds without a heartbeat. Keep a physical power cutoff within reach when operating the robot.
