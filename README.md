# Outreach project utility: Speed of light

_Work in progress_

This is the frontend to the _speed of light_ outreach project. This project
has been developed to measure the speed of light similar to the idea
that Hippolyte Fizeau developed in 1848. In contrast to his experiment
in this case a little cheat is used - a bicycle works as chopper to produce
a sharp difference in light intensity of a laser source. The light travels
through two arms of the experiment - one being only a few meters away from
the chopper, the other being about hundred meters away. The signal of both
pulses is recorded on photodiodes and sampled by a fast oscilloscope (this
is where the cheating comes in - we have a definition of time and fast direct
sampling).

Since this project has been developed to increase the interest in science
and let people participate actively during exhibitions it's by no way a
precision measurement - it's more of a (working) experiment that people
can look at, play with and grasp the idea of light traveling at finite speeds.

This application:

* Gathers data from the oscilloscope
* Visualizes the samples
* Calculates a cross correlation of the symmetrized periodicalized recorded
  function
* Estimates the speed of light from this correlation function by doing
  a simple peak search
* Does averaging over the estimated speed of light and visualized this.

## Experimental setup

The experimental setup consists of two basic parts:

* A chopper assembly - where a bicycle is used (or any other kind of chopper)
* A beamsplitter and photodiode assembly as well as a long beamline

![Chopper assembly](https://raw.githubusercontent.com/tspspi/outreachspeedoflight/master/doc/assembly_chopper.png)

![Beamsplitter and photodiode assembly](https://raw.githubusercontent.com/tspspi/outreachspeedoflight/master/doc/assembly_diodeandcoupling.png)

# Example screenshots

## Running the embedded DAQ simulation

![Running simulation](https://raw.githubusercontent.com/tspspi/outreachspeedoflight/master/doc/screenshot_simulation.png)


# Configuration files

## daq.conf

The data acquisition module configures the communication with the MSO5000 oscilloscope.

Example configuration:

```
{
	"osci" : {
		"ip" : "10.0.0.196",
		"port" : 5555,
		"sperdiv" : 1e-6,
		"trigch" : 1,
		"triglvl" : 0.5,
		"ch1" : {
			"offset" : 0,
			"scale" : 0.5
		},
		"ch2" : {
			"offset" : 0,
			"scale" : 0.1
		},
		"maxqueryrate" : 2
	},
	"chopper" : {
		"diameter" : 68e-2
	},
	"path" : {
		"length" : 100,
		"n" : 1.4
	},
	"loglevel" : "debug",
	"mode" : "continuous"
}
```

The ```osci``` section configured the MSO5000 oscilloscope:

* Connectivity:
   * The ```ip``` field can be either the IP or hostname as string
   * ```port``` is optional and defaults to ```5555```
* Optional _Horizontal axis_ (time) configuration:
   * ```sperdiv``` specifies the seconds per division on the horizontal axis.
     This has to be a value supported by the oscilloscope
* Optional _Trigger_ configuration:
   * ```trigch``` selects a channel (1 or 2) for the trigger to act on
   * ```triglvl``` selects the trigger level in volts.
* Optional channel configuration ```ch1``` and ```ch2```:
   * One can specify an ```offset``` in volts
   * and a ```scale``` specified in _volts per division_ that has to be
     a supported value by the oscilloscope
* A optional maximum query rate in Hz (i.e. queries per second) that can
  be used to limit the amount of queries to the oscilloscope since at some
  point it won't update it's own local display anymore due to priorization
  of network queries. When not specified the application queries as fast
  as possible.

The ```chopper``` section configures the chopper that is used. For our
experimental setup this can be a bicycle or a simple wodden wheel:

* ```diameter``` configures the diameter of the wheel in meters. This is only
  used for velocity calculation from trigger rate assuming that only one trigger
  is issued per cycle.

An important configuration is the ```path```. This describes the free path
the light pulse is traveling through. One can describe the ```length``` in
meters and the refractive index ```n``` (1 for air or vacuum or about 1.4 for
glass fibers)

At last one can select between two modes of operation using the ```mode```
parameter:

* ```triggered``` uses the scope in single trigger mode and re-arms when ready to
  gather more data. This ensures that both channels correspond to the same
  event but looks less real time on the oscilloscopes local display.
* ```continuous``` continuously samples on the scope and queries data as fast
  as possible.

## gui.conf

The user interface can be configured using ```gui.conf```. This allows one to configure:

* The number of last measurements to be shown using ```lastsamples```
* The number of measurements to include in rolling average ```averagecount```

In addition one can directly configure some layout parameters:

* ```plotsize``` with ```x``` and ```y``` parameters directly scales all plots
* ```mainwindowsize``` with ```x``` and ```y``` parameters scales the main window
  as initially created.

Note that invalid setting of those parameters might clip some graphs or cause
some strange behaviour of the user interface.