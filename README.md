# WAPS_IES
WAPS Image Extraction Software (IES) is a software application for telemetry data processing,
image extraction, lost packet identification (due to communication link losses) and
retransmission request notification to the operator.

The software is intended to be used by MUSC to simplify WAPS PD image acquisition operations.
WAPS IES is able receive telemetry from up to 4 AECs inside BIOLAB simultaneously.
Each AEC contains 8 memory slots for images. Only one image is present in a memory slot at a time.
The IES is able to recognise transmission of images from different AECs and
memory slots including packet re-requests up to overwriting of the memory slot with a new image.
IES also differentiates colour (uCAM) and infrared (FLIR).

The WAPS IES is intended to receive a stream of CCSDS packets using TCP protocol by
connecting Yamcs TCP reverse link or any other comparable TCP server.
The IES selects the BIOLAB telemetry packets contains WAPS image data from the CCSDS stream.
The WAPS image data is sorted according EC address, memory slot and CCSDS packet time.

During AOS (Acquisition of Signal) the IES acquires TCP steam of live CCSDS packets.
During LOS (Loss of Signal) the live telemetry is stored on board the ISS and
is transmitted to ground using a different route. Therefore, the data cannot be acquired directly.
When the data becomes available it is processed the same way as live data.
This requires manual operator TCP stream retransmission to the IES.
This data is intended to be transmitted to a separate instance of the IES.
A configuration file can be used to simplify IES start-up.
A local database file is used to store all received BIOLAB TM packets containing WAPS image data.
The IES produces
1) command stack files for missing packet re-requests
2) 2) Reconstructed image files
3) 3) Log file with IES operational events.
4) A GUI provides visual indication to the operator.

