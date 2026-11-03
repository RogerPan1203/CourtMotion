# CourtMotion Tennis Robot: User Guide

This guide is for a robot that has already been set up. For everyday use, you do not need to open the code or type commands. Power the robot, connect the Raspberry Pi to your computer, and open the control page.

**Control page: <http://192.168.99.1:8080/>**

This page runs locally on the Raspberry Pi. Open it on the computer connected to the Pi. It is not the GitHub website, and there is currently no account or password to enter.

## Each time you use the robot

1. **Check the machine.** Make sure the power and motor cables are secure. Keep people and obstacles away from moving parts, and know where the physical power switch is.
2. **Connect and power it.** Plug in the robot and Raspberry Pi, connect the Pi to your computer with the usual cable, and give the Pi time to start.
3. **Open the control page.** In your computer's browser, go to **<http://192.168.99.1:8080/>**. Include `http://` and `:8080` exactly as shown.
4. **Check the connection.** The top right should say **Controller online · live**, and the status should say **STOPPED**. If you see **Disconnected · retrying**, check the connection before starting the motors.
5. **Set the output.** Use the **STP2 / Channel 2** and **STP4 / Channel 4** sliders. The motors do not start just because you move a slider. Both sliders begin at 30%; use a low setting for the first test or after changing cables.
6. **Start.** Click **START STP2 + STP4**. Check the values in the confirmation window, tick the safety box, then click **Confirm and start**. Both channels run together. To change the values while running, stop first, adjust the sliders, and start again.
7. **Stop.** Click **EMERGENCY STOP** and confirm the status returns to **STOPPED**. Turn off the machine's power when finished.

## If the page will not open

1. Check that the Raspberry Pi has power, has had time to start, and is still connected to the computer.
2. Open **<http://192.168.99.1:8080/>** on the connected computer. Use **http**, not **https**, and keep the **:8080** at the end.
3. Refresh the page and wait for **Controller online · live**. If it still does not connect, turn off the machine's power before checking the Pi connection or control service.

## Safety stop

If the page closes or loses contact for about 8 seconds, the Pi stops the motors automatically. Keep the control page open while the robot is running. If the page does not respond, use the physical power switch or disconnect power immediately. The stop button turns off all 16 controller outputs.

## About this GitHub repository

This repository backs up the control page and Raspberry Pi program. For everyday operation, use the **local control page above**; opening GitHub does not connect to or start the robot. The second motor output uses **Channel 4** (changed from Channel 5). Check the actual wiring before running the machine if its connections have been changed.
