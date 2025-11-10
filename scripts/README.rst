Scripts directory
-----------------

Store here the scripts that your plugin will provide. Consider to use the ``chimera-(nameofscript)`` standard.

Don't forget to put your script on ``pyproject.toml`` by adding it on the ``[project.scripts]`` context. E. g.:

::

    [project.scripts]
    chimera-example = "chimera_template.cli.example:main"


