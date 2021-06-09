Controlled Vocabulary Objects
-----------------------------

.. automodule:: psims.controlled_vocabulary.controlled_vocabulary

:mod:`psims` uses several controlled vocabularies to name specific
entities controlled externally from the file formats being written to
make them update-able without needing to modify the schema for many
domain-specific changes. The :class:`~.ControlledVocabulary` type
represents a parsed and interpreted controlled vocabulary, a collection
of :class:`~psims.controlled_vocabulary.entity.Term` objects.


.. autoclass:: ControlledVocabulary
    :members:


Caching
-------
:mod:`psims` accesses controlled vocabularies from the internet to retrieve the
most up-to-date version of each vocabularies. If an internet connection is unavailable,
it will fall back to a vendored copy of a specific version of each controlled vocabulary
bundled with :mod:`psims` at build time.

Additionally, an application might choose to save a copy of each required controlled
vocabulary file on the file system in a specific location. This can be accomplished with the
:obj:`psims.controlled_vocabulary.controlled_vocabulary.obo_cache` object, an instance of :class:`~.OBOCache` type.
Setting :attr:`~.OBOCache.cache_path` will specify the path to the directory to cache files
in, and :attr:`~.OBOCache.enabled` to toggle whether or not the cache is used. If the cache
is enabled and a copy of the controlled vocabulary is not in the cache, a new copy will be
downloaded or loaded from the vendored copy if unavailable, and writes it to the cache directory
for future re-use.

If a library wants to create its own separate cache directory, it can create a new instance of
:class:`OBOCache` and configure it separately. This custom cache instance can be passed to all
file writing classes as the :obj:`vocabulary_resolver` parameter.

.. autoclass:: OBOCache
    :members:
