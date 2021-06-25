Controlled Vocabulary Objects
-----------------------------

.. automodule:: psims.controlled_vocabulary.controlled_vocabulary

:mod:`psims` uses controlled vocabularies to refer to externally controlled
and organized terms to describe the entities being written about in the file
formats it produces. These domain-specific vocabularies can be updated independently
from the file schemas for faster update and maintenance life cycles.

The :class:`~.ControlledVocabulary` type represents a parsed and interpreted
controlled vocabulary, a collection of :class:`~psims.controlled_vocabulary.entity.Entity`
objects.


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
XML file writing classes as the :obj:`vocabulary_resolver` parameter.

.. note::

    :class:`OBOCache` has two behavioral switches that interact:
        - :attr:`OBOCache.enabled` - When this is :const:`True`, files from the cache directory will be used
          and new files will be added to the cache directory. Otherwise, a new copy of each CV
          file will be requested when accessing a vocabulary.
        - :attr:`OBOCache.use_remote` - When this is :const:`True`, new copies of CV files will be requested
          over the network, falling back to packaged copy in :mod:`psims` only when the network
          request fails. Otherwise, the packaged copy will be used automatically.

.. autoclass:: OBOCache
    :members:


Semantic Data
-------------
Terms in a controlled vocabulary define entities, categories, properties and relationships between
them. The :class:`~psims.controlled_vocabulary.entity.Entity` type is how these are represented
in memory.

.. autoclass:: psims.controlled_vocabulary.entity.Entity
    :members: