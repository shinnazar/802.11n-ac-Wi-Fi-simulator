# 802.11n-ac-Wi-Fi-simulator
This is an IEEE 802.11n/ac Wi-Fi simulator. It can also be used to simulate IEEE 802.11a/b/g by changing a few parameters. 

What it supports:
* DCF operations
* A-MPDU aggregation
* Unsaturated and saturated traffic generation

What it doesn't support:
* Multi-cell environment
* Noisy channel condition
* Interference model
* Block acknowledgement window sliding
  
The project includes the following files:
* constants.py - includes values for parameters
* station.py - includes Station class which imitates wi-fi stations
* main.py - includes Simulator class which implements simulation logic
* script.py - script file to run the simulation scenario
