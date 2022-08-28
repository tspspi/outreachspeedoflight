# Outreach project utility: Speed of light

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
