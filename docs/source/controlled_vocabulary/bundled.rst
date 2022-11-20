Bundled Controlled Vocabularies
-------------------------------

:mod:`psims` ships bundled copies of several controlled vocabularies
for use when an internet connection isn't available. These versions
change periodically with each release. If you have an application that
requires a fixed version, see the discussion around :class:`~.OBOCache`
to specify where to store your specific version.

.. exec::

    from psims.controlled_vocabulary.vendor import version_table
    from rst_table import as_rest_table

    rows = [("Controlled Vocabulary", "Version")]
    for name, props in sorted(version_table().items()):
        rows.append((
            "**%s**" % (key.split(".")[0], ),
            props['version'], ))

    print(as_rest_table(rows))