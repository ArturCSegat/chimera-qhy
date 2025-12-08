Chimera QHY Repository
=======================

Repository of Chimera instruments and controllers for [QHY products](https://www.qhyccd.com/).

Instruments Supported
-------

* **QHY600M**: a monochrome, back-illuminated, high-sensitivity, CMOS technology (low noise and high-speed readout), astronomical imaging camera. The QHY600PH-M uses SONY IMX455, a BSI full frame (35mm format) sensor with 3.76um pixels and native 16-bit ([product web site](https://www.qhyccd.com/astronomical-camera-qhy600/)).



chimera-template plugin
=======================

This is a template plugin for the chimera observatory control system
https://github.com/astroufsc/chimera.

Usage
-----

Rename chimera_template for your plugin name. It is important that the plugin
name must start with chimera\_ to be found by chimera. Instruments and
controllers must follow the standard ``chimera_(plugin_name)/(instruments|controllers)/(plugin).py``

The class inside ``(plugin).py`` should be named Plugin (with CamelCase letters).

For more info: https://github.com/astroufsc/chimera/blob/master/docs/site/chimerafordevs.rst#chimera-objects


Installation
------------

Installation instructions. Dependencies, etc...

::

   pip install -U chimera_template

or

::

    pip install -U git+https://github.com/astroufsc/chimera-template.git


Configuration Example
---------------------

Here goes an example of the configuration to be added on ``chimera.config`` file.

::

    instrument:
        name: model
        type: Example


Tested Hardware (for instruments)
---------------------------------

This plugin was tested on these hardware:

* Hardware example 1, model 2
* Hardware example 2, model 3


Contact
-------

For more information, contact us on chimera's discussion list:
https://groups.google.com/forum/#!forum/chimera-discuss

Bug reports and patches are welcome and can be sent over our GitHub page:
https://github.com/astroufsc/chimera-template/
