Chimera QHY600 Plugin
=====================

Chimera camera plugin for **QHY600M / QHY600PH-M** (Sony IMX455) cameras.

Instruments supported
---------------------

- **QHY600M / QHY600PH-M** (monochrome)

Installation
------------

From this folder:

```bash
pip install -e .
```

Requirements
------------

### Real camera usage

You need the QHYCCD SDK installed so `libqhyccd.so` is available.

If the library is not on the system loader path, set one of these environment variables:

- `QHYCCD_SDK_PATH`
- `QHYCCD_LIB_PATH`

Or provide an explicit path in the Chimera config via `sdk_library_path`.

Configuration example
---------------------

Add to your `chimera.config`:

```yaml
camera:
  type: QHY600
  name: qhy600m
  readout_mode_index: 1
  gain: 10.0
  # sdk_library_path: /usr/local/lib/libqhyccd.so
```

Local testing (no hardware)
---------------------------

For local development without the QHY SDK or a camera connected, enable the mock SDK:

```yaml
camera:
  type: QHY600
  name: qhy600m
  use_mock_sdk: true
```

This mock prints each SDK call and generates a synthetic image that changes with ROI/binning/exposure/gain.

Contact
-------

Chimera discussion list: https://groups.google.com/forum/#!forum/chimera-discuss
